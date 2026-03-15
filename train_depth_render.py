"""
train_depth_render.py — PPO + CFR Training Script for DepthRenderGym v1
========================================================================
Usage:
    python train_depth_render.py                          # 30k steps
    python train_depth_render.py --steps 10000            # custom
    python train_depth_render.py --steps 5000 --eval      # + eval run
    python train_depth_render.py --load-cfr               # resume CFR
    python train_depth_render.py --demo                   # quick 3-step demo

Outputs:
    ~/.openclaw/gyms/depth_render_cfr.json      — CFR strategy (auto-saved)
    ~/.openclaw/gyms/depth_render_ppo.json      — PPO policy weights
    ~/.openclaw/gyms/depth_render_log.jsonl     — per-episode training log
    depth_render_results.json                   — final validation results
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Local import
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))
from depth_render_gym import (
    N_ACTIONS,
    N_OBS,
    CFR_PRIOR,
    DepthRenderGym,
    build_context_injection,
    compute_reward,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
GYM_DIR       = Path("~/.openclaw/gyms").expanduser()
CFR_PATH      = GYM_DIR / "depth_render_cfr.json"
PPO_PATH      = GYM_DIR / "depth_render_ppo.json"
LOG_PATH      = GYM_DIR / "depth_render_log.jsonl"
RESULTS_PATH  = Path("depth_render_results.json")

GYM_DIR.mkdir(parents=True, exist_ok=True)

# ===========================================================================
# PPO POLICY (Lightweight — Softmax Linear)
# ===========================================================================

@dataclass
class PPOPolicy:
    """
    Minimal linear policy: obs (4,) → logits (5,) → action probs.
    Weights: (5, 4) matrix + bias (5,).
    Trained with REINFORCE (policy gradient) approximation.
    """
    W:   np.ndarray
    b:   np.ndarray
    lr:  float = 3e-4
    gamma: float = 0.99
    eps_clip: float = 0.2

    @classmethod
    def init(cls, seed: int = 0) -> "PPOPolicy":
        rng = np.random.default_rng(seed)
        W = rng.normal(0, 0.1, (N_ACTIONS, N_OBS)).astype(np.float64)
        b = np.zeros(N_ACTIONS, dtype=np.float64)
        return cls(W=W, b=b)

    def logits(self, obs: np.ndarray) -> np.ndarray:
        return self.W @ obs + self.b

    def probs(self, obs: np.ndarray) -> np.ndarray:
        lg = self.logits(obs)
        lg -= lg.max()   # numerical stability
        e = np.exp(lg)
        return e / e.sum()

    def sample(self, obs: np.ndarray, rng: np.random.Generator) -> int:
        p = self.probs(obs)
        return int(rng.choice(N_ACTIONS, p=p))

    def update(
        self,
        obs_buf:    List[np.ndarray],
        act_buf:    List[int],
        ret_buf:    List[float],
        old_probs:  List[float],
    ) -> float:
        """PPO-clip update — returns mean policy loss."""
        loss_total = 0.0
        for obs, act, ret, old_p in zip(obs_buf, act_buf, ret_buf, old_probs):
            probs = self.probs(obs)
            new_p = probs[act]
            ratio = new_p / (old_p + 1e-8)
            # Advantage = return (no baseline for simplicity)
            adv = ret
            clip_r = np.clip(ratio, 1 - self.eps_clip, 1 + self.eps_clip)
            ppo_loss = -min(ratio * adv, clip_r * adv)

            # Gradient: d(loss)/dW via log-prob gradient
            grad_log = np.zeros_like(probs)
            grad_log[act] = 1.0
            grad_log -= probs
            grad = np.outer(grad_log, obs)

            self.W -= self.lr * ppo_loss * grad
            self.b -= self.lr * ppo_loss * grad_log
            loss_total += ppo_loss

        return loss_total / max(len(obs_buf), 1)

    def to_dict(self) -> Dict:
        return {"W": self.W.tolist(), "b": self.b.tolist()}

    @classmethod
    def from_dict(cls, d: Dict) -> "PPOPolicy":
        return cls(W=np.array(d["W"]), b=np.array(d["b"]))

    def save(self, path: Path = PPO_PATH):
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path = PPO_PATH) -> "PPOPolicy":
        if path.exists():
            with open(path) as f:
                return cls.from_dict(json.load(f))
        return cls.init()


# ===========================================================================
# TRAINING LOOP
# ===========================================================================

def compute_returns(rewards: List[float], gamma: float = 0.99) -> List[float]:
    returns = []
    R = 0.0
    for r in reversed(rewards):
        R = r + gamma * R
        returns.insert(0, R)
    # Normalize
    arr = np.array(returns)
    if arr.std() > 1e-8:
        arr = (arr - arr.mean()) / arr.std()
    return arr.tolist()


def train(
    total_steps:   int   = 30_000,
    seed:          int   = 42,
    load_cfr:      bool  = False,
    verbose:       bool  = True,
    log_interval:  int   = 100,
    save_interval: int   = 1000,
    db_url:        Optional[str] = None,
) -> Dict:
    """
    Main PPO+CFR training loop.
    Returns summary dict with final metrics.
    """
    rng = np.random.default_rng(seed)

    # Init env + policy
    env    = DepthRenderGym(max_steps=20, db_url=db_url, seed=seed)
    policy = PPOPolicy.load() if PPO_PATH.exists() else PPOPolicy.init(seed)

    if load_cfr:
        env.load_cfr()

    # Metrics
    episode_rewards:  List[float] = []
    episode_lengths:  List[int]   = []
    all_scores:       List[Dict]  = []
    step_count        = 0
    ep_count          = 0
    start_time        = time.time()

    log_fh = open(LOG_PATH, "a")

    if verbose:
        print(f"\n{'─'*60}")
        print(f"  DepthRenderGym v1 — PPO+CFR Training")
        print(f"  Total steps: {total_steps:,}  |  Seed: {seed}")
        print(f"{'─'*60}")

    # ---------------------------------------------------------------------------
    # Training loop
    # ---------------------------------------------------------------------------
    while step_count < total_steps:
        obs, info = env.reset()
        ep_reward = 0.0
        ep_steps  = 0

        # Rollout buffers
        obs_buf:   List[np.ndarray] = []
        act_buf:   List[int]        = []
        rew_buf:   List[float]      = []
        old_probs: List[float]      = []

        done = False
        while not done and step_count < total_steps:
            # Blend PPO + CFR for action selection
            cfr_strat = env.cfr.get_strategy()
            ppo_probs = policy.probs(obs)
            # Weighted blend: 60% PPO, 40% CFR (shifts toward PPO as training progresses)
            blend_ratio = min(step_count / total_steps, 0.8)
            blend_probs = (blend_ratio) * ppo_probs + (1 - blend_ratio) * cfr_strat
            blend_probs = np.clip(blend_probs, 1e-6, 1.0)
            blend_probs /= blend_probs.sum()

            action   = int(rng.choice(N_ACTIONS, p=blend_probs))
            old_p    = float(blend_probs[action])

            next_obs, reward, terminated, truncated, step_info = env.step(action)
            done = terminated or truncated

            obs_buf.append(obs.copy())
            act_buf.append(action)
            rew_buf.append(reward)
            old_probs.append(old_p)

            ep_reward  += reward
            ep_steps   += 1
            step_count += 1
            obs = next_obs

        # PPO update at end of episode
        if obs_buf:
            returns   = compute_returns(rew_buf, policy.gamma)
            ppo_loss  = policy.update(obs_buf, act_buf, returns, old_probs)
        else:
            ppo_loss = 0.0

        ep_count += 1
        episode_rewards.append(ep_reward)
        episode_lengths.append(ep_steps)

        # Log episode
        ep_log = {
            "episode":     ep_count,
            "steps":       step_count,
            "ep_reward":   round(ep_reward, 4),
            "ep_steps":    ep_steps,
            "ppo_loss":    round(float(ppo_loss), 6),
            "cfr_updates": env.cfr.update_count,
            "depth_score": round(float(env._obs[0]), 4),
            "canvas_qual": round(float(env._obs[1]), 4),
        }
        log_fh.write(json.dumps(ep_log) + "\n")
        log_fh.flush()

        all_scores.append({
            "depth":  float(env._obs[0]),
            "canvas": float(env._obs[1]),
        })

        # Console output
        if verbose and ep_count % log_interval == 0:
            avg_r     = np.mean(episode_rewards[-log_interval:])
            avg_depth = np.mean([s["depth"]  for s in all_scores[-log_interval:]])
            avg_canvas= np.mean([s["canvas"] for s in all_scores[-log_interval:]])
            cfr_str   = " ".join(f"{v:.2f}" for v in env.cfr.get_strategy())
            elapsed   = time.time() - start_time
            steps_ps  = step_count / elapsed
            print(
                f"Ep {ep_count:5d} | Step {step_count:7,d} | "
                f"Reward {avg_r:6.3f} | Depth {avg_depth:.3f} | "
                f"Canvas {avg_canvas:.3f} | CFR [{cfr_str}] | "
                f"{steps_ps:.0f} step/s"
            )

        # Checkpoint saves
        if step_count % save_interval == 0:
            env.save_cfr(str(CFR_PATH))
            policy.save(PPO_PATH)

    # ---------------------------------------------------------------------------
    # Final save
    # ---------------------------------------------------------------------------
    env.save_cfr(str(CFR_PATH))
    policy.save(PPO_PATH)
    log_fh.close()

    elapsed = time.time() - start_time
    summary = {
        "total_steps":       step_count,
        "episodes":          ep_count,
        "elapsed_s":         round(elapsed, 1),
        "steps_per_sec":     round(step_count / elapsed, 1),
        "mean_reward":       round(float(np.mean(episode_rewards)), 4),
        "max_reward":        round(float(np.max(episode_rewards)), 4),
        "final_depth":       round(float(np.mean([s["depth"]  for s in all_scores[-50:]])), 4),
        "final_canvas":      round(float(np.mean([s["canvas"] for s in all_scores[-50:]])), 4),
        "cfr_updates":       env.cfr.update_count,
        "cfr_avg_strategy":  {
            k: round(v, 3) for k, v in zip(
                ["expand_analysis", "canvas_mermaid", "plotly_chart",
                 "rich_table", "source_tree"],
                env.cfr.average_strategy().tolist(),
            )
        },
    }

    if verbose:
        print(f"\n{'─'*60}")
        print(f"  Training complete!")
        print(f"  Steps: {step_count:,}  |  Episodes: {ep_count}  |  {elapsed:.1f}s")
        print(f"  Mean reward: {summary['mean_reward']:.4f}")
        print(f"  Final depth: {summary['final_depth']:.4f}")
        print(f"  Final canvas: {summary['final_canvas']:.4f}")
        print(f"  CFR strategy: {summary['cfr_avg_strategy']}")
        print(f"{'─'*60}\n")

    return summary


# ===========================================================================
# EVALUATION
# ===========================================================================

EVAL_QUERIES = [
    "1.09 ADP?",
    "Compare Bijan vs CMC dynasty value.",
    "Show me a Mermaid flowchart of the OpenClaw hook pipeline.",
    "What is the best RB to target in round 2 of a 12-team PPR draft?",
    "Build a source tree for 2026 dynasty rankings.",
]

def evaluate(
    n_episodes: int = 5,
    db_url:     Optional[str] = None,
    seed:       int = 99,
) -> Dict:
    """Run evaluation episodes and compute final score."""
    env    = DepthRenderGym(max_steps=20, db_url=db_url, seed=seed)
    policy = PPOPolicy.load()
    env.load_cfr()

    rng = np.random.default_rng(seed)
    scores = []

    print(f"\n{'─'*60}")
    print(f"  DepthRenderGym v1 — Evaluation ({n_episodes} episodes)")
    print(f"{'─'*60}")

    for i, query in enumerate(EVAL_QUERIES[:n_episodes]):
        obs, info = env.reset()
        ep_reward = 0.0
        done      = False
        step      = 0

        while not done:
            action = policy.sample(obs, rng)
            obs, reward, terminated, truncated, step_info = env.step(action)
            ep_reward += reward
            done = terminated or truncated
            step += 1

        final = env.get_summary()
        score_100 = final["score_100"]
        scores.append(score_100)

        print(
            f"  Q{i+1}: '{query[:40]:<40s}' → "
            f"Score {score_100:3d}/100 | "
            f"Depth {final['depth_score']:.3f} | "
            f"Canvas {final['canvas_quality']:.3f}"
        )

        # Generate ADP chart for the canonical test query
        if "ADP" in query or "1.09" in query:
            print(f"\n  [Canvas preview — ADP chart for '{query}']")
            chart = env.generate_canvas(
                "plotly",
                query=query,
                chart_type="horizontal_bar",
                x=["McCaffrey", "Hill", "Jefferson", "Robinson", "Henry"],
                y=[1.01, 1.02, 1.03, 1.09, 1.12],
                x_label="ADP", y_label="Player",
                title=f"Dynasty ADP — {query}",
            )
            print(chart[:400])

    avg_score = round(float(np.mean(scores)), 1)
    print(f"\n  Average score: {avg_score}/100  (target: 95/100)")
    print(f"{'─'*60}\n")

    return {
        "eval_scores":    scores,
        "avg_score_100":  avg_score,
        "target":         95,
        "pass":           avg_score >= 90,
    }


# ===========================================================================
# QUICK DEMO (no gymnasium required)
# ===========================================================================

def demo():
    """3-step demo showing canvas output without full training."""
    print("\n=== DepthRenderGym v1 — Quick Demo ===\n")
    env = DepthRenderGym(max_steps=5, seed=0)
    obs, info = env.reset()
    print(f"Query: {info['question']}")
    print(f"Initial obs: {obs}\n")

    actions = [0, 2, 3]  # expand_analysis, plotly_chart, rich_table
    for a in actions:
        obs, r, term, trunc, info = env.step(a)
        print(f"Action: {info['action_name']:<20s}  Reward: {r:.4f}")
        print(f"  Scores: {info['scores']}")
        print(f"  Sample: {info['augmented_sample'][:120]}\n")

    inj = build_context_injection(env, "1.09 ADP?")
    print("Context injection (hook payload):")
    print(json.dumps(json.loads(inj), indent=2))


# ===========================================================================
# CLI
# ===========================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train DepthRenderGym v1")
    parser.add_argument("--steps",     type=int,  default=30_000,
                        help="Total training steps (default: 30000)")
    parser.add_argument("--seed",      type=int,  default=42)
    parser.add_argument("--load-cfr",  action="store_true",
                        help="Load existing CFR checkpoint")
    parser.add_argument("--eval",      action="store_true",
                        help="Run evaluation after training")
    parser.add_argument("--eval-only", action="store_true",
                        help="Only run evaluation (skip training)")
    parser.add_argument("--demo",      action="store_true",
                        help="Quick 3-step demo (no training)")
    parser.add_argument("--db-url",    type=str,  default=None,
                        help="PostgreSQL URL for memory probe")
    args = parser.parse_args()

    if args.demo:
        demo()
        sys.exit(0)

    if args.eval_only:
        results = evaluate(db_url=args.db_url)
        with open(RESULTS_PATH, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Results saved → {RESULTS_PATH}")
        sys.exit(0)

    # Training
    summary = train(
        total_steps = args.steps,
        seed        = args.seed,
        load_cfr    = args.load_cfr,
        db_url      = args.db_url,
    )

    # Optional eval
    if args.eval:
        eval_results = evaluate(db_url=args.db_url)
        summary["eval"] = eval_results

    # Save results
    with open(RESULTS_PATH, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Results saved → {RESULTS_PATH}")
