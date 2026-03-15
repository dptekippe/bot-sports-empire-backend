"""
train_futureself.py — PPO + CFR training for FutureSelfGym v1
==============================================================
25 000 steps of PPO (Stable-Baselines3) with CFR-guided action masking
and pgvector memory seeding.

Usage
-----
    python train_futureself.py                  # default 25k steps
    python train_futureself.py --steps 50000    # longer run
    python train_futureself.py --eval           # run evaluation after training
    python train_futureself.py --pgvector       # pull live memories from DB

Outputs
-------
    models/futureself_ppo_25k.zip       — trained SB3 model
    models/cfr_strategy.json            — final CFR average strategy
    logs/futureself_tensorboard/        — TensorBoard logs
    logs/futureself_train.log           — training log
    universal_insights.jsonl            — appended after each training run
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

# Lazy imports — we test for SB3 availability gracefully
try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import (
        BaseCallback,
        CheckpointCallback,
        EvalCallback,
    )
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False

from futureself_gym import (
    ACTION_NAMES,
    HORIZON_DAYS,
    FutureSelfGym,
    CFRRegretTracker,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR   = Path(__file__).parent
MODEL_DIR  = BASE_DIR / "models"
LOG_DIR    = BASE_DIR / "logs"
INSIGHT_FILE = BASE_DIR / "universal_insights.jsonl"

MODEL_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "futureself_train.log"),
    ],
)
logger = logging.getLogger("TrainFutureSelf")

# ---------------------------------------------------------------------------
# pgvector memory loader
# ---------------------------------------------------------------------------

def load_pgvector_memories(limit: int = 10) -> List[Dict]:
    """
    Query Render PostgreSQL pgvector for top-10 recent FF/deploy/chess memories.
    Falls back to empty list if DB unavailable.

    SQL:
        SELECT content, project, importance FROM memories
        WHERE project IN ('FF','deploy','chess')
          AND timestamp > now() - INTERVAL '90 days'
        ORDER BY importance DESC
        LIMIT 10;
    """
    try:
        import psycopg2
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            logger.warning("DATABASE_URL not set — skipping pgvector seed")
            return []

        conn = psycopg2.connect(database_url, sslmode="require")
        cur = conn.cursor()
        cur.execute(
            """
            SELECT content, project, COALESCE(importance, 5) as importance
            FROM memories
            WHERE project IN ('FF', 'deploy', 'chess')
              AND created_at > now() - INTERVAL '90 days'
            ORDER BY importance DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()
        conn.close()

        memories = [
            {"content": row[0], "project": row[1], "importance": row[2]}
            for row in rows
        ]
        logger.info("Loaded %d memories from pgvector (FF/deploy/chess)", len(memories))
        return memories

    except Exception as exc:  # noqa: BLE001
        logger.warning("pgvector load failed (%s) — using defaults", exc)
        return []

# ---------------------------------------------------------------------------
# CFR Callback (SB3 compatible)
# ---------------------------------------------------------------------------

class CFRCallback(BaseCallback):
    """
    Runs CFR updates alongside PPO.
    At each rollout end, computes regrets from value estimates and updates
    the shared CFRRegretTracker.
    """

    def __init__(self, cfr_tracker: CFRRegretTracker, verbose: int = 0):
        super().__init__(verbose)
        self.cfr = cfr_tracker
        self.episode_utilities: List[np.ndarray] = []

    def _on_step(self) -> bool:
        return True

    def _on_rollout_end(self) -> None:
        """Called after each PPO rollout collection."""
        if hasattr(self.locals, "actions") and self.locals.get("actions") is not None:
            actions = self.locals["actions"]
            rewards = self.locals.get("rewards", np.zeros(len(actions)))

            for action, reward in zip(actions, rewards):
                # Approximate utilities: chosen action = observed reward,
                # others = mean reward (counterfactual placeholder)
                utils = np.full(7, float(rewards.mean()))
                utils[int(action)] = float(reward)
                self.cfr.update(int(action), utils)

        if self.verbose >= 1:
            strat = self.cfr.average_strategy()
            logger.info(
                "CFR strategy @ step %d: %s",
                self.num_timesteps,
                {ACTION_NAMES[i]: f"{strat[i]:.3f}" for i in range(7)},
            )

