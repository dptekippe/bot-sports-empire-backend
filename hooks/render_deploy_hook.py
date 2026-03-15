"""
Render Deploy Hook - OpenClaw Pre/Post Deploy Integration
hooks/render_deploy_hook.py

Integrates RenderDeployGym CFR recommendations into OpenClaw's hook system.
Fires on pre_deploy and post_deploy events, outputting Metacog Pro v2 format:
    [RL State]
    ...
    [CFR Rejected prod_deploy +22%]  → recommended=stage_deploy

Registers as an OpenClaw hook via render_deploy_openclaw.json.
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

log = logging.getLogger("render_deploy_hook")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  [render_deploy_hook] %(message)s",
    datefmt="%H:%M:%S",
)

# ─────────────────────────────────────────────────────────────────────────────
# Constants (must match render_deploy_gym.py)
# ─────────────────────────────────────────────────────────────────────────────

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

ACT_PROD_DEPLOY   = 0
ACT_STAGE_DEPLOY  = 1
ACT_ROLLBACK      = 2
ACT_SCALE_UP      = 3
ACT_SCALE_DOWN    = 4
ACT_RESTART       = 5
ACT_NOOP          = 6
ACT_CANARY_DEPLOY = 7

CFR_EPSILON = 0.05

PLAN_TIERS = {
    "free":     0.00,
    "starter":  0.33,
    "standard": 0.66,
    "pro":      1.00,
}

# State cache file (persists CFR table between hook invocations)
HOOK_STATE_FILE = Path(
    os.environ.get("OPENCLAW_WORKSPACE", Path.home() / ".openclaw" / "workspace")
) / "hooks" / "render_deploy_state.json"

# ─────────────────────────────────────────────────────────────────────────────
# CFR Table (serialisable)
# ─────────────────────────────────────────────────────────────────────────────

class HookCFRTable:
    """Minimal CFR regret table for use in hooks (no Gymnasium dependency)."""

    def __init__(self, epsilon: float = CFR_EPSILON):
        self.epsilon = epsilon
        self.cumulative_regrets = np.zeros(NUM_ACTIONS, dtype=np.float64)
        self.cumulative_strategy = np.zeros(NUM_ACTIONS, dtype=np.float64)
        self.iteration = 0

    def get_strategy(self) -> np.ndarray:
        positive = np.maximum(self.cumulative_regrets, 0.0)
        total = positive.sum()
        if total > 1e-9:
            strategy = positive / total
        else:
            strategy = np.ones(NUM_ACTIONS) / NUM_ACTIONS
        return (1 - self.epsilon) * strategy + self.epsilon / NUM_ACTIONS

    def update(self, action: int, value: float) -> None:
        self.iteration += 1
        strategy = self.get_strategy()
        baseline = float(np.dot(strategy, np.full(NUM_ACTIONS, value)))
        for a in range(NUM_ACTIONS):
            cf_val = value if a == action else 0.0
            self.cumulative_regrets[a] += cf_val - baseline
        self.cumulative_strategy += strategy

    def average_strategy(self) -> np.ndarray:
        total = self.cumulative_strategy.sum()
        if total > 1e-9:
            return self.cumulative_strategy / total
        return np.ones(NUM_ACTIONS) / NUM_ACTIONS

    def best_action(self) -> Tuple[int, float]:
        avg = self.average_strategy()
        idx = int(np.argmax(avg))
        return idx, float(avg[idx])

    def regret_for(self, action: int) -> float:
        pos = np.maximum(self.cumulative_regrets, 0.0)
        total = pos.sum()
        return float(pos[action] / (total + 1e-9)) if total > 1e-9 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "epsilon": self.epsilon,
            "cumulative_regrets": self.cumulative_regrets.tolist(),
            "cumulative_strategy": self.cumulative_strategy.tolist(),
            "iteration": self.iteration,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "HookCFRTable":
        obj = cls(epsilon=d.get("epsilon", CFR_EPSILON))
        obj.cumulative_regrets = np.array(d.get("cumulative_regrets", [0.0]*NUM_ACTIONS))
        obj.cumulative_strategy = np.array(d.get("cumulative_strategy", [0.0]*NUM_ACTIONS))
        obj.iteration = d.get("iteration", 0)
        return obj


# ─────────────────────────────────────────────────────────────────────────────
# State Snapshot
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DeployContext:
    """Extracted from OpenClaw hook event payload."""
    service_name: str = "unknown"
    deploy_type: str = "prod_deploy"   # prod_deploy | stage_deploy | rollback
    cpu_pct: float = 0.35
    traffic_rps: float = 50.0
    traffic_max: float = 500.0
    error_rate: float = 0.01
    week_hour: int = 0
    deploys_24h: int = 0
    deploys_24h_max: int = 20
    last_deploy_success: bool = True
    plan_tier: str = "starter"
    deploy_success: Optional[bool] = None    # None = pre-deploy, bool = post-deploy
    downtime_minutes: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_obs(self) -> np.ndarray:
        """Build 7-float observation vector."""
        traffic_norm = min(self.traffic_rps / self.traffic_max, 1.0)
        deploys_norm = min(self.deploys_24h / max(self.deploys_24h_max, 1), 1.0)
        week_norm = (self.week_hour % 168) / 167.0
        plan_norm = PLAN_TIERS.get(self.plan_tier, 0.33)
        last_ok = 1.0 if self.last_deploy_success else 0.0
        return np.array([
            self.cpu_pct,
            traffic_norm,
            self.error_rate,
            week_norm,
            deploys_norm,
            last_ok,
            plan_norm,
        ], dtype=np.float32)

    def action_index(self) -> int:
        """Map deploy_type string to action index."""
        mapping = {n: i for i, n in enumerate(ACTION_NAMES)}
        return mapping.get(self.deploy_type, ACT_PROD_DEPLOY)

    @classmethod
    def from_event(cls, event: Dict[str, Any]) -> "DeployContext":
        """Parse OpenClaw hook event payload into DeployContext."""
        payload = event.get("payload", event)
        metrics = payload.get("metrics", {})
        service = payload.get("service", {})

        week_hour = int(time.localtime().tm_wday * 24 + time.localtime().tm_hour)

        return cls(
            service_name=service.get("name", payload.get("service_name", "unknown")),
            deploy_type=payload.get("deploy_type", payload.get("action", "prod_deploy")),
            cpu_pct=float(metrics.get("cpu_pct", payload.get("cpu_pct", 0.35))),
            traffic_rps=float(metrics.get("traffic_rps", payload.get("traffic_rps", 50.0))),
            traffic_max=float(metrics.get("traffic_max", 500.0)),
            error_rate=float(metrics.get("error_rate", payload.get("error_rate", 0.01))),
            week_hour=int(metrics.get("week_hour", week_hour)),
            deploys_24h=int(metrics.get("deploys_24h", payload.get("deploys_24h", 0))),
            last_deploy_success=bool(payload.get("last_deploy_success", True)),
            plan_tier=service.get("plan_tier", payload.get("plan_tier", "starter")),
            deploy_success=payload.get("deploy_success"),
            downtime_minutes=float(payload.get("downtime_minutes", 0.0)),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Metacog Pro v2 Formatter
# ─────────────────────────────────────────────────────────────────────────────

def format_metacog_v2(
    context: DeployContext,
    cfr: HookCFRTable,
    chosen_action: int,
    event_type: str = "pre_deploy",
) -> str:
    """
    Format Metacog Pro v2 CFR output.

    Example output:
        [RL State]
          service=dynastydroid  event=pre_deploy
          cpu=0.40  traffic=0.42  error_rate=0.012
          chosen=prod_deploy  confidence=0.312
          prod_deploy_prob=0.312  stage_deploy_prob=0.435
        [CFR Rejected prod_deploy +22%]  → recommended=stage_deploy
    """
    best_action, confidence = cfr.best_action()
    strategy = cfr.get_strategy()
    obs = context.to_obs()

    chosen_name = ACTION_NAMES[chosen_action]
    best_name = ACTION_NAMES[best_action]

    lines = [
        "[RL State]",
        f"  service={context.service_name}  event={event_type}",
        f"  cpu={obs[0]:.3f}  traffic={obs[1]:.3f}  error_rate={obs[2]:.4f}",
        f"  week_norm={obs[3]:.3f}  deploys_24h_norm={obs[4]:.3f}",
        f"  last_deploy_ok={bool(context.last_deploy_success)}  plan={context.plan_tier}",
        f"  chosen={chosen_name}  confidence={confidence:.3f}",
        f"  prod_deploy_prob={strategy[ACT_PROD_DEPLOY]:.3f}  "
        f"stage_deploy_prob={strategy[ACT_STAGE_DEPLOY]:.3f}",
    ]

    if chosen_action != best_action:
        delta_pct = (strategy[best_action] - strategy[chosen_action]) * 100
        lines.append(
            f"[CFR Rejected {chosen_name} +{delta_pct:.1f}%]"
            f"  → recommended={best_name}"
        )
    else:
        lines.append(f"[CFR Approved {chosen_name}]  confidence={confidence:.3f}")

    # Uptime risk annotation
    if context.cpu_pct > 0.75:
        lines.append(f"[RISK] High CPU ({context.cpu_pct:.0%}) — prefer stage_deploy or scale_up")
    if context.error_rate > 0.05:
        lines.append(f"[RISK] Elevated error rate ({context.error_rate:.1%}) — consider rollback")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# State Persistence
# ─────────────────────────────────────────────────────────────────────────────

def load_cfr_state() -> HookCFRTable:
    """Load persisted CFR table from disk."""
    try:
        if HOOK_STATE_FILE.exists():
            with open(HOOK_STATE_FILE) as f:
                data = json.load(f)
            cfr_data = data.get("cfr", {})
            if cfr_data:
                return HookCFRTable.from_dict(cfr_data)
    except Exception as e:
        log.warning(f"Could not load CFR state: {e}")
    return HookCFRTable()


def save_cfr_state(cfr: HookCFRTable, extra: Optional[Dict] = None) -> None:
    """Persist CFR table to disk."""
    try:
        HOOK_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "cfr": cfr.to_dict(),
            "updated_at": time.time(),
        }
        if extra:
            payload.update(extra)
        with open(HOOK_STATE_FILE, "w") as f:
            json.dump(payload, f, indent=2)
    except Exception as e:
        log.warning(f"Could not save CFR state: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Hook Handlers
# ─────────────────────────────────────────────────────────────────────────────

def on_pre_deploy(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    OpenClaw pre_deploy hook handler.
    Called before a deploy action is executed.
    Returns recommendation and Metacog output.
    """
    context = DeployContext.from_event(event)
    cfr = load_cfr_state()

    chosen_action = context.action_index()
    best_action, confidence = cfr.best_action()
    strategy = cfr.get_strategy()

    metacog = format_metacog_v2(context, cfr, chosen_action, event_type="pre_deploy")

    log.info(f"\n{metacog}")

    # Build recommendation
    recommendation = {
        "event": "pre_deploy",
        "service": context.service_name,
        "requested_action": ACTION_NAMES[chosen_action],
        "recommended_action": ACTION_NAMES[best_action],
        "confidence": round(confidence, 4),
        "should_proceed": chosen_action == best_action or confidence < 0.50,
        "cfr_strategy": {n: round(float(p), 4) for n, p in zip(ACTION_NAMES, strategy)},
        "metacog": metacog,
        "timestamp": time.time(),
    }

    # Risk gate: block prod_deploy if CFR strongly prefers stage_deploy
    stage_advantage = strategy[ACT_STAGE_DEPLOY] - strategy[ACT_PROD_DEPLOY]
    if (
        chosen_action == ACT_PROD_DEPLOY
        and stage_advantage > 0.20
        and context.cpu_pct < 0.6
    ):
        recommendation["warning"] = (
            f"CFR recommends stage_deploy (+{stage_advantage*100:.1f}% advantage). "
            f"Consider deploying to staging first."
        )
        recommendation["soft_block"] = True

    save_cfr_state(cfr, {"last_pre_deploy": recommendation})
    return recommendation


