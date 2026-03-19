"""
example_cartpole.py — CartPole-v1 Demo with pgvector Memory

Demonstrates:
  1. Running RLHarness with CartPole-v1 for 50 episodes
  2. Reward shaping improving performance over baseline
  3. Hyperparameter tuning suggestions every 10 episodes
  4. Live pgvector stats after each episode

Usage:
    python example_cartpole.py

Requirements:
    pip install gymnasium numpy psycopg2 requests

Environment variables (optional):
    DATABASE_URL      — PostgreSQL connection string
    OLLAMA_URL        — Ollama server URL (default: http://localhost:11434)
    EMBEDDING_MODEL   — embedding model name (default: all-mpnet-base-v2)

The pgvector table (rl_memories) is auto-created on first run.
"""

import os
import sys
import time
import argparse
from typing import Any

# Add harness dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gymnasium as gym
import numpy as np

from pgvector_client import PgVectorClient, PgVectorConfig
from rl_harness import RLHarness, RLHyperparams
from reward_shaper import RewardShaper
from hp_tuner import HPTuner


# =============================================================================
# Simple Agent Policies
# =============================================================================

def random_policy(state: Any, hp: Any) -> int:
    """Pure random baseline."""
    return gym.spaces.discrete.Discrete(2).sample()


def slightly_informed_policy(state: Any, hp: Any) -> int:
    """
    ε-greedy policy using a trivial heuristic for CartPole.
    The heuristic flips action when the pole angle is large.
    """
    import math

    if isinstance(state, (list, tuple)):
        # CartPole: [cart_x, cart_v, pole_angle, pole_v]
        angle = state[2] if len(state) > 2 else 0.0
    else:
        angle = float(state[2]) if hasattr(state, "__getitem__") else 0.0

    # Exploration
    if np.random.random() < hp.epsilon:
        return np.random.randint(0, 2)

    # Simple heuristic: push cart away from falling pole
    return 0 if angle < 0 else 1


# =============================================================================
# Logging Callback
# =============================================================================

class LiveStatsCallback:
    """Accumulates stats for printing after each episode."""

    def __init__(self, pg_client: PgVectorClient):
        self.pg = pg_client
        self.history: list[dict] = []

    def on_episode_end(self, result):
        stats = self.pg.get_stats()
        row = {
            "ep": result.episode_id,
            "return": result.total_reward,
            "steps": result.num_steps,
            "epsilon": result.hyperparams.epsilon,
            "total_memories": stats["total_memories"],
            "avg_return": stats["avg_episode_return"],
        }
        self.history.append(row)

        if result.episode_id % 10 == 0:
            # Full HP tuning report
            tuner = HPTuner(self.pg)
            returns = [h["return"] for h in self.history[-10:]]
            print(tuner.tuning_report(returns, result.hyperparams))
            print()


# =============================================================================
# Main Demo
# =============================================================================

