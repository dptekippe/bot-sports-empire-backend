"""
rl_harness.py — Gymnasium RL Harness with pgvector Memory

Wraps any Gymnasium environment to:
  1. Run episodes and collect (s, a, r, s') transitions
  2. Store each step to pgvector via PgVectorClient
  3. Query pgvector for similar past states at each step
  4. Shape rewards based on pgvector insights
  5. Self-tune hyperparameters after N episodes

Usage:
    from rl_harness import RLHarness

    client = PgVectorClient()
    harness = RLHarness(client)

    stats = harness.run(
        env_name="CartPole-v1",
        num_episodes=50,
        use_reward_shaping=True,
        use_hp_tuning=True,
    )
"""

from __future__ import annotations

import gymnasium as gym
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from pgvector_client import PgVectorClient, PgVectorConfig


# ============ HYPERPARAMETERS ============

@dataclass
class RLHyperparams:
    """Hyperparameters for an RL run. Tunable by hp_tuner."""

    lr_rate: float = 1e-3
    gamma: float = 0.99        # discount factor
    epsilon: float = 1.0      # exploration rate (ε-greedy)
    epsilon_min: float = 0.01
    epsilon_decay: float = 0.995
    importance_baseline: float = 5.0   # default importance for new memories

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def to_dict(self) -> Dict[str, float]:
        return {
            "lr_rate": self.lr_rate,
            "gamma": self.gamma,
            "epsilon": self.epsilon,
            "epsilon_min": self.epsilon_min,
            "epsilon_decay": self.epsilon_decay,
        }


# ============ EPISODE RESULT ============

@dataclass
class EpisodeResult:
    episode_id: int
    total_reward: float
    num_steps: int
    duration_s: float
    hyperparams: RLHyperparams
    shaped_reward: Optional[float] = None   # avg shaped reward if shaping enabled
    pgvector_insight: Optional[Dict[str, Any]] = None


# ============ CALLBACKS ============

@dataclass
class RLCallbacks:
    """Optional hooks called at various points during episode execution."""

    on_step: Optional[Callable[[int, Any, Any, float, bool, Dict], None]] = None
    # signature: (step, state, action, shaped_reward, done, pgvector_ctx)

    on_episode_start: Optional[Callable[[int, RLHyperparams], None]] = None
    on_episode_end: Optional[Callable[[EpisodeResult], None]] = None


# ============ MAIN RL HARNESS ============

