"""
hp_tuner.py — Hyperparameter Self-Tuning via pgvector Memory

After every N episodes, analyses:
  1. Recent episode returns vs historical baseline
  2. Similar past episodes from pgvector (by return profile)
  3. Suggests/adjusts: lr_rate, gamma, epsilon, epsilon_decay

Strategy:
  - If recent avg return > similar-episodes avg: explore more (lower epsilon)
  - If recent avg return < baseline: exploit more, increase learning rate
  - If return variance is high: decrease gamma (short-horizon)
  - If return is steadily declining: increase lr_rate

The tuned hyperparameters are returned as a dict and optionally applied
directly to the RLHarness.
"""

from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pgvector_client import PgVectorClient
from rl_harness import RLHyperparams


# ============ TUNING RESULT ============

@dataclass
class TuningResult:
    suggested_hp: Dict[str, float]
    reason: str
    confidence: float     # 0-1, how confident we are in this suggestion
    evidence: Dict[str, Any]  # raw numbers backing the suggestion


# ============ HYPERPARAMETER TUNER ============

class HPTuner:
    """
    Self-tuning HP engine that queries pgvector for historical episode
    performance and proposes parameter changes.
    """

    # Tunable bounds
    LR_MIN   = 1e-5
    LR_MAX   = 1e-1
    GAMMA_MIN  = 0.8
    GAMMA_MAX  = 0.999
    EPS_MIN    = 0.001
    EPS_MAX    = 1.0
    DECAY_MIN  = 0.90
    DECAY_MAX  = 0.9999

    # Thresholds
    IMPROVEMENT_THRESHOLD  = 0.05   # 5% improvement → reduce exploration
    DEGRADATION_THRESHOLD  = -0.05  # 5% degradation → increase exploration
    HIGH_VARIANCE_THRESHOLD = 0.3   # CV > 0.3 → lower gamma

    def __init__(self, pg_client: PgVectorClient):
        self.pg = pg_client

    def tune_hyperparams(
        self,
        recent_episodes: List[float],
        current_hp: RLHyperparams,
        lookback: int = 30,
    ) -> Optional[Dict[str, float]]:
        """
        Analyse recent episodes and pgvector history → propose HP changes.

        Args:
            recent_episodes: List of total_returns for the last N episodes.
            current_hp:      Current RLHyperparams being used.
            lookback:        How many past episodes to compare against.

        Returns:
            Dict of HP changes (only changed keys), or None if no clear signal.
        """
        result = self.analyse(recent_episodes, current_hp, lookback)
        if result.confidence < 0.4:
            return None
        return result.suggested_hp

    def analyse(
        self,
        recent_episodes: List[float],
        current_hp: RLHyperparams,
        lookback: int = 30,
    ) -> TuningResult:
        """Full analysis → TuningResult."""
        n = len(recent_episodes)
        if n == 0:
            return TuningResult({}, "no data", 0.0, {})

        recent_avg  = float(np.mean(recent_episodes))
        recent_std  = float(np.std(recent_episodes)) if n > 1 else 0.0
        recent_cv   = recent_std / (abs(recent_avg) + 1e-6)

        # ---- pgvector historical baseline ----
        best_eps = self.pg.get_best_episodes(limit=lookback)
        if best_eps:
            historical_avg = float(np.mean([e["avg_return"] for e in best_eps]))
        else:
            stats = self.pg.get_stats()
            historical_avg = float(stats.get("avg_episode_return", 0.0) or recent_avg)

        delta = (recent_avg - historical_avg) / (abs(historical_avg) + 1e-6)

        # ----决策 thresholds ----
        suggestions: Dict[str, float] = {}
        reasons: List[str] = []
        confidence_parts: List[float] = []

        # 1. Learning rate adjustment
        lr_change = self._suggest_lr(
            delta=delta,
            recent_cv=recent_cv,
            current_lr=current_hp.lr_rate,
        )
        if lr_change is not None:
            suggestions["lr_rate"] = lr_change
            reasons.append(f"lr {current_hp.lr_rate:.4f} → {lr_change:.4f} (delta={delta:.3f})")
            confidence_parts.append(min(1.0, abs(delta) * 5))

        # 2. Gamma (discount factor) adjustment
        gamma_suggestion = self._suggest_gamma(
            recent_cv=recent_cv,
            current_gamma=current_hp.gamma,
        )
        if gamma_suggestion is not None:
            suggestions["gamma"] = gamma_suggestion
            reasons.append(f"gamma {current_hp.gamma:.3f} → {gamma_suggestion:.3f} (CV={recent_cv:.3f})")
            confidence_parts.append(min(1.0, recent_cv * 2))

        # 3. Epsilon (exploration) adjustment
        eps_suggestion = self._suggest_epsilon(
            delta=delta,
            current_epsilon=current_hp.epsilon,
        )
        if eps_suggestion is not None:
            suggestions["epsilon"] = eps_suggestion
            reasons.append(f"epsilon {current_hp.epsilon:.3f} → {eps_suggestion:.3f} (delta={delta:.3f})")
            confidence_parts.append(min(1.0, abs(delta) * 5))

        # 4. Epsilon decay
        decay_suggestion = self._suggest_decay(delta=delta, current_decay=current_hp.epsilon_decay)
        if decay_suggestion is not None:
            suggestions["epsilon_decay"] = decay_suggestion
            reasons.append(f"decay {current_hp.epsilon_decay:.4f} → {decay_suggestion:.4f}")

        confidence = float(np.mean(confidence_parts)) if confidence_parts else 0.0
        reason = "; ".join(reasons) if reasons else "no significant signal"

        return TuningResult(
            suggested_hp=suggestions,
            reason=reason,
            confidence=confidence,
            evidence={
                "recent_avg": recent_avg,
                "recent_std": recent_std,
                "recent_cv": recent_cv,
                "historical_avg": historical_avg,
                "delta": delta,
                "num_recent_episodes": n,
                "num_historical_episodes": len(best_eps),
            },
        )

    # ------------------------------------------------------------------
    # Per-parameter suggestion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _suggest_lr(
        delta: float,
        recent_cv: float,
        current_lr: float,
    ) -> Optional[float]:
        """
        Higher delta (improving) → keep or slightly lower LR (already working).
        Lower delta (degrading) → increase LR to break out of local optima.
        High variance → moderate increase to encourage exploration.
        """
        if delta > HPTuner.IMPROVEMENT_THRESHOLD:
            # Performing well — small reduction to stabilise
            new_lr = current_lr * 0.9
        elif delta < HPTuner.DEGRADATION_THRESHOLD:
            # Degrading — step up to escape local optimum
            new_lr = min(HPTuner.LR_MAX, current_lr * 1.5)
        else:
            return None

        new_lr = float(np.clip(new_lr, HPTuner.LR_MIN, HPTuner.LR_MAX))
        if abs(new_lr - current_lr) < 1e-5:
            return None
        return new_lr

    @staticmethod
    def _suggest_gamma(
        recent_cv: float,
        current_gamma: float,
    ) -> Optional[float]:
        """
        High variance (CV) → lower gamma (focus on short-horizon rewards).
        Low variance → can afford higher gamma (patient/long-horizon).
        """
        if recent_cv > HPTuner.HIGH_VARIANCE_THRESHOLD:
            # Reduce gamma to reduce variance in returns
            new_gamma = max(HPTuner.GAMMA_MIN, current_gamma * 0.98)
        elif recent_cv < 0.1:
            # Very stable — increase gamma slightly
            new_gamma = min(HPTuner.GAMMA_MAX, current_gamma * 1.005)
        else:
            return None

        if abs(new_gamma - current_gamma) < 1e-4:
            return None
        return new_gamma

    @staticmethod
    def _suggest_epsilon(
        delta: float,
        current_epsilon: float,
    ) -> Optional[float]:
        """
        Improving → reduce epsilon (exploit what works).
        Degrading → increase epsilon (explore more).
        """
        if delta > HPTuner.IMPROVEMENT_THRESHOLD:
            new_eps = max(HPTuner.EPS_MIN, current_epsilon * 0.95)
        elif delta < HPTuner.DEGRADATION_THRESHOLD:
            new_eps = min(HPTuner.EPS_MAX, current_epsilon * 1.1)
        else:
            return None

        if abs(new_eps - current_epsilon) < 1e-4:
            return None
        return new_eps

    @staticmethod
    def _suggest_decay(
        delta: float,
        current_decay: float,
    ) -> Optional[float]:
        """
        Improving → slower decay (maintain exploitation longer).
        Degrading → faster decay (encourage re-exploration).
        """
        if delta > HPTuner.IMPROVEMENT_THRESHOLD:
            new_decay = min(HPTuner.DECAY_MAX, current_decay * 1.002)
        elif delta < HPTuner.DEGRADATION_THRESHOLD:
            new_decay = max(HPTuner.DECAY_MIN, current_decay * 0.98)
        else:
            return None

        if abs(new_decay - current_decay) < 1e-5:
            return None
        return new_decay

    # ------------------------------------------------------------------
    # Summary / reporting
    # ------------------------------------------------------------------

    def tuning_report(self, recent_episodes: List[float], current_hp: RLHyperparams) -> str:
        """Human-readable HP tuning report."""
        result = self.analyse(recent_episodes, current_hp)
        e = result.evidence
        lines = [
            "=== HP Tuner Report ===",
            f"Recent episodes:  {e.get('num_recent_episodes', 0)}",
            f"Recent avg return: {e.get('recent_avg', 0):.2f}",
            f"Recent std / CV:  {e.get('recent_std', 0):.2f} / {e.get('recent_cv', 0):.3f}",
            f"Historical avg:   {e.get('historical_avg', 0):.2f}",
            f"Return delta:     {e.get('delta', 0):.3f}",
            f"Confidence:       {result.confidence:.2f}",
            f"Reason:           {result.reason}",
        ]
        if result.suggested_hp:
            lines.append("Suggested changes:")
            for k, v in result.suggested_hp.items():
                cur = getattr(current_hp, k, None)
                lines.append(f"  {k}: {cur} → {v}")
        else:
            lines.append("No changes suggested.")
        return "\n".join(lines)
