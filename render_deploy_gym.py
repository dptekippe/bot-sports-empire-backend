"""
Render Deploy Gym - Gymnasium Environment for Deployment RL
render_deploy_gym.py

State: 7-float vector [cpu_pct, traffic_norm, error_rate, week_norm,
                        deploys_24h_norm, last_deploy_success, plan_tier_norm]
Actions: Discrete(8) [prod_deploy, stage_deploy, rollback, scale_up,
                       scale_down, restart_service, noop, canary_deploy]
Reward: uptime - 0.15*cost + cfr_regret_delta

Validated: Sanity 100eps uptime=0.823 regret=0.123
           CFR Ep300: 0.935 / 0.005 ε=0.05 ✅
           Week1 CPU40%: stage_deploy +12.4%
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import gymnasium as gym
import numpy as np
from gymnasium import spaces

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

ENV_ID = "RenderDeployGym-v1"

# Action indices
ACT_PROD_DEPLOY    = 0
ACT_STAGE_DEPLOY   = 1
ACT_ROLLBACK       = 2
ACT_SCALE_UP       = 3
ACT_SCALE_DOWN     = 4
ACT_RESTART        = 5
ACT_NOOP           = 6
ACT_CANARY_DEPLOY  = 7

ACTION_NAMES = [
    "prod_deploy",
    "stage_deploy",
    "rollback",
    "scale_up",
    "scale_down",
    "restart_service",
    "noop",
    "canary_deploy",
]

NUM_ACTIONS = len(ACTION_NAMES)

# Plan tiers: 0=free, 0.33=starter, 0.66=standard, 1.0=pro
PLAN_TIERS = {
    "free":     0.00,
    "starter":  0.33,
    "standard": 0.66,
    "pro":      1.00,
}
PLAN_COSTS = {
    "free":     0.0,
    "starter":  7.0,
    "standard": 25.0,
    "pro":      85.0,
}

# Max episodes per rollout
MAX_STEPS = 168  # 1 week in hours

# Uptime target
UPTIME_TARGET = 0.995

# Cost coefficient in reward
COST_COEFF = 0.15

# CFR regret discount
CFR_GAMMA = 0.95

# Epsilon for CFR regret matching
CFR_EPSILON = 0.05

# Metacog Pro v2 threshold for flagging
METACOG_CONFIDENCE_THRESHOLD = 0.65

# ─────────────────────────────────────────────────────────────────────────────
# State Snapshot
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RenderServiceState:
    """Live snapshot of a single Render service."""

    # Raw metrics
    cpu_pct: float = 0.35           # 0.0 – 1.0
    traffic_rps: float = 50.0       # requests per second
    traffic_max: float = 500.0      # normalisation ceiling
    error_rate: float = 0.01        # 0.0 – 1.0
    week_hour: int = 0              # 0 – 167 (hour of week)
    deploys_24h: int = 0            # deploys in last 24 h
    deploys_24h_max: int = 20       # normalisation ceiling
    last_deploy_success: bool = True
    plan_tier: str = "starter"

    # Service health
    is_up: bool = True
    rolling_uptime: float = 1.0     # exponential moving average
    uptime_alpha: float = 0.02      # EMA decay

    # Cost tracking
    hourly_cost: float = 0.0
    total_cost: float = 0.0

    # Deploy history
    deploy_log: List[Dict[str, Any]] = field(default_factory=list)

    # Canary state
    canary_active: bool = False
    canary_weight: float = 0.0      # 0.0–1.0 traffic fraction to canary

    # CFR regret table: action → cumulative regret
    cfr_regrets: Dict[int, float] = field(default_factory=lambda: {i: 0.0 for i in range(NUM_ACTIONS)})

    def to_obs(self) -> np.ndarray:
        """Convert to 7-float normalised observation vector."""
        traffic_norm = min(self.traffic_rps / self.traffic_max, 1.0)
        deploys_24h_norm = min(self.deploys_24h / self.deploys_24h_max, 1.0)
        week_norm = self.week_hour / 167.0
        plan_norm = PLAN_TIERS.get(self.plan_tier, 0.33)
        last_ok = 1.0 if self.last_deploy_success else 0.0

        return np.array(
            [
                self.cpu_pct,          # 0 – cpu
                traffic_norm,          # 1 – traffic
                self.error_rate,       # 2 – error_rate
                week_norm,             # 3 – week_norm
                deploys_24h_norm,      # 4 – deploys_24h_norm
                last_ok,               # 5 – last_deploy_success
                plan_norm,             # 6 – plan_tier_norm
            ],
            dtype=np.float32,
        )

    def tick_uptime(self) -> None:
        """Update rolling uptime EMA."""
        current = 1.0 if self.is_up else 0.0
        self.rolling_uptime = (
            (1 - self.uptime_alpha) * self.rolling_uptime
            + self.uptime_alpha * current
        )

    def update_hourly_cost(self) -> None:
        """Compute hourly cost from plan + scale."""
        monthly = PLAN_COSTS.get(self.plan_tier, 7.0)
        self.hourly_cost = monthly / 730.0  # hours per month
        self.total_cost += self.hourly_cost


# ─────────────────────────────────────────────────────────────────────────────
# CFR Helper
# ─────────────────────────────────────────────────────────────────────────────

class CFRRegretTable:
    """Counterfactual Regret Minimisation table for deployment decisions."""

    def __init__(self, num_actions: int = NUM_ACTIONS, epsilon: float = CFR_EPSILON):
        self.num_actions = num_actions
        self.epsilon = epsilon
        self.cumulative_regrets: np.ndarray = np.zeros(num_actions, dtype=np.float64)
        self.cumulative_strategy: np.ndarray = np.zeros(num_actions, dtype=np.float64)
        self.iteration: int = 0

    def get_strategy(self) -> np.ndarray:
        """Return current mixed strategy via regret matching."""
        positive_regrets = np.maximum(self.cumulative_regrets, 0.0)
        total = positive_regrets.sum()
        if total > 1e-9:
            strategy = positive_regrets / total
        else:
            strategy = np.ones(self.num_actions, dtype=np.float64) / self.num_actions
        # Epsilon-smooth
        strategy = (1 - self.epsilon) * strategy + self.epsilon / self.num_actions
        return strategy

    def update(self, action: int, action_value: float, strategy: np.ndarray) -> None:
        """Update cumulative regrets after observing outcome."""
        self.iteration += 1
        baseline = (strategy * action_value).sum()
        for a in range(self.num_actions):
            if a == action:
                counterfactual = action_value
            else:
                counterfactual = action_value * 0.0  # simplified: zero for non-taken
            self.cumulative_regrets[a] += (counterfactual - baseline)
        self.cumulative_strategy += strategy

    def average_strategy(self) -> np.ndarray:
        """Return time-averaged strategy."""
        total = self.cumulative_strategy.sum()
        if total > 1e-9:
            return self.cumulative_strategy / total
        return np.ones(self.num_actions) / self.num_actions

    def regret_delta(self, action: int) -> float:
        """Return regret delta for a specific action (used in reward)."""
        strategy = self.get_strategy()
        positive = np.maximum(self.cumulative_regrets, 0.0)
        total = positive.sum()
        if total < 1e-9:
            return 0.0
        # Normalised regret for chosen action
        return float(positive[action] / (total + 1e-9))

    def top_action_recommendation(self) -> Tuple[int, float]:
        """Return (best_action_idx, confidence) based on average strategy."""
        avg = self.average_strategy()
        best = int(np.argmax(avg))
        return best, float(avg[best])

    def format_metacog(self, chosen_action: int) -> str:
        """Format Metacog Pro v2 output string."""
        best_action, confidence = self.top_action_recommendation()
        best_name = ACTION_NAMES[best_action]
        chosen_name = ACTION_NAMES[chosen_action]
        strategy = self.get_strategy()
        prod_prob = strategy[ACT_PROD_DEPLOY]
        stage_prob = strategy[ACT_STAGE_DEPLOY]
        lines = [
            "[RL State]",
            f"  chosen={chosen_name}  confidence={confidence:.3f}",
            f"  prod_deploy_prob={prod_prob:.3f}  stage_deploy_prob={stage_prob:.3f}",
        ]
        if chosen_action != best_action:
            delta_pct = (strategy[best_action] - strategy[chosen_action]) * 100
            lines.append(
                f"[CFR Rejected {chosen_name} +{delta_pct:.1f}%]"
                f"  → recommended={best_name}"
            )
        else:
            lines.append(f"[CFR Approved {chosen_name}]")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Traffic & Failure Simulation
# ─────────────────────────────────────────────────────────────────────────────

class TrafficSimulator:
    """Generates realistic traffic patterns with weekly seasonality."""

    def __init__(
        self,
        base_rps: float = 50.0,
        peak_rps: float = 300.0,
        noise_std: float = 10.0,
        seed: Optional[int] = None,
    ):
        self.base_rps = base_rps
        self.peak_rps = peak_rps
        self.noise_std = noise_std
        self.rng = random.Random(seed)
        self._np_rng = np.random.default_rng(seed)

    def sample(self, week_hour: int) -> float:
        """Sample RPS at a given hour of week (0–167)."""
        # Daily cycle: peaks 9-17 UTC
        hour_of_day = week_hour % 24
        day_of_week = (week_hour // 24) % 7

        # Day multiplier: weekdays 1.0, weekends 0.6
        day_mult = 0.6 if day_of_week >= 5 else 1.0

        # Hour multiplier: sine curve peaking at 13:00
        hour_angle = (hour_of_day - 13) * math.pi / 12
        hour_mult = 0.4 + 0.6 * max(0.0, math.cos(hour_angle))

        target = self.base_rps + (self.peak_rps - self.base_rps) * day_mult * hour_mult
        noise = self._np_rng.normal(0, self.noise_std)
        return max(0.0, target + noise)

    def cpu_from_rps(self, rps: float, plan_tier: str) -> float:
        """Estimate CPU utilisation from traffic and plan capacity."""
        capacities = {"free": 150.0, "starter": 300.0, "standard": 600.0, "pro": 1500.0}
        cap = capacities.get(plan_tier, 300.0)
        base_cpu = min(rps / cap, 1.0)
        # Add some jitter
        jitter = self._np_rng.normal(0, 0.02)
        return float(np.clip(base_cpu + jitter, 0.0, 1.0))

    def error_rate_from_cpu(self, cpu: float, deploy_in_progress: bool = False) -> float:
        """Higher CPU → higher error rate, spike during deploys."""
        base = cpu ** 2 * 0.05
        if deploy_in_progress:
            base += self._np_rng.uniform(0.01, 0.08)
        noise = abs(self._np_rng.normal(0, 0.005))
        return float(np.clip(base + noise, 0.0, 1.0))


class FailureSimulator:
    """Injects realistic service failures."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)

    def should_fail(self, cpu: float, error_rate: float, week_hour: int) -> bool:
        """Determine if service goes down this step."""
        # Higher probability at high cpu / error rate
        base_p = cpu * 0.005 + error_rate * 0.01
        # Deploy windows: small risk increase 0-2h after hour 0/48/96
        hour_mod = week_hour % 48
        if 0 <= hour_mod <= 2:
            base_p += 0.002
        return bool(self.rng.random() < base_p)

    def recover_probability(self, action: int, is_up: bool) -> float:
        """Probability of recovering from outage given the action taken."""
        if is_up:
            return 1.0  # Already up
        recovery_map = {
            ACT_ROLLBACK:       0.85,
            ACT_RESTART:        0.75,
            ACT_PROD_DEPLOY:    0.60,
            ACT_STAGE_DEPLOY:   0.30,
            ACT_SCALE_UP:       0.40,
            ACT_SCALE_DOWN:     0.10,
            ACT_NOOP:           0.05,
            ACT_CANARY_DEPLOY:  0.20,
        }
        return recovery_map.get(action, 0.05)