class RLHarness:
    """
    Orchestrates:
      - Environment lifecycle
      - Experience collection
      - pgvector storage + recall
      - Reward shaping (optional)
      - Hyperparameter tuning (optional)
    """

    def __init__(
        self,
        pg_client: PgVectorClient,
        callbacks: Optional[RLCallbacks] = None,
        shaping_bonus_weight: float = 0.1,
        shaping_penalty_weight: float = 0.05,
        recall_top_k: int = 5,
    ):
        """
        Args:
            pg_client: PgVectorClient connected to rl_memories table.
            callbacks: Optional RLCallbacks for logging / visualisation.
            shaping_bonus_weight: Max bonus added to reward when pgvector
                shows similar state historically led to high return.
            shaping_penalty_weight: Max penalty when similar state led to
                low return.
            recall_top_k: How many similar memories to fetch per step.
        """
        self.pg = pg_client
        self.callbacks = callbacks or RLCallbacks()
        self.shaping_bonus_weight = shaping_bonus_weight
        self.shaping_penalty_weight = shaping_penalty_weight
        self.recall_top_k = recall_top_k

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        env_name: str,
        num_episodes: int,
        hyperparams: Optional[RLHyperparams] = None,
        use_reward_shaping: bool = True,
        use_hp_tuning: bool = True,
        hp_tune_every: int = 10,
        agent_policy: Optional[Callable[[Any, RLHyperparams], Any]] = None,
        verbose: bool = True,
    ) -> Dict[str, Any]:
        """
        Run a full training loop.

        Args:
            env_name:       Gymnasium env ID (e.g. "CartPole-v1").
            num_episodes:  Number of episodes to run.
            hyperparams:   Starting hyperparameters.
            use_reward_shaping: Whether to query pgvector and modify rewards.
            use_hp_tuning:     Whether to self-tune hparams every hp_tune_every.
            agent_policy:  Policy function(state, hyperparams) -> action.
                            If None, a random policy is used.
            verbose:        Print progress.

        Returns:
            Summary dict with episode results, final stats, and tuned hparams.
        """
        hp = hyperparams or RLHyperparams()
        env = gym.make(env_name)
        results: List[EpisodeResult] = []
        episode_returns: List[float] = []

        for ep in range(1, num_episodes + 1):
            result = self.collect_episode(
                env=env,
                episode_id=ep,
                hyperparams=hp,
                use_reward_shaping=use_reward_shaping,
                agent_policy=agent_policy,
            )
            results.append(result)
            episode_returns.append(result.total_reward)
            hp.decay_epsilon()

            if verbose:
                self._print_episode(result, use_reward_shaping)

            # ---- hyperparameter tuning ----
            if use_hp_tuning and ep % hp_tune_every == 0:
                from reward_shaper import RewardShaper
                from hp_tuner import HPTuner

                tuner = HPTuner(self.pg)
                suggestion = tuner.tune_hyperparams(
                    recent_episodes=episode_returns[-hp_tune_every:],
                    current_hp=hp,
                )
                if suggestion:
                    old_hp = {k: v for k, v in hp.to_dict().items()}
                    hp.lr_rate = suggestion.get("lr_rate", hp.lr_rate)
                    hp.gamma = suggestion.get("gamma", hp.gamma)
                    hp.epsilon = suggestion.get("epsilon", hp.epsilon)
                    hp.epsilon_decay = suggestion.get("epsilon_decay", hp.epsilon_decay)
                    if verbose:
                        print(
                            f"  [HP Tuning] lr: {old_hp['lr_rate']:.4f} → {hp.lr_rate:.4f}  "
                            f"gamma: {old_hp['gamma']:.3f} → {hp.gamma:.3f}  "
                            f"eps: {old_hp['epsilon']:.3f} → {hp.epsilon:.3f}"
                        )

        env.close()

        # ---- final stats ----
        final_stats = self.pg.get_stats()
        best_episodes = self.pg.get_best_episodes(limit=5)

        if verbose:
            print(f"\n{'='*60}")
            print(f"  Total memories in pgvector: {final_stats['total_memories']}")
            print(f"  Avg reward/step:            {final_stats['avg_reward']:.3f}")
            print(f"  Avg episode return:         {final_stats['avg_episode_return']:.2f}")
            print(f"  Best episodes (by avg return):")
            for row in best_episodes:
                print(
                    f"    ep {row['episode_id']}: "
                    f"avg_return={row['avg_return']:.2f}  "
                    f"steps={row['steps']}"
                )
            print(f"{'='*60}\n")

        return {
            "episode_results": results,
            "final_stats": final_stats,
            "best_episodes": best_episodes,
            "final_hyperparams": hp.to_dict(),
        }

    def collect_episode(
        self,
        env: gym.Env,
        episode_id: int,
        hyperparams: RLHyperparams,
        use_reward_shaping: bool = True,
        agent_policy: Optional[Callable[[Any, RLHyperparams], Any]] = None,
    ) -> EpisodeResult:
        """
        Run one episode, store every step to pgvector.

        Args:
            env:               A reset()-able Gymnasium env.
            episode_id:        Unique integer ID for this episode.
            hyperparams:       Current HPs (used for ε-greedy, etc.).
            use_reward_shaping: If True, call RewardShaper per step.
            agent_policy:      Function(state, hyperparams) -> action.
                                Defaults to random.

        Returns:
            EpisodeResult with metrics and optional pgvector insight.
        """
        policy = agent_policy or self._random_policy
        shaper = RewardShaper(self.pg) if use_reward_shaping else None

        import time

        state, _ = env.reset()
        done = False
        step = 0
        total_reward = 0.0
        shaped_rewards: List[float] = []
        pgvector_ctx: Optional[Dict[str, Any]] = None

        t0 = time.time()

        self.callbacks.on_episode_start and self.callbacks.on_episode_start(
            episode_id, hyperparams
        )

        while not done:
            action = policy(state, hyperparams)

            next_state, raw_reward, terminated, truncated, _ = env.step(action)
            done = terminated or truncated

            # ---- reward shaping ----
            if shaper is not None:
                shaped_reward, pgvector_ctx = shaper.shape_reward(
                    original_reward=raw_reward,
                    state=state,
                    next_state=next_state,
                    action=action,
                    recall_top_k=self.recall_top_k,
                    bonus_weight=self.shaping_bonus_weight,
                    penalty_weight=self.shaping_penalty_weight,
                )
            else:
                shaped_reward = raw_reward
                pgvector_ctx = None

            # ---- compute importance ----
            # Importance = base + bonus for high raw_reward + bonus for rare states
            importance = self._compute_importance(
                raw_reward=raw_reward,
                pgvector_ctx=pgvector_ctx,
                base=hyperparams.importance_baseline,
            )

            # ---- store to pgvector ----
            self.pg.store_experience(
                state=state,
                action=action,
                reward=shaped_reward,
                next_state=next_state,
                episode_id=episode_id,
                episode_return=0.0,   # filled in at episode end
                importance=importance,
            )

            shaped_rewards.append(shaped_reward)
            total_reward += raw_reward
            step += 1

            self.callbacks.on_step and self.callbacks.on_step(
                step, state, action, shaped_reward, done, pgvector_ctx
            )

            state = next_state

        elapsed = time.time() - t0

        # Update episode_return on stored memories (backfill)
        self._backfill_episode_return(episode_id, total_reward)

        return EpisodeResult(
            episode_id=episode_id,
            total_reward=total_reward,
            num_steps=step,
            duration_s=elapsed,
            hyperparams=hyperparams,
            shaped_reward=np.mean(shaped_rewards) if shaped_rewards else 0.0,
            pgvector_insight=pgvector_ctx,
        )

    def get_pgvector_insight(self, state: Any) -> Dict[str, Any]:
        """
        Standalone query: get similar memories for a state without shaping.
        Useful for inspection / debugging.
        """
        memories = self.pg.recall(state, top_k=self.recall_top_k)
        if not memories:
            return {"found": False, "count": 0}

        avg_return = np.mean(
            [m["episode_return"] for m in memories if m.get("episode_return") is not None]
        )
        avg_importance = np.mean([m["importance"] for m in memories])
        return {
            "found": True,
            "count": len(memories),
            "avg_episode_return": float(avg_return),
            "avg_importance": float(avg_importance),
            "top_memories": [
                {
                    "episode_id": m["episode_id"],
                    "action": m["action"],
                    "reward": m["reward"],
                    "importance": m["importance"],
                }
                for m in memories[:3]
            ],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _random_policy(state: Any, hp: RLHyperparams) -> Any:
        """ε-greedy random policy."""
        if hasattr(state, "shape"):
            num_actions = int(np.prod(state.shape))  # rough guess
        else:
            num_actions = 2
        # Use Gym's action space if available on env (passed separately in subclass)
        return np.random.randint(0, max(2, num_actions))

    @staticmethod
    def _compute_importance(
        raw_reward: float,
        pgvector_ctx: Optional[Dict[str, Any]],
        base: float = 5.0,
    ) -> float:
        """Importance = base + reward contribution + pgvector signal."""
        imp = base + raw_reward * 0.5
        if pgvector_ctx and pgvector_ctx.get("similar_state_found"):
            delta = pgvector_ctx.get("return_delta", 0.0)
            imp += abs(delta) * 0.2
        return float(np.clip(imp, 1.0, 10.0))

    def _backfill_episode_return(self, episode_id: int, episode_return: float) -> None:
        """Update all memories from this episode with the final return."""
        conn = self.pg._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE rl_memories
                    SET episode_return = %s
                    WHERE episode_id = %s
                    """,
                    (float(episode_return), episode_id),
                )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _print_episode(result: EpisodeResult, shaping: bool) -> None:
        suffix = f"  shaped_avg={result.shaped_reward:.3f}" if shaping else ""
        print(
            f"  ep {result.episode_id:3d} | "
            f"return={result.total_reward:7.1f} | "
            f"steps={result.num_steps:4d} | "
            f"eps={result.hyperparams.epsilon:.3f}{suffix}"
        )
