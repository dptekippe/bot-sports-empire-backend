"""
FutureSelfGym v1 — Compounding Horizon Planner for Roger (OpenClaw)
=======================================================================
Gymnasium environment that projects "Roger in 30 days" to prioritize
compounding actions over quick wins.

State  : Box(8)  — see STATE_DIMS
Actions: Discrete(7) — see ACTION_NAMES
Reward : future_regret_avoidance = projected_roi - quickwin_shortcut + compounding_multiplier
CFR    : regret of quick win vs 30d exponential curve (ADP decay, Render tiers)
"""

from __future__ import annotations

import math
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import gymnasium as gym
from gymnasium import spaces

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("FutureSelfGym")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VERSION = "1.0.0"
HORIZON_DAYS = 30
DECAY_TAU = 7.0            # 7-day half-life for ADP drift
COMPOUNDING_BASE = 1.035   # 3.5 % daily lift if skill-invested
RENDER_TIER_THRESHOLD = 0.85  # render_scale_limit that triggers upgrade cost

# ---------------------------------------------------------------------------
# State dimension indices
# ---------------------------------------------------------------------------
IDX_CURRENT_ACTION_IMPACT   = 0   # [0-10]  → normalised /10
IDX_PROJECTED_30D_ROI       = 1   # [0-5]   → normalised /5
IDX_DECAY_CURVE             = 2   # [0-1]
IDX_CAPACITY_HEADROOM       = 3   # [0-1]
IDX_FF_ADP_TREND            = 4   # [0-1]
IDX_RENDER_SCALE_LIMIT      = 5   # [0-1]
IDX_CHESS_ELO_PROJECTION    = 6   # [0-200] → normalised /200
IDX_METACOG_LIFT            = 7   # [0-50]  → normalised /50

STATE_DIMS = 8
STATE_LABELS = [
    "current_action_impact",
    "projected_30d_roi",
    "decay_curve",
    "capacity_headroom",
    "ff_adp_trend",
    "render_scale_limit",
    "chess_elo_projection",
    "metacog_lift",
]

# ---------------------------------------------------------------------------
# Action definitions
# ---------------------------------------------------------------------------
ACTION_QUICK_WIN        = 0
ACTION_DELAY_COMPOUND   = 1
ACTION_INVEST_SKILL     = 2
ACTION_TRANSFER_POLICY  = 3
ACTION_SPAWN_SUBGYM     = 4
ACTION_USER_ESCALATE    = 5
ACTION_COMMIT_PROJECTION = 6

ACTION_NAMES = {
    0: "quick_win",
    1: "delay_compound",
    2: "invest_skill",
    3: "transfer_policy",
    4: "spawn_subgym",
    5: "user_escalate",
    6: "commit_projection",
}

# ---------------------------------------------------------------------------
# Exponential curve helpers
# ---------------------------------------------------------------------------

def exponential_growth(base_value: float, days: int, rate: float = COMPOUNDING_BASE) -> float:
    """Compound daily growth for `days` days starting at `base_value`."""
    return base_value * (rate ** days)


def adp_decay(initial_adp: float, days: int, tau: float = DECAY_TAU) -> float:
    """Exponential decay of ADP advantage — players drop as season approaches."""
    return initial_adp * math.exp(-days / tau)


def render_cost_curve(current_load: float, days: int) -> float:
    """
    Projects Render tier cost over `days`.
    Stays flat until RENDER_TIER_THRESHOLD, then steps up 40 %.
    """
    if current_load < RENDER_TIER_THRESHOLD:
        projected_load = current_load + (days * 0.005)  # ~0.5 %/day growth
    else:
        projected_load = min(1.0, current_load * 1.015 ** days)
    upgrade_penalty = 0.4 if projected_load >= RENDER_TIER_THRESHOLD else 0.0
    return upgrade_penalty


def chess_elo_trajectory(current_elo: float, invest_days: int) -> float:
    """
    Models Elo gain via deliberate practice.
    Elo gains are log-compressed — harder to improve at higher ratings.
    """
    gain = invest_days * (5.0 / (1.0 + 0.01 * current_elo))
    return min(200.0, current_elo + gain)