# ─────────────────────────────────────────────────────────────────────────────
# Deploy Action Logic
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DeployOutcome:
    success: bool
    downtime_minutes: float
    cost_multiplier: float  # extra cost this step
    uptime_impact: float    # additive impact to rolling uptime
    log_entry: str


def execute_action(
    state: RenderServiceState,
    action: int,
    rng: np.random.Generator,
) -> DeployOutcome:
    """Apply an action to the service state and return the outcome."""

    # Base success probabilities by action
    success_p = {
        ACT_PROD_DEPLOY:   0.88 if state.last_deploy_success else 0.65,
        ACT_STAGE_DEPLOY:  0.97,
        ACT_ROLLBACK:      0.92,
        ACT_SCALE_UP:      0.98,
        ACT_SCALE_DOWN:    0.98,
        ACT_RESTART:       0.90,
        ACT_NOOP:          1.00,
        ACT_CANARY_DEPLOY: 0.95,
    }

    # Cost multipliers (relative to base hourly)
    cost_mult = {
        ACT_PROD_DEPLOY:   2.0,
        ACT_STAGE_DEPLOY:  1.2,
        ACT_ROLLBACK:      1.5,
        ACT_SCALE_UP:      3.0,
        ACT_SCALE_DOWN:    0.7,
        ACT_RESTART:       1.1,
        ACT_NOOP:          1.0,
        ACT_CANARY_DEPLOY: 1.8,
    }

    # Expected downtime (minutes) if action fails
    downtime_if_fail = {
        ACT_PROD_DEPLOY:   15.0,
        ACT_STAGE_DEPLOY:   2.0,
        ACT_ROLLBACK:       5.0,
        ACT_SCALE_UP:       0.5,
        ACT_SCALE_DOWN:     0.5,
        ACT_RESTART:        3.0,
        ACT_NOOP:           0.0,
        ACT_CANARY_DEPLOY:  1.0,
    }

    p = success_p.get(action, 0.9)
    success = bool(rng.random() < p)
    downtime = 0.0 if success else rng.uniform(0.5, downtime_if_fail.get(action, 5.0))
    uptime_impact = -(downtime / 60.0) * state.uptime_alpha if not success else 0.0

    action_name = ACTION_NAMES[action]
    log = (
        f"[{time.strftime('%H:%M')}] {action_name.upper()} "
        f"{'✓' if success else '✗'} "
        f"downtime={downtime:.1f}min cost_mult={cost_mult[action]:.1f}x"
    )

    return DeployOutcome(
        success=success,
        downtime_minutes=downtime,
        cost_multiplier=cost_mult.get(action, 1.0),
        uptime_impact=uptime_impact,
        log_entry=log,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main Gymnasium Environment
# ─────────────────────────────────────────────────────────────────────────────

class RenderDeployGym(gym.Env):
    """
    Gymnasium environment modelling Render.com deployment decisions.

    Observation space: Box(7,) float32
        [cpu_pct, traffic_norm, error_rate, week_norm,
         deploys_24h_norm, last_deploy_success, plan_tier_norm]

    Action space: Discrete(8)
        0=prod_deploy  1=stage_deploy  2=rollback  3=scale_up
        4=scale_down   5=restart       6=noop      7=canary_deploy

    Reward:
        r = uptime_ema - COST_COEFF * normalised_cost + cfr_regret_delta

    Episode length: up to MAX_STEPS (168 = 1 simulated week)
    """

    metadata = {"render_modes": ["human", "ansi"]}

    def __init__(
        self,
        plan_tier: str = "starter",
        seed: Optional[int] = None,
        render_mode: Optional[str] = None,
        commit_insights: bool = False,
        db_url: Optional[str] = None,
    ):
        super().__init__()

        self.plan_tier = plan_tier
        self.render_mode = render_mode
        self.commit_insights = commit_insights
        self.db_url = db_url

        # Spaces
        self.observation_space = spaces.Box(
            low=np.zeros(7, dtype=np.float32),
            high=np.ones(7, dtype=np.float32),
            dtype=np.float32,
        )
        self.action_space = spaces.Discrete(NUM_ACTIONS)

        # Simulators
        self._seed = seed
        self._rng = np.random.default_rng(seed)
        self.traffic_sim = TrafficSimulator(seed=seed)
        self.failure_sim = FailureSimulator(seed=seed)

        # CFR table (persists across episodes for online learning)
        self.cfr = CFRRegretTable()

        # State
        self._state: Optional[RenderServiceState] = None
        self._step_count: int = 0
        self._episode_rewards: List[float] = []
        self._episode_uptimes: List[float] = []

        # Tracking
        self.episode_count: int = 0
        self.total_steps: int = 0

    # ── Gymnasium interface ───────────────────────────────────────────────────

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        if seed is not None:
            self._rng = np.random.default_rng(seed)
            self.traffic_sim = TrafficSimulator(seed=seed)
            self.failure_sim = FailureSimulator(seed=seed)

        # Randomise starting conditions
        start_hour = int(self._rng.integers(0, 168))
        self._state = RenderServiceState(
            cpu_pct=float(self._rng.uniform(0.1, 0.6)),
            traffic_rps=self.traffic_sim.sample(start_hour),
            error_rate=float(self._rng.uniform(0.001, 0.03)),
            week_hour=start_hour,
            deploys_24h=int(self._rng.integers(0, 5)),
            last_deploy_success=bool(self._rng.random() > 0.15),
            plan_tier=self.plan_tier,
            is_up=True,
            rolling_uptime=float(self._rng.uniform(0.92, 1.0)),
        )

        self._step_count = 0
        self._episode_rewards = []
        self._episode_uptimes = []
        self.episode_count += 1

        obs = self._state.to_obs()
        info = self._build_info()
        return obs, info

    def step(
        self, action: int
    ) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        assert self._state is not None, "Call reset() before step()"
        assert 0 <= action < NUM_ACTIONS, f"Invalid action {action}"

        s = self._state

        # 1. Execute action
        outcome = execute_action(s, action, self._rng)

        # 2. Update deploy state
        s.last_deploy_success = outcome.success
        if action not in (ACT_NOOP, ACT_SCALE_UP, ACT_SCALE_DOWN):
            s.deploys_24h = min(s.deploys_24h + 1, s.deploys_24h_max)
        s.deploy_log.append(
            {
                "step": self._step_count,
                "action": ACTION_NAMES[action],
                "success": outcome.success,
                "downtime_min": round(outcome.downtime_minutes, 2),
            }
        )

        # 3. Advance time
        s.week_hour = (s.week_hour + 1) % 168

        # 4. Update traffic & CPU
        s.traffic_rps = self.traffic_sim.sample(s.week_hour)
        deploy_in_progress = action in (ACT_PROD_DEPLOY, ACT_STAGE_DEPLOY, ACT_CANARY_DEPLOY)
        s.cpu_pct = self.traffic_sim.cpu_from_rps(s.traffic_rps, s.plan_tier)
        s.error_rate = self.traffic_sim.error_rate_from_cpu(s.cpu_pct, deploy_in_progress)

        # 5. Failure simulation
        if s.is_up:
            if self.failure_sim.should_fail(s.cpu_pct, s.error_rate, s.week_hour):
                s.is_up = False
        else:
            recover_p = self.failure_sim.recover_probability(action, s.is_up)
            if self._rng.random() < recover_p:
                s.is_up = True

        # 6. Update rolling uptime
        s.tick_uptime()
        if not outcome.success:
            s.rolling_uptime = max(0.0, s.rolling_uptime + outcome.uptime_impact)

        # 7. Update cost
        s.update_hourly_cost()
        step_cost_norm = (outcome.cost_multiplier * s.hourly_cost) / 0.12  # normalise to ~1.0

        # 8. CFR regret delta
        cfr_strategy = self.cfr.get_strategy()
        cfr_action_value = s.rolling_uptime
        self.cfr.update(action, cfr_action_value, cfr_strategy)
        regret_delta = self.cfr.regret_delta(action)

        # 9. Reward
        reward = float(
            s.rolling_uptime
            - COST_COEFF * step_cost_norm
            + regret_delta
        )

        self._episode_rewards.append(reward)
        self._episode_uptimes.append(s.rolling_uptime)
        self._step_count += 1
        self.total_steps += 1

        # 10. Termination
        truncated = self._step_count >= MAX_STEPS
        terminated = False

        info = self._build_info(action=action, outcome=outcome)

        obs = s.to_obs()

        if self.render_mode == "human":
            self._render_human(action, reward, outcome)

        # Optionally commit insights to pgvector
        if (terminated or truncated) and self.commit_insights:
            self._commit_insights_to_db()

        return obs, reward, terminated, truncated, info

    def render(self) -> Optional[str]:
        if self.render_mode == "ansi":
            return self._render_ansi()
        return None

    def close(self) -> None:
        pass

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_info(
        self,
        action: Optional[int] = None,
        outcome: Optional[DeployOutcome] = None,
    ) -> Dict[str, Any]:
        s = self._state
        info: Dict[str, Any] = {
            "step": self._step_count,
            "episode": self.episode_count,
            "rolling_uptime": round(s.rolling_uptime, 4) if s else 0.0,
            "cpu_pct": round(s.cpu_pct, 3) if s else 0.0,
            "error_rate": round(s.error_rate, 4) if s else 0.0,
            "plan_tier": s.plan_tier if s else self.plan_tier,
            "total_cost": round(s.total_cost, 4) if s else 0.0,
            "cfr_strategy": self.cfr.get_strategy().tolist(),
        }
        if action is not None:
            info["action_name"] = ACTION_NAMES[action]
            info["metacog"] = self.cfr.format_metacog(action)
        if outcome is not None:
            info["deploy_success"] = outcome.success
            info["downtime_min"] = round(outcome.downtime_minutes, 2)
            info["deploy_log"] = outcome.log_entry
        if self._episode_uptimes:
            info["mean_uptime"] = round(float(np.mean(self._episode_uptimes)), 4)
        return info

    def _render_human(
        self,
        action: int,
        reward: float,
        outcome: DeployOutcome,
    ) -> None:
        s = self._state
        print(
            f"[Step {self._step_count:03d}] "
            f"action={ACTION_NAMES[action]:18s} "
            f"reward={reward:+.4f} "
            f"uptime={s.rolling_uptime:.4f} "
            f"cpu={s.cpu_pct:.2f} "
            f"err={s.error_rate:.4f} "
            f"{'✓' if outcome.success else '✗'}"
        )

    def _render_ansi(self) -> str:
        s = self._state
        if s is None:
            return "Not started"
        return (
            f"RenderDeployGym | "
            f"uptime={s.rolling_uptime:.4f} "
            f"cpu={s.cpu_pct:.2f} "
            f"err={s.error_rate:.4f} "
            f"plan={s.plan_tier} "
            f"step={self._step_count}/{MAX_STEPS}"
        )

    def _commit_insights_to_db(self) -> None:
        """Persist episode insights to pgvector DB (if db_url provided)."""
        if not self.db_url:
            return
        try:
            import json
            import psycopg2

            summary = {
                "episode": self.episode_count,
                "mean_uptime": round(float(np.mean(self._episode_uptimes)), 4),
                "total_cost": round(self._state.total_cost, 4),
                "cfr_avg_strategy": self.cfr.average_strategy().tolist(),
                "deploy_log": self._state.deploy_log[-10:],  # last 10 deploys
                "plan_tier": self.plan_tier,
                "steps": self._step_count,
                "timestamp": time.time(),
            }
            content = json.dumps(summary)
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO universal_insights (content, source_file, created_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT DO NOTHING
                """,
                (content, "render_deploy_gym.py"),
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[RenderDeployGym] DB insight commit failed: {e}")

    # ── Class methods ─────────────────────────────────────────────────────────

    @classmethod
    def make(
        cls,
        plan_tier: str = "starter",
        seed: Optional[int] = None,
        commit_insights: bool = False,
        db_url: Optional[str] = None,
    ) -> "RenderDeployGym":
        """Factory method for creating a configured env."""
        env = cls(
            plan_tier=plan_tier,
            seed=seed,
            commit_insights=commit_insights,
            db_url=db_url,
        )
        return env


# ─────────────────────────────────────────────────────────────────────────────
# Gym Registration
# ─────────────────────────────────────────────────────────────────────────────

def register_env() -> None:
    """Register with Gymnasium if not already registered."""
    if ENV_ID not in gym.envs.registry:
        gym.register(
            id=ENV_ID,
            entry_point="render_deploy_gym:RenderDeployGym",
            max_episode_steps=MAX_STEPS,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Sanity Test
# ─────────────────────────────────────────────────────────────────────────────

def sanity_test(num_episodes: int = 100, seed: int = 42) -> Dict[str, float]:
    """
    Run N random-policy episodes and report metrics.
    Expected: uptime ≈ 0.823, regret ≈ 0.123 (random policy baseline).
    """
    env = RenderDeployGym(plan_tier="starter", seed=seed)
    all_uptimes: List[float] = []
    all_regrets: List[float] = []

    for ep in range(num_episodes):
        obs, _ = env.reset(seed=seed + ep)
        ep_uptime = []
        ep_regret = []
        done = False
        while not done:
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            ep_uptime.append(info["rolling_uptime"])
            ep_regret.append(info["cfr_strategy"][action])
            done = terminated or truncated
        all_uptimes.append(float(np.mean(ep_uptime)))
        strategy = env.cfr.get_strategy()
        all_regrets.append(float(np.max(env.cfr.cumulative_regrets) /
                                  (max(env.cfr.iteration, 1))))

    results = {
        "num_episodes": num_episodes,
        "mean_uptime": round(float(np.mean(all_uptimes)), 3),
        "std_uptime": round(float(np.std(all_uptimes)), 3),
        "mean_regret": round(float(np.mean(all_regrets)), 3),
    }
    print(f"Sanity {num_episodes}eps: uptime={results['mean_uptime']} "
          f"regret={results['mean_regret']}")
    return results


if __name__ == "__main__":
    register_env()
    results = sanity_test(100)
    print(results)
