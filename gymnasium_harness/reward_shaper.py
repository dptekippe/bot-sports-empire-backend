"""
reward_shaper.py — Reward Shaping via pgvector Memory

Uses the hybrid search (similarity + importance + recency) from pgvector
to determine whether the current state has historically led to good or bad
outcomes, then adds a bonus or penalty to the environment reward.

Key idea (Potential-Based Reward Shaping, Ng et al. 1999):
    F(s,s') = γ·Φ(s') - Φ(s) + bonus(s)

We implement a simplified version:
    shaped_reward = original_reward + shaping_bonus
    shaping_bonus ∈ [-penalty_weight, +bonus_weight]

The bonus is computed from the return delta vs similar historical states.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pgvector_client import PgVectorClient


# ============ SHAPING RESULT ============

@dataclass
class ShapingResult:
    shaped_reward: float
    original_reward: float
    bonus: float
    similar_states_found: bool
    avg_similar_return: float
    return_delta: float
    top_memories: List[Dict[str, Any]]


# ============ REWARD SHAPER ============

class RewardShaper:
    """
    Reward shaper that queries pgvector for similar past states and
    modifies the environment reward based on historical performance.
    """

    def __init__(
        self,
        pg_client: PgVectorClient,
        min_similar_memories: int = 1,
        warmup_episodes: int = 3,
    ):
        """
        Args:
            pg_client:          PgVectorClient for memory recall.
            min_similar_memories: Minimum # of similar memories needed
                                  before applying shaping.
            warmup_episodes:    Number of initial episodes to skip shaping
                                  (so pgvector can accumulate memories).
        """
        self.pg = pg_client
        self.min_similar_memories = min_similar_memories
        self.warmup_episodes = warmup_episodes
        self._episode_count = 0

    def shape_reward(
        self,
        original_reward: float,
        state: Any,
        next_state: Any,
        action: Any,
        recall_top_k: int = 5,
        bonus_weight: float = 0.1,
        penalty_weight: float = 0.05,
    ) -> tuple[float, Dict[str, Any]]:
        """
        Compute the shaped reward and pgvector context for one step.

        Returns:
            (shaped_reward, context_dict)
            The context dict is stored alongside the memory and can be
            used for inspection / HP tuning.
        """
        self._episode_count += 1

        # Skip during warmup
        if self._episode_count <= self.warmup_episodes * 50:  # ~50 steps/ep
            return original_reward, {
                "similar_state_found": False,
                "shaping_applied": False,
                "return_delta": 0.0,
                "reason": "warmup",
            }

        # Query pgvector for similar states
        memories = self.pg.recall(state, top_k=recall_top_k, min_importance=1.0)

        if len(memories) < self.min_similar_memories:
            return original_reward, {
                "similar_state_found": False,
                "shaping_applied": False,
                "return_delta": 0.0,
                "reason": "no_similar_memories",
            }

        # Compute metrics from similar memories
        similar_returns = [
            m["episode_return"]
            for m in memories
            if m.get("episode_return") is not None
        ]
        if not similar_returns:
            return original_reward, {
                "similar_state_found": False,
                "shaping_applied": False,
                "return_delta": 0.0,
                "reason": "no_return_data",
            }

        avg_similar_return = float(np.mean(similar_returns))
        # Use global average as baseline
        global_avg = self.pg.get_stats().get("avg_episode_return", 0.0) or 0.0
        return_delta = avg_similar_return - global_avg

        # Compute shaping bonus: bounded to [-penalty_weight, +bonus_weight]
        # Scale by the magnitude of the return delta
        scale = min(1.0, abs(return_delta) / 50.0)  # normalise by 50-step expected return
        if return_delta > 0:
            shaping_bonus = bonus_weight * scale
        else:
            shaping_bonus = -penalty_weight * scale

        shaped_reward = original_reward + shaping_bonus

        ctx = {
            "similar_state_found": True,
            "shaping_applied": True,
            "avg_similar_return": avg_similar_return,
            "global_avg_return": global_avg,
            "return_delta": return_delta,
            "shaping_bonus": shaping_bonus,
            "num_similar_memories": len(memories),
            "top_memories": [
                {
                    "episode_id": m["episode_id"],
                    "action": m["action"],
                    "reward": m["reward"],
                    "episode_return": m.get("episode_return"),
                    "importance": m["importance"],
                }
                for m in memories[:3]
            ],
        }

        return shaped_reward, ctx

    def compute_potential(self, state: Any) -> float:
        """
        Compute Φ(s) — the potential function for a state.
        Used for potential-based shaping verification (Ng et al. 1999).

        We define Φ(s) as the average episode_return of similar states.
        """
        memories = self.pg.recall(state, top_k=5)
        if not memories:
            return 0.0
        returns = [
            m["episode_return"]
            for m in memories
            if m.get("episode_return") is not None
        ]
        return float(np.mean(returns)) if returns else 0.0

    def shaping_summary(self) -> Dict[str, Any]:
        """Return a human-readable summary of the shaper's state."""
        stats = self.pg.get_stats()
        return {
            "warmup_complete": self._episode_count > self.warmup_episodes * 50,
            "total_steps_seen": self._episode_count,
            "pgvector_stats": stats,
        }