# ---------------------------------------------------------------------------
# Horizon logging callback
# ---------------------------------------------------------------------------

class HorizonLogCallback(BaseCallback):
    """Logs a horizon projection every N steps to universal_insights.jsonl."""

    def __init__(self, log_every: int = 5000, verbose: int = 0):
        super().__init__(verbose)
        self.log_every = log_every
        self._last_log = 0

    def _on_step(self) -> bool:
        if self.num_timesteps - self._last_log >= self.log_every:
            self._last_log = self.num_timesteps
            self._log_projection()
        return True

    def _log_projection(self) -> None:
        env = FutureSelfGym(seed=int(time.time()) % 10000)
        proj = env.project_horizon("Deploy prod now?", delay_days=3)
        env.close()

        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "step": self.num_timesteps,
            "type": "future_tree",
            "projection": proj,
        }

        with open(INSIGHT_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")

        logger.info(
            "[Step %d] Horizon: %s | gain=%.4f | metacog=%d",
            self.num_timesteps,
            proj["recommendation"],
            proj["gain"],
            proj["metacog_score"],
        )

# ---------------------------------------------------------------------------
# Training entry point
# ---------------------------------------------------------------------------

def train(
    total_steps: int = 25_000,
    use_pgvector: bool = False,
    run_eval: bool = False,
    seed: int = 42,
) -> str:
    """
    Train PPO + CFR on FutureSelfGym.
    Returns path to saved model.
    """
    if not SB3_AVAILABLE:
        raise ImportError(
            "stable-baselines3 is required: pip install stable-baselines3[extra]"
        )

    logger.info("=== FutureSelfGym v1 Training ===")
    logger.info("Steps: %d | pgvector: %s | eval: %s", total_steps, use_pgvector, run_eval)

    # Load memory context
    pgvector_context = load_pgvector_memories() if use_pgvector else []

    # Build env factory
    def make_env():
        env = FutureSelfGym(
            cfr_enabled=True,
            pgvector_context=pgvector_context,
            seed=seed,
        )
        return Monitor(env)

    # Vectorised env (4 parallel)
    vec_env = DummyVecEnv([make_env] * 4)
    vec_env = VecNormalize(vec_env, norm_obs=True, norm_reward=True, clip_obs=10.0)

    # Shared CFR tracker
    cfr = CFRRegretTracker(n_actions=7)

    # Callbacks
    callbacks = [
        CFRCallback(cfr, verbose=1),
        HorizonLogCallback(log_every=5_000),
        CheckpointCallback(
            save_freq=5_000,
            save_path=str(MODEL_DIR),
            name_prefix="futureself_ppo",
        ),
    ]

    if run_eval:
        eval_env = DummyVecEnv([make_env])
        eval_env = VecNormalize(eval_env, norm_obs=True, norm_reward=False)
        callbacks.append(
            EvalCallback(
                eval_env,
                best_model_save_path=str(MODEL_DIR / "best"),
                log_path=str(LOG_DIR / "eval"),
                eval_freq=5_000,
                n_eval_episodes=20,
                verbose=1,
            )
        )

    # PPO hyperparameters (tuned for short-horizon episodic task)
    model = PPO(
        policy="MlpPolicy",
        env=vec_env,
        learning_rate=3e-4,
        n_steps=256,
        batch_size=64,
        n_epochs=10,
        gamma=0.97,          # Favour 30d compounding over immediate
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,       # Encourage exploration of delay actions
        vf_coef=0.5,
        max_grad_norm=0.5,
        tensorboard_log=str(LOG_DIR / "futureself_tensorboard"),
        verbose=1,
        seed=seed,
    )

    # Train
    t_start = time.time()
    model.learn(total_timesteps=total_steps, callback=callbacks, progress_bar=True)
    elapsed = time.time() - t_start
    logger.info("Training complete in %.1fs", elapsed)

    # Save model
    model_path = str(MODEL_DIR / f"futureself_ppo_{total_steps // 1000}k")
    model.save(model_path)
    vec_env.save(str(MODEL_DIR / "vec_normalize.pkl"))
    logger.info("Model saved: %s.zip", model_path)

    # Save CFR strategy
    cfr_path = MODEL_DIR / "cfr_strategy.json"
    cfr_data = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "steps": total_steps,
        "average_strategy": cfr.average_strategy().tolist(),
        "action_names": ACTION_NAMES,
        "cumulative_regret": cfr.to_dict()["cumulative_regret"],
    }
    with open(cfr_path, "w") as f:
        json.dump(cfr_data, f, indent=2)
    logger.info("CFR strategy saved: %s", cfr_path)

    # Final horizon projection
    env_proj = FutureSelfGym(seed=seed + 1, pgvector_context=pgvector_context)
    proj = env_proj.project_horizon("Deploy prod now?", delay_days=3)
    env_proj.close()

    insight = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "step": total_steps,
        "type": "training_complete",
        "elapsed_seconds": round(elapsed, 1),
        "projection": proj,
        "cfr_final": cfr_data["average_strategy"],
    }
    with open(INSIGHT_FILE, "a") as f:
        f.write(json.dumps(insight) + "\n")

    logger.info("\n=== Final Horizon Projection ===")
    logger.info("Recommendation: %s", proj["recommendation"])
    logger.info("Gain:           %.4f", proj["gain"])
    logger.info("Metacog:        %d/100", proj["metacog_score"])
    logger.info("Capacity:       %d%%", proj["capacity_headroom_pct"])
    logger.info("Explanation:    %s", proj["explanation"])

    return model_path + ".zip"