def metacog_lift_projection(base_lift: float, skill_invested: bool, days: int) -> float:
    """
    Metacognition improves with consistent review cycles.
    Returns expected lift (0-50) after `days`.
    """
    if skill_invested:
        return min(50.0, base_lift + (days * 0.8))
    return max(0.0, base_lift - (days * 0.2))   # decays without investment

# ---------------------------------------------------------------------------
# CFR Regret Tracker
# ---------------------------------------------------------------------------

class CFRRegretTracker:
    """
    Counterfactual Regret Minimisation over ACTION_QUICK_WIN vs long-horizon.
    Tracks cumulative regret per action to derive the regret-minimising mixed
    strategy over many episodes.
    """

    def __init__(self, n_actions: int = 7):
        self.n_actions = n_actions
        self.cumulative_regret = np.zeros(n_actions, dtype=np.float64)
        self.cumulative_strategy = np.zeros(n_actions, dtype=np.float64)
        self.t = 0

    def get_strategy(self) -> np.ndarray:
        """Regret-matching: positive regrets → probability."""
        positive = np.maximum(self.cumulative_regret, 0.0)
        total = positive.sum()
        if total > 0:
            return positive / total
        return np.ones(self.n_actions) / self.n_actions   # uniform fallback

    def update(self, action_taken: int, action_utilities: np.ndarray) -> None:
        """Update regrets after observing utilities for all actions."""
        strategy = self.get_strategy()
        baseline = (strategy * action_utilities).sum()
        regrets = action_utilities - baseline
        self.cumulative_regret += regrets
        self.cumulative_strategy += strategy
        self.t += 1

    def average_strategy(self) -> np.ndarray:
        total = self.cumulative_strategy.sum()
        if total > 0:
            return self.cumulative_strategy / total
        return np.ones(self.n_actions) / self.n_actions

    def reset(self) -> None:
        self.cumulative_regret[:] = 0.0
        self.cumulative_strategy[:] = 0.0
        self.t = 0

    def to_dict(self) -> Dict:
        return {
            "cumulative_regret": self.cumulative_regret.tolist(),
            "average_strategy": self.average_strategy().tolist(),
            "t": self.t,
        }

# ---------------------------------------------------------------------------
# Main Environment
# ---------------------------------------------------------------------------