def run_demo(
    num_episodes: int = 50,
    use_reward_shaping: bool = True,
    use_hp_tuning: bool = True,
    hp_tune_every: int = 10,
    compare_baseline: bool = False,
):
    """
    Run the CartPole demo.

    Args:
        num_episodes:       Total episodes.
        use_reward_shaping: Enable pgvector-based reward shaping.
        use_hp_tuning:      Enable HP self-tuning.
        hp_tune_every:      Tune HP every N episodes.
        compare_baseline:   If True, run a no-shaping baseline first for
                            comparison (requires 2x num_episodes).
    """
    print("=" * 60)
    print("  Gymnasium RL Harness + pgvector Memory Demo")
    print("  CartPole-v1")
    print("=" * 60)

    # ---- Setup pgvector client ----
    config = PgVectorConfig.from_env()
    pg = PgVectorClient(config)
    pg.ensure_table()
    print(f"\n[pgvector] connected to: {config.connection_string}")
    print(f"[pgvector] Ollama: {config.ollama_url}/api/embeddings")
    print(f"[pgvector] model: {config.embedding_model}\n")

    # Quick Ollama health check
    try:
        import requests
        resp = requests.get(
            f"{config.ollama_url}/api/tags", timeout=5
        )
        models = [m["name"] for m in resp.json().get("models", [])]
        print(f"[Ollama] available models: {models}")
    except Exception as e:
        print(f"[Ollama] WARNING — could not reach Ollama: {e}")
        print("         Embeddings will fail. Ensure Ollama is running:")
        print("         ollama serve")
        return

    # ---- Baseline comparison ----
    if compare_baseline:
        print("\n### BASELINE (no reward shaping) ###")
        harness_baseline = RLHarness(
            pg_client=pg,
            use_reward_shaping=False,
            callbacks=LiveStatsCallback(pg),
        )
        hp0 = RLHyperparams()
        baseline_results = harness_baseline.run(
            env_name="CartPole-v1",
            num_episodes=num_episodes,
            hyperparams=hp0,
            use_reward_shaping=False,
            use_hp_tuning=False,
            agent_policy=slightly_informed_policy,
            verbose=True,
        )
        baseline_returns = [r.total_reward for r in baseline_results["episode_results"]]
        baseline_avg = np.mean(baseline_returns[-10:])
        print(f"\nBaseline avg return (last 10 eps): {baseline_avg:.1f}")

        # Reset for shaped run
        pg.ensure_table()
        print("\n### SHAPED (reward shaping enabled) ###")
    else:
        baseline_avg = None

    # ---- Main shaped run ----
    harness = RLHarness(
        pg_client=pg,
        shaping_bonus_weight=0.1,
        shaping_penalty_weight=0.05,
        recall_top_k=5,
    )

    hp = RLHyperparams(
        lr_rate=5e-4,
        gamma=0.99,
        epsilon=1.0,
        epsilon_decay=0.995,
        epsilon_min=0.01,
    )

    print("\nStarting training loop...\n")

    results = harness.run(
        env_name="CartPole-v1",
        num_episodes=num_episodes,
        hyperparams=hp,
        use_reward_shaping=use_reward_shaping,
        use_hp_tuning=use_hp_tuning,
        hp_tune_every=hp_tune_every,
        agent_policy=slightly_informed_policy,
        verbose=True,
    )

    # ---- Summary ----
    shaped_returns = [r.total_reward for r in results["episode_results"]]
    shaped_avg = np.mean(shaped_returns[-10:])
    final_stats = results["final_stats"]
    final_hp = results["final_hyperparams"]

    print("\n" + "=" * 60)
    print("  TRAINING COMPLETE")
    print("=" * 60)
    print(f"  Episodes:            {num_episodes}")
    print(f"  Reward shaping:       {use_reward_shaping}")
    print(f"  HP tuning:           {use_hp_tuning}")
    print(f"  pgvector memories:   {final_stats['total_memories']}")
    print(f"  Final epsilon:        {final_hp['epsilon']:.4f}")
    print(f"  Final lr_rate:        {final_hp['lr_rate']:.6f}")
    print(f"  Final gamma:          {final_hp['gamma']:.4f}")

    if baseline_avg is not None:
        improvement = ((shaped_avg - baseline_avg) / (baseline_avg + 1e-6)) * 100
        print(f"\n  BASELINE avg (last 10): {baseline_avg:.1f}")
        print(f"  SHAPED avg (last 10):   {shaped_avg:.1f}")
        print(f"  Improvement:            {improvement:+.1f}%")
    else:
        print(f"\n  Avg return (last 10 eps): {shaped_avg:.1f}")

    # ---- Per-episode breakdown ----
    print("\n  Episode-by-episode returns:")
    for r in results["episode_results"]:
        marker = " ← HP tuned" if r.episode_id % hp_tune_every == 0 and use_hp_tuning else ""
        print(f"    ep {r.episode_id:3d}: return={r.total_reward:6.1f}  steps={r.num_steps:4d}{marker}")

    # ---- Best episodes ----
    best = results["best_episodes"]
    print("\n  Top episodes by avg return:")
    for row in best:
        print(f"    ep {row['episode_id']}: avg_return={row['avg_return']:.2f}  steps={row['steps']}")

    return results


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CartPole RL Harness Demo")
    parser.add_argument("--episodes", "-n", type=int, default=50,
                        help="Number of episodes (default: 50)")
    parser.add_argument("--no-shaping", action="store_true",
                        help="Disable reward shaping")
    parser.add_argument("--no-hp-tuning", action="store_true",
                        help="Disable HP self-tuning")
    parser.add_argument("--tune-every", type=int, default=10,
                        help="HP tune frequency (default: 10)")
    parser.add_argument("--baseline", action="store_true",
                        help="Run baseline comparison first")
    args = parser.parse_args()

    run_demo(
        num_episodes=args.episodes,
        use_reward_shaping=not args.no_shaping,
        use_hp_tuning=not args.no_hp_tuning,
        hp_tune_every=args.tune_every,
        compare_baseline=args.baseline,
    )