# ---------------------------------------------------------------------------
# Standalone evaluation
# ---------------------------------------------------------------------------

def evaluate(model_path: str, n_episodes: int = 50) -> Dict[str, Any]:
    """Run evaluation episodes and return summary stats."""
    if not SB3_AVAILABLE:
        raise ImportError("stable-baselines3 required")

    from stable_baselines3 import PPO

    model = PPO.load(model_path)
    env = FutureSelfGym(render_mode="human", seed=999)

    returns = []
    action_counts = {a: 0 for a in range(7)}

    for ep in range(n_episodes):
        obs, _ = env.reset()
        ep_return = 0.0
        done = False

        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, _ = env.step(int(action))
            ep_return += reward
            action_counts[int(action)] += 1
            done = terminated or truncated

        returns.append(ep_return)

    env.close()

    stats = {
        "n_episodes":      n_episodes,
        "mean_return":     float(np.mean(returns)),
        "std_return":      float(np.std(returns)),
        "min_return":      float(np.min(returns)),
        "max_return":      float(np.max(returns)),
        "action_dist":     {ACTION_NAMES[k]: v for k, v in action_counts.items()},
    }

    logger.info("Evaluation complete: mean_return=%.3f ± %.3f", stats["mean_return"], stats["std_return"])
    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train FutureSelfGym v1")
    p.add_argument("--steps",     type=int,  default=25_000, help="Total PPO steps (default 25000)")
    p.add_argument("--eval",      action="store_true",       help="Run evaluation after training")
    p.add_argument("--pgvector",  action="store_true",       help="Seed from live pgvector DB")
    p.add_argument("--eval-only", type=str,  default=None,   help="Path to existing model to evaluate")
    p.add_argument("--seed",      type=int,  default=42,     help="Random seed")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.eval_only:
        stats = evaluate(args.eval_only)
        print(json.dumps(stats, indent=2))
    else:
        model_path = train(
            total_steps=args.steps,
            use_pgvector=args.pgvector,
            run_eval=args.eval,
            seed=args.seed,
        )
        print(f"\n✅ Model ready: {model_path}")

        if args.eval:
            stats = evaluate(model_path)
            print(json.dumps(stats, indent=2))