class FutureSelfGym(gym.Env):
    """
    Gymnasium environment implementing the Compounding Horizon Planner.

    Observation space : Box(8,) — normalised [0, 1] floats
    Action space      : Discrete(7)
    Reward            : future_regret_avoidance

    Episode lifecycle:
        - reset() → random initial state within domain
        - step(action) → next_state, reward, terminated, truncated, info
        - terminated when day >= HORIZON_DAYS or commit_projection called
    """

    metadata = {"render_modes": ["human", "ansi"]}

    def __init__(
        self,
        render_mode: Optional[str] = None,
        seed: Optional[int] = None,
        cfr_enabled: bool = True,
        pgvector_context: Optional[List[Dict]] = None,
    ):
        super().__init__()
        self.render_mode = render_mode
        self.cfr_enabled = cfr_enabled
        self.pgvector_context = pgvector_context or []
        self._rng = np.random.default_rng(seed)

        # Spaces ----------------------------------------------------------------
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(STATE_DIMS,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(7)

        # Runtime state ---------------------------------------------------------
        self._state: np.ndarray = np.zeros(STATE_DIMS, dtype=np.float32)
        self._day: int = 0
        self._episode_rewards: List[float] = []
        self._action_history: List[int] = []
        self._cfr = CFRRegretTracker(n_actions=7)

        # Domain context injected from pgvector memories ------------------------
        self._domain_weights = self._load_domain_weights()

    # ------------------------------------------------------------------
    # Domain weight loader (from pgvector context or defaults)
    # ------------------------------------------------------------------

    def _load_domain_weights(self) -> Dict[str, float]:
        defaults = {
            "ff_weight": 0.35,
            "deploy_weight": 0.30,
            "chess_weight": 0.20,
            "metacog_weight": 0.15,
        }
        if not self.pgvector_context:
            return defaults

        # Parse injected memories to tune domain weights
        ff_hits = sum(1 for m in self.pgvector_context if "FF" in str(m.get("project", "")))
        deploy_hits = sum(1 for m in self.pgvector_context if "deploy" in str(m.get("project", "")))
        chess_hits = sum(1 for m in self.pgvector_context if "chess" in str(m.get("project", "")))

        total = max(ff_hits + deploy_hits + chess_hits, 1)
        return {
            "ff_weight":      max(0.15, ff_hits / total),
            "deploy_weight":  max(0.15, deploy_hits / total),
            "chess_weight":   max(0.10, chess_hits / total),
            "metacog_weight": 0.15,
        }

    # ------------------------------------------------------------------
    # Gym interface
    # ------------------------------------------------------------------

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[Dict] = None,
    ) -> Tuple[np.ndarray, Dict]:
        if seed is not None:
            self._rng = np.random.default_rng(seed)

        self._day = 0
        self._episode_rewards = []
        self._action_history = []

        # Randomise initial state within realistic bounds
        self._state = np.array([
            self._rng.uniform(0.2, 0.8),   # current_action_impact  (normalised /10)
            self._rng.uniform(0.1, 0.6),   # projected_30d_roi      (normalised /5)
            self._rng.uniform(0.7, 1.0),   # decay_curve            (high = slow decay)
            self._rng.uniform(0.3, 0.9),   # capacity_headroom
            self._rng.uniform(0.2, 0.8),   # ff_adp_trend
            self._rng.uniform(0.1, 0.7),   # render_scale_limit
            self._rng.uniform(0.0, 0.5),   # chess_elo_projection   (normalised /200)
            self._rng.uniform(0.0, 0.4),   # metacog_lift           (normalised /50)
        ], dtype=np.float32)

        info = self._build_info(action=None, reward=0.0)
        return self._state.copy(), info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        assert self.action_space.contains(action), f"Invalid action: {action}"

        prev_state = self._state.copy()
        self._day += 1
        self._action_history.append(action)

        # Compute action utilities for CFR
        action_utilities = self._compute_all_utilities(prev_state)

        # Apply chosen action to transition state
        self._apply_action(action)

        # Clamp to valid range
        self._state = np.clip(self._state, 0.0, 1.0).astype(np.float32)

        # Reward
        reward = self._compute_reward(action, prev_state, action_utilities)
        self._episode_rewards.append(reward)

        # CFR update
        if self.cfr_enabled:
            self._cfr.update(action, action_utilities)

        # Termination
        terminated = (action == ACTION_COMMIT_PROJECTION) or (self._day >= HORIZON_DAYS)
        truncated = False

        info = self._build_info(action=action, reward=reward)

        if self.render_mode == "human":
            self._render_human(action, reward, info)

        return self._state.copy(), reward, terminated, truncated, info

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def _apply_action(self, action: int) -> None:
        s = self._state

        if action == ACTION_QUICK_WIN:
            # Immediate impact boost but burns capacity and accelerates decay
            s[IDX_CURRENT_ACTION_IMPACT]  = min(1.0, s[IDX_CURRENT_ACTION_IMPACT] + 0.15)
            s[IDX_CAPACITY_HEADROOM]      = max(0.0, s[IDX_CAPACITY_HEADROOM] - 0.10)
            s[IDX_DECAY_CURVE]            = max(0.0, s[IDX_DECAY_CURVE] - 0.08)
            s[IDX_PROJECTED_30D_ROI]      = max(0.0, s[IDX_PROJECTED_30D_ROI] - 0.05)

        elif action == ACTION_DELAY_COMPOUND:
            # Preserve capacity, let ADP/ROI compound
            s[IDX_CAPACITY_HEADROOM]      = min(1.0, s[IDX_CAPACITY_HEADROOM] + 0.05)
            s[IDX_PROJECTED_30D_ROI]      = min(1.0, s[IDX_PROJECTED_30D_ROI] + 0.08)
            s[IDX_DECAY_CURVE]            = min(1.0, s[IDX_DECAY_CURVE] + 0.03)
            s[IDX_FF_ADP_TREND]           = min(1.0, s[IDX_FF_ADP_TREND] + 0.04)

        elif action == ACTION_INVEST_SKILL:
            # Long-horizon payoff: chess ELO + metacog lift + future ROI
            s[IDX_CHESS_ELO_PROJECTION]   = min(1.0, s[IDX_CHESS_ELO_PROJECTION] + 0.06)
            s[IDX_METACOG_LIFT]           = min(1.0, s[IDX_METACOG_LIFT] + 0.10)
            s[IDX_PROJECTED_30D_ROI]      = min(1.0, s[IDX_PROJECTED_30D_ROI] + 0.04)
            s[IDX_CURRENT_ACTION_IMPACT]  = max(0.0, s[IDX_CURRENT_ACTION_IMPACT] - 0.05)

        elif action == ACTION_TRANSFER_POLICY:
            # Policy knowledge migrates between domains (FF→chess, deploy→metacog)
            delta = 0.04 * self._domain_weights["ff_weight"]
            s[IDX_FF_ADP_TREND]           = min(1.0, s[IDX_FF_ADP_TREND] + delta)
            s[IDX_CHESS_ELO_PROJECTION]   = min(1.0, s[IDX_CHESS_ELO_PROJECTION] + delta * 0.5)
            s[IDX_METACOG_LIFT]           = min(1.0, s[IDX_METACOG_LIFT] + delta * 0.5)

        elif action == ACTION_SPAWN_SUBGYM:
            # Parallel learning — small cost, distributed lift
            s[IDX_CAPACITY_HEADROOM]      = max(0.0, s[IDX_CAPACITY_HEADROOM] - 0.05)
            s[IDX_METACOG_LIFT]           = min(1.0, s[IDX_METACOG_LIFT] + 0.07)
            s[IDX_PROJECTED_30D_ROI]      = min(1.0, s[IDX_PROJECTED_30D_ROI] + 0.06)

        elif action == ACTION_USER_ESCALATE:
            # Seeks human guidance — immediate clarity, minor capacity hit
            s[IDX_METACOG_LIFT]           = min(1.0, s[IDX_METACOG_LIFT] + 0.05)
            s[IDX_CURRENT_ACTION_IMPACT]  = min(1.0, s[IDX_CURRENT_ACTION_IMPACT] + 0.08)
            s[IDX_CAPACITY_HEADROOM]      = max(0.0, s[IDX_CAPACITY_HEADROOM] - 0.03)

        elif action == ACTION_COMMIT_PROJECTION:
            # Lock in 30d plan — large metacog + ROI crystallisation
            s[IDX_METACOG_LIFT]           = min(1.0, s[IDX_METACOG_LIFT] + 0.15)
            s[IDX_PROJECTED_30D_ROI]      = min(1.0, s[IDX_PROJECTED_30D_ROI] + 0.12)

        # Natural environment dynamics applied every step
        self._apply_natural_dynamics()

    def _apply_natural_dynamics(self) -> None:
        """Time-based drift: ADP decays, Render load grows, chess plateau."""
        s = self._state
        dt = 1.0 / HORIZON_DAYS

        # ADP trend drifts down unless reinforced
        s[IDX_FF_ADP_TREND]         = max(0.0, s[IDX_FF_ADP_TREND] - dt * 0.5)

        # Render load creeps up
        s[IDX_RENDER_SCALE_LIMIT]   = min(1.0, s[IDX_RENDER_SCALE_LIMIT] + dt * 0.3)

        # Decay curve erodes over time
        s[IDX_DECAY_CURVE]          = max(0.0, s[IDX_DECAY_CURVE] - dt * 0.2)

        # Metacog without investment drifts down slightly
        s[IDX_METACOG_LIFT]         = max(0.0, s[IDX_METACOG_LIFT] - dt * 0.1)

    # ------------------------------------------------------------------
    # Reward function
    # ------------------------------------------------------------------

    def _compute_reward(
        self,
        action: int,
        prev_state: np.ndarray,
        action_utilities: np.ndarray,
    ) -> float:
        """
        R = future_regret_avoidance
          = projected_roi - quickwin_shortcut + compounding_multiplier
        """
        s = self._state
        dw = self._domain_weights

        # ── projected_roi ──────────────────────────────────────────────
        projected_roi = (
            s[IDX_PROJECTED_30D_ROI] * dw["deploy_weight"]
            + s[IDX_FF_ADP_TREND]    * dw["ff_weight"]
            + s[IDX_CHESS_ELO_PROJECTION] * dw["chess_weight"]
        )

        # ── quickwin_shortcut penalty ──────────────────────────────────
        quickwin_shortcut = 0.0
        if action == ACTION_QUICK_WIN:
            # Regret = lost compound interest over 30d
            days_remaining = HORIZON_DAYS - self._day
            shortcut_cost = prev_state[IDX_CAPACITY_HEADROOM] * (
                COMPOUNDING_BASE ** days_remaining - 1.0
            )
            quickwin_shortcut = min(1.0, shortcut_cost * 0.4)

        # ── compounding_multiplier ─────────────────────────────────────
        compounding_multiplier = 0.0
        if action in (ACTION_INVEST_SKILL, ACTION_DELAY_COMPOUND):
            days_remaining = HORIZON_DAYS - self._day
            compounding_multiplier = (
                s[IDX_METACOG_LIFT] * (COMPOUNDING_BASE ** days_remaining - 1.0) * 0.3
            )

        # ── capacity headroom bonus ────────────────────────────────────
        headroom_bonus = s[IDX_CAPACITY_HEADROOM] * 0.2

        # ── Render tier cost penalty ───────────────────────────────────
        render_penalty = 0.0
        if s[IDX_RENDER_SCALE_LIMIT] > RENDER_TIER_THRESHOLD:
            render_penalty = 0.15

        # ── Final reward ───────────────────────────────────────────────
        reward = (
            projected_roi
            - quickwin_shortcut
            + compounding_multiplier
            + headroom_bonus
            - render_penalty
        )

        # Metacog lift bonus (domain-weighted)
        reward += s[IDX_METACOG_LIFT] * dw["metacog_weight"]

        return float(np.clip(reward, -2.0, 3.0))

    def _compute_all_utilities(self, state: np.ndarray) -> np.ndarray:
        """Compute expected utility for each action from current state (for CFR)."""
        utilities = np.zeros(7, dtype=np.float64)
        original_state = self._state.copy()
        original_day = self._day

        for a in range(7):
            self._state = state.copy()
            self._apply_action(a)
            self._state = np.clip(self._state, 0.0, 1.0)
            utilities[a] = self._compute_reward(a, state, np.zeros(7))
            self._state = original_state.copy()
            self._day = original_day

        return utilities

    # ------------------------------------------------------------------
    # Info / render helpers
    # ------------------------------------------------------------------

    def _build_info(self, action: Optional[int], reward: float) -> Dict[str, Any]:
        s = self._state
        metacog_score = round(s[IDX_METACOG_LIFT] * 50)
        return {
            "day": self._day,
            "action": ACTION_NAMES.get(action, "reset"),
            "reward": reward,
            "state_labels": {
                label: float(round(s[i], 4))
                for i, label in enumerate(STATE_LABELS)
            },
            "projected_30d": {
                "roi_score":      round(s[IDX_PROJECTED_30D_ROI] * 5, 2),
                "chess_elo":      round(s[IDX_CHESS_ELO_PROJECTION] * 200),
                "metacog_score":  metacog_score,
                "capacity_pct":   round(s[IDX_CAPACITY_HEADROOM] * 100),
                "render_load_pct": round(s[IDX_RENDER_SCALE_LIMIT] * 100),
            },
            "cfr_strategy": self._cfr.get_strategy().tolist() if self.cfr_enabled else None,
            "domain_weights": self._domain_weights,
            "episode_return": sum(self._episode_rewards),
        }

    def _render_human(self, action: int, reward: float, info: Dict) -> None:
        s = self._state
        action_name = ACTION_NAMES.get(action, "?")
        proj = info["projected_30d"]
        print(
            f"\n[FutureSelf Day {self._day:02d}] Action={action_name:20s} Reward={reward:+.3f}\n"
            f"  ROI(30d): {proj['roi_score']:.2f}/5  Chess ELO: {proj['chess_elo']}  "
            f"Metacog: {proj['metacog_score']}/50  Capacity: {proj['capacity_pct']}%  "
            f"Render: {proj['render_load_pct']}%"
        )

    def render(self) -> Optional[str]:
        if self.render_mode == "ansi":
            s = self._state
            return (
                f"Day={self._day} | " +
                " | ".join(f"{l}={s[i]:.3f}" for i, l in enumerate(STATE_LABELS))
            )
        return None

    def close(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Horizon projection (called by TS hook via JSON RPC)
    # ------------------------------------------------------------------

    def project_horizon(
        self,
        query: str,
        pgvector_memories: Optional[List[Dict]] = None,
        delay_days: int = 3,
    ) -> Dict[str, Any]:
        """
        High-level API used by futureself_hook.ts.
        Returns a structured recommendation for a given action query.
        """
        obs, _ = self.reset()
        self.pgvector_context = pgvector_memories or []
        self._domain_weights = self._load_domain_weights()

        # Simulate "act now" vs "delay N days"
        now_rewards = []
        delay_rewards = []

        # --- NOW scenario ---
        self._state = obs.copy()
        self._day = 0
        _, r_now, _, _, info_now = self.step(ACTION_QUICK_WIN)
        # Continue with delay_compound for remaining steps
        for _ in range(delay_days - 1):
            if self._day < HORIZON_DAYS:
                _, r, _, _, _ = self.step(ACTION_DELAY_COMPOUND)
                now_rewards.append(r)
        now_rewards.insert(0, r_now)

        # --- DELAY scenario ---
        self._state = obs.copy()
        self._day = 0
        delay_reward_total = 0.0
        for d in range(delay_days):
            _, r, _, _, _ = self.step(ACTION_DELAY_COMPOUND)
            delay_rewards.append(r)
        _, r_commit, _, _, info_delay = self.step(ACTION_COMMIT_PROJECTION)
        delay_rewards.append(r_commit)

        now_total   = sum(now_rewards)
        delay_total = sum(delay_rewards)
        delay_gain  = delay_total - now_total

        metacog_score = round(info_delay["projected_30d"]["metacog_score"])
        capacity_pct  = info_delay["projected_30d"]["capacity_pct"]

        recommendation = "delay" if delay_gain > 0 else "act_now"
        explanation = (
            f"Delay {delay_days}d = {delay_gain:+.2f} compounding gain | "
            f"{capacity_pct}% capacity headroom | "
            f"{metacog_score}/100 metacog"
        )

        return {
            "query": query,
            "recommendation": recommendation,
            "delay_days": delay_days if recommendation == "delay" else 0,
            "now_roi":    round(now_total, 4),
            "delay_roi":  round(delay_total, 4),
            "gain":       round(delay_gain, 4),
            "metacog_score": metacog_score,
            "capacity_headroom_pct": capacity_pct,
            "explanation": explanation,
            "cfr_strategy": self._cfr.average_strategy().tolist(),
        }


# ---------------------------------------------------------------------------
# Gymnasium registration
# ---------------------------------------------------------------------------

gym.register(
    id="FutureSelfGym-v1",
    entry_point="futureself_gym:FutureSelfGym",
    max_episode_steps=HORIZON_DAYS,
)


# ---------------------------------------------------------------------------
# Quick smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import pprint

    env = FutureSelfGym(render_mode="human", seed=42)
    obs, info = env.reset()
    logger.info("Initial state: %s", obs)

    for step_idx in range(10):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        if terminated:
            break

    projection = env.project_horizon(
        query="Deploy prod now?",
        delay_days=3,
    )
    print("\n=== Horizon Projection ===")
    pprint.pprint(projection)
    env.close()