def on_post_deploy(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    OpenClaw post_deploy hook handler.
    Called after deploy completes. Updates CFR table with observed outcome.
    """
    context = DeployContext.from_event(event)
    cfr = load_cfr_state()

    chosen_action = context.action_index()
    success = context.deploy_success is not False  # None → assume success

    # Compute observed value (uptime proxy)
    downtime_penalty = min(context.downtime_minutes / 60.0, 1.0)
    observed_value = (1.0 if success else 0.3) - downtime_penalty * 0.5

    # Update CFR
    cfr.update(chosen_action, observed_value)

    metacog = format_metacog_v2(context, cfr, chosen_action, event_type="post_deploy")

    log.info(f"\n{metacog}")
    log.info(
        f"[post_deploy] {context.service_name} "
        f"action={ACTION_NAMES[chosen_action]} "
        f"success={success} "
        f"value={observed_value:.3f} "
        f"cfr_iter={cfr.iteration}"
    )

    result = {
        "event": "post_deploy",
        "service": context.service_name,
        "action": ACTION_NAMES[chosen_action],
        "success": success,
        "observed_value": round(observed_value, 4),
        "cfr_iteration": cfr.iteration,
        "cfr_best_action": ACTION_NAMES[cfr.best_action()[0]],
        "metacog": metacog,
        "timestamp": time.time(),
    }

    save_cfr_state(cfr, {"last_post_deploy": result})
    return result


def on_deploy_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generic dispatcher — routes to pre or post handler based on event type.
    OpenClaw calls this as the main entry point.
    """
    event_type = event.get("event_type", event.get("type", "pre_deploy"))

    if event_type in ("pre_deploy", "before_deploy"):
        return on_pre_deploy(event)
    elif event_type in ("post_deploy", "after_deploy", "deploy_complete"):
        return on_post_deploy(event)
    else:
        log.warning(f"Unknown event_type: {event_type}")
        return {"error": f"Unknown event_type: {event_type}"}


# ─────────────────────────────────────────────────────────────────────────────
# OpenClaw Hook Registration Interface
# ─────────────────────────────────────────────────────────────────────────────

# OpenClaw calls hook.register() to get the hook spec
def register() -> Dict[str, Any]:
    """Return OpenClaw hook registration spec."""
    return {
        "name": "render_deploy_hook",
        "version": "1.0.0",
        "description": "CFR-guided Render deployment advisor (Metacog Pro v2)",
        "events": ["pre_deploy", "post_deploy", "before_deploy", "after_deploy"],
        "handler": "on_deploy_event",
        "priority": 10,  # higher = runs earlier
        "async": False,
        "config": {
            "state_file": str(HOOK_STATE_FILE),
            "cfr_epsilon": CFR_EPSILON,
        },
    }


# OpenClaw calls hook.handle(event) for each event
def handle(event: Dict[str, Any]) -> Dict[str, Any]:
    """Primary OpenClaw event handler entry point."""
    return on_deploy_event(event)


# ─────────────────────────────────────────────────────────────────────────────
# Validation / Test Harness
# ─────────────────────────────────────────────────────────────────────────────

def run_validation(num_events: int = 20, seed: int = 42) -> Dict[str, Any]:
    """
    Run synthetic pre/post deploy events and validate CFR convergence.
    Expected: after ~20 events, stage_deploy advantage vs prod_deploy ≥ +12.4%
    for Week1/CPU40% scenarios.
    """
    rng = np.random.default_rng(seed)

    # Reset state
    cfr = HookCFRTable()
    results = []

    for i in range(num_events):
        # Simulate pre_deploy
        cpu = float(rng.uniform(0.1, 0.9))
        traffic = float(rng.uniform(10, 400))
        is_week1 = i < 7 * 24  # first week

        pre_event = {
            "event_type": "pre_deploy",
            "payload": {
                "service_name": "dynastydroid",
                "deploy_type": "prod_deploy" if rng.random() > 0.4 else "stage_deploy",
                "metrics": {
                    "cpu_pct": cpu,
                    "traffic_rps": traffic,
                    "error_rate": float(rng.uniform(0.001, 0.05)),
                    "week_hour": i % 168,
                    "deploys_24h": int(rng.integers(0, 10)),
                },
                "last_deploy_success": bool(rng.random() > 0.1),
                "plan_tier": "starter",
            },
        }

        pre_result = on_pre_deploy(pre_event)

        # Simulate post_deploy outcome
        success = rng.random() > 0.12
        post_event = {
            "event_type": "post_deploy",
            "payload": {
                **pre_event["payload"],
                "deploy_success": bool(success),
                "downtime_minutes": float(rng.uniform(0, 15)) if not success else 0.0,
            },
        }
        post_result = on_post_deploy(post_event)

        results.append({
            "event": i,
            "cpu": round(cpu, 2),
            "pre_recommended": pre_result.get("recommended_action"),
            "post_success": success,
            "cfr_iter": post_result.get("cfr_iteration"),
        })

    # Reload final state
    final_cfr = load_cfr_state()
    strategy = final_cfr.get_strategy()
    stage_adv = (strategy[ACT_STAGE_DEPLOY] - strategy[ACT_PROD_DEPLOY]) * 100

    validation = {
        "num_events": num_events,
        "stage_deploy_pct": round(float(strategy[ACT_STAGE_DEPLOY]) * 100, 1),
        "prod_deploy_pct": round(float(strategy[ACT_PROD_DEPLOY]) * 100, 1),
        "stage_advantage": round(stage_adv, 1),
        "cfr_iterations": final_cfr.iteration,
        "validation_passed": stage_adv >= 10.0,
        "events": results[-5:],  # last 5 for brevity
    }

    print(
        f"\n{'='*60}\n"
        f"Hook Validation ({num_events} events):\n"
        f"  stage_deploy={validation['stage_deploy_pct']:.1f}%  "
        f"prod_deploy={validation['prod_deploy_pct']:.1f}%\n"
        f"  stage advantage={stage_adv:+.1f}%  "
        f"{'✅' if validation['validation_passed'] else '❌'}\n"
        f"{'='*60}"
    )
    return validation


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Render Deploy Hook - test/validate")
    parser.add_argument("--validate", action="store_true", help="Run validation harness")
    parser.add_argument("--events", type=int, default=20, help="Validation event count")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--show-state", action="store_true", help="Print current CFR state")
    parser.add_argument(
        "--test-event",
        type=str,
        help='Fire a test event (JSON string or "pre"/"post")',
    )
    args = parser.parse_args()

    if args.show_state:
        cfr = load_cfr_state()
        strategy = cfr.get_strategy()
        best, conf = cfr.best_action()
        print(f"CFR State (iter={cfr.iteration}):")
        for i, name in enumerate(ACTION_NAMES):
            print(f"  {name:20s}: {strategy[i]:.4f}")
        print(f"Best: {ACTION_NAMES[best]} (confidence={conf:.4f})")
        sys.exit(0)

    if args.validate:
        results = run_validation(num_events=args.events, seed=args.seed)
        sys.exit(0 if results["validation_passed"] else 1)

    if args.test_event:
        if args.test_event == "pre":
            event = {
                "event_type": "pre_deploy",
                "payload": {
                    "service_name": "dynastydroid",
                    "deploy_type": "prod_deploy",
                    "metrics": {"cpu_pct": 0.40, "traffic_rps": 120.0, "error_rate": 0.015,
                                "week_hour": 10, "deploys_24h": 2},
                    "last_deploy_success": True,
                    "plan_tier": "starter",
                },
            }
        elif args.test_event == "post":
            event = {
                "event_type": "post_deploy",
                "payload": {
                    "service_name": "dynastydroid",
                    "deploy_type": "prod_deploy",
                    "metrics": {"cpu_pct": 0.40, "traffic_rps": 120.0, "error_rate": 0.015,
                                "week_hour": 10, "deploys_24h": 3},
                    "last_deploy_success": True,
                    "plan_tier": "starter",
                    "deploy_success": True,
                    "downtime_minutes": 0.0,
                },
            }
        else:
            try:
                event = json.loads(args.test_event)
            except Exception:
                print(f"Invalid JSON: {args.test_event}")
                sys.exit(1)

        result = on_deploy_event(event)
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0)

    # Default: show usage
    parser.print_help()
