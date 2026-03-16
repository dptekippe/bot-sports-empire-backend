"""
train_meta.py - PPO + CFR-HER Training for MetaGym v1
=======================================================
50k steps, MiniMax-Text-01 genius profile.
Neural fusion weights updated jointly with policy.

Usage:
    python train_meta.py                          # 50k steps
    python train_meta.py --steps 10000            # fast run
    python train_meta.py --steps 50000 --eval     # + evaluation
    python train_meta.py --load                   # resume from checkpoint
    python train_meta.py --demo                   # 5-step demo

Outputs:
    ~/.openclaw/gyms/metagym_cfr.json         - CFR strategy
    ~/.openclaw/gyms/metagym_fusion.json      - NeuralFusion weights
    ~/.openclaw/gyms/metagym_matrix.json      - GymMatrix health
    ~/.openclaw/gyms/metagym_ppo.json         - PPO policy
    ~/.openclaw/gyms/metagym_log.jsonl        - per-episode log
    metagym_results.json                      - final summary
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from metagym import (
    N_ACTIONS,
    N_HOOKS,
    STATE_DIM,
    ACTION_NAMES,
    CFR_PRIOR,
    MetaGym,
    build_meta_injection,
    classify_domain,
    GYM_DIR,
)

GYM_DIR.mkdir(parents=True, exist_ok=True)

PPO_PATH     = GYM_DIR / "metagym_ppo.json"
LOG_PATH     = GYM_DIR / "metagym_log.jsonl"
RESULTS_PATH = Path("metagym_results.json")

# ══════════════════════════════════════════════════════════════════════════════
# PPO POLICY - 3-layer with larger hidden for meta-complexity
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class MetaPPOPolicy:
    """
    3-layer policy for MetaGym:
    STATE_DIM(24) → 128 → 64 → N_ACTIONS(8)
    Trained with PPO-clip + entropy regularization.
    """
    W1: np.ndarray
    b1: np.ndarray
    W2: np.ndarray
    b2: np.ndarray
    W3: np.ndarray
    b3: np.ndarray
    lr:       float = 1e-4  # Reduced from 2e-4 for stability
    gamma:    float = 0.99
    eps_clip: float = 0.2
    ent_coef: float = 0.01   # Entropy bonus for exploration
    clip_norm: float = 1.0   # Gradient clipping

    @classmethod
    def init(cls, seed: int = 42) -> "MetaPPOPolicy":
        rng = np.random.default_rng(seed)
        def he(fan_in, fan_out):
            # Smaller init to prevent gradient explosion
            return rng.normal(0, 0.1 * math.sqrt(2.0 / fan_in), (fan_out, fan_in)).astype(np.float64)
        return cls(
            W1=he(STATE_DIM, 128), b1=np.zeros(128),
            W2=he(128, 64),        b2=np.zeros(64),
            W3=he(64, N_ACTIONS),  b3=np.zeros(N_ACTIONS),
        )

    def logits(self, obs: np.ndarray) -> np.ndarray:
        x = obs.astype(np.float64)
        x = np.maximum(self.W1 @ x + self.b1, 0.0)
        x = np.maximum(self.W2 @ x + self.b2, 0.0)
        return self.W3 @ x + self.b3

    def probs(self, obs: np.ndarray) -> np.ndarray:
        lg  = self.logits(obs)
        lg -= lg.max()
        e   = np.exp(lg)
        return e / e.sum()

    def entropy(self, obs: np.ndarray) -> float:
        p   = self.probs(obs)
        p   = np.clip(p, 1e-9, 1.0)
        return -float(np.sum(p * np.log(p)))

    def sample(self, obs: np.ndarray, rng: np.random.Generator) -> int:
        return int(rng.choice(N_ACTIONS, p=self.probs(obs)))

    def update(
        self,
        obs_buf:   List[np.ndarray],
        act_buf:   List[int],
        ret_buf:   List[float],
        old_probs: List[float],
    ) -> float:
        total_loss = 0.0
        for obs, act, ret, old_p in zip(obs_buf, act_buf, ret_buf, old_probs):
            probs = self.probs(obs)
            new_p = probs[act]
            ratio = new_p / (old_p + 1e-8)
            adv   = ret
            clip  = np.clip(ratio, 1 - self.eps_clip, 1 + self.eps_clip)
            ppo_l = -min(ratio * adv, clip * adv)

            # Entropy bonus
            ent   = self.entropy(obs)
            loss  = ppo_l - self.ent_coef * ent

            # Gradient through 3-layer net
            grad_log = np.zeros(N_ACTIONS)
            grad_log[act] = 1.0
            grad_log -= probs

            # Layer 3 gradient
            x1 = obs.astype(np.float64)
            h1 = np.maximum(self.W1 @ x1 + self.b1, 0.0)
            h2 = np.maximum(self.W2 @ h1 + self.b2, 0.0)

            dW3 = np.outer(grad_log, h2) * loss
            db3 = grad_log * loss

            delta = self.W3.T @ (grad_log * loss)
            delta *= (h2 > 0).astype(np.float64)

            dW2 = np.outer(delta, h1)
            db2 = delta.copy()

            delta2 = self.W2.T @ delta
            delta2 *= (h1 > 0).astype(np.float64)

            dW1 = np.outer(delta2, x1)
            db1 = delta2.copy()

            # Gradient clipping (clip_norm=1.0)
            for grad in [dW3, db3, dW2, db2, dW1, db1]:
                norm = np.linalg.norm(grad)
                if norm > self.clip_norm:
                    grad *= self.clip_norm / norm

            self.W3 -= self.lr * dW3
            self.b3 -= self.lr * db3
            self.W2 -= self.lr * dW2
            self.b2 -= self.lr * db2
            self.W1 -= self.lr * dW1
            self.b1 -= self.lr * db1

            total_loss += loss

        return total_loss / max(len(obs_buf), 1)

    def to_dict(self) -> Dict:
        return {k: getattr(self, k).tolist()
                for k in ("W1","b1","W2","b2","W3","b3")}

    @classmethod
    def from_dict(cls, d: Dict) -> "MetaPPOPolicy":
        return cls(**{k: np.array(v) for k, v in d.items()})

    def save(self, path: Path = PPO_PATH):
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path = PPO_PATH) -> "MetaPPOPolicy":
        if path.exists():
            with open(path) as f:
                return cls.from_dict(json.load(f))
        return cls.init()


# ══════════════════════════════════════════════════════════════════════════════
# HER BUFFER - Hindsight Experience Replay
# ══════════════════════════════════════════════════════════════════════════════

class HERBuffer:
    """
    Hindsight Experience Replay: when an episode ends with metacog < 98,
    relabel it as if the terminal state WAS the goal.
    Dramatically improves sample efficiency for sparse rewards.
    """
    def __init__(self, maxlen: int = 2000):
        self.buf: List[Dict] = []
        self.maxlen = maxlen

    def push(self, obs, action, reward, next_obs, done, metacog):
        entry = {
            "obs":     obs.copy(),
            "action":  action,
            "reward":  reward,
            "next_obs":next_obs.copy(),
            "done":    done,
            "metacog": metacog,
        }
        self.buf.append(entry)
        if len(self.buf) > self.maxlen:
            self.buf.pop(0)

    def sample_her(
        self, n: int, rng: np.random.Generator
    ) -> List[Dict]:
        """
        Sample n transitions. With 40% probability, substitute goal
        as the terminal metacog of the episode (hindsight relabeling).
        """
        if not self.buf:
            return []
        idxs = rng.integers(0, len(self.buf), n)
        samples = []
        for i in idxs:
            e = self.buf[i].copy()
            # 40% hindsight relabeling
            if rng.random() < 0.40 and e["metacog"] >= 70:
                # Relabel: pretend this was the goal → give high reward
                e["reward"] = e["reward"] * 1.5 + 0.15
            samples.append(e)
        return samples

    def __len__(self):
        return len(self.buf)


# ══════════════════════════════════════════════════════════════════════════════
# RETURNS
# ══════════════════════════════════════════════════════════════════════════════

def compute_returns(rewards: List[float], gamma: float = 0.99) -> List[float]:
    R = 0.0
    returns = []
    for r in reversed(rewards):
        R = r + gamma * R
        returns.insert(0, R)
    arr = np.array(returns)
    if arr.std() > 1e-8:
        arr = (arr - arr.mean()) / arr.std()
    return arr.tolist()


# ══════════════════════════════════════════════════════════════════════════════
# TRAINING
# ══════════════════════════════════════════════════════════════════════════════

def train(
    total_steps:   int   = 50_000,
    seed:          int   = 42,
    load:          bool  = False,
    verbose:       bool  = True,
    log_interval:  int   = 200,
    save_interval: int   = 2000,
    db_url:        Optional[str] = None,
) -> Dict:
    rng  = np.random.default_rng(seed)
    env  = MetaGym(max_steps=25, db_url=db_url, seed=seed)
    pol  = MetaPPOPolicy.load() if load and PPO_PATH.exists() else MetaPPOPolicy.init(seed)
    her  = HERBuffer(maxlen=3000)

    if load:
        env.load()

    # Metrics
    ep_rewards:    List[float] = []
    ep_metacogs:   List[int]   = []
    ep_truths:     List[float] = []
    step_count     = 0
    ep_count       = 0
    t0             = time.time()

    log_fh = open(LOG_PATH, "a")

    if verbose:
        print(f"\n{'─'*64}")
        print(f"  MetaGym v{__import__('metagym').VERSION} - PPO+CFR-HER Training")
        print(f"  Total steps: {total_steps:,}  |  Seed: {seed}")
        print(f"  Architecture: 15-hook fusion | NeuralFusion 4-layer | HER buffer")
        print(f"{'─'*64}")

    while step_count < total_steps:
        obs, info     = env.reset()
        ep_r          = 0.0
        ep_mc_scores  = []

        obs_buf:  List[np.ndarray] = []
        act_buf:  List[int]        = []
        rew_buf:  List[float]      = []
        old_prob: List[float]      = []

        done = False
        while not done and step_count < total_steps:
            # Blend PPO + CFR
            cfr_s    = env.cfr.get_strategy()
            ppo_p    = pol.probs(obs)
            t_ratio  = min(step_count / total_steps, 0.85)
            blend    = t_ratio * ppo_p + (1 - t_ratio) * cfr_s
            blend    = np.clip(blend, 1e-6, 1.0)
            blend   /= blend.sum()
            
            # NaN guard
            if np.isnan(blend).any() or np.isinf(blend).any():
                blend = np.ones(N_ACTIONS) / N_ACTIONS
            
            action   = int(rng.choice(N_ACTIONS, p=blend))
            old_p    = float(blend[action])

            next_obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            mc   = info["metacog_score"]

            obs_buf.append(obs.copy())
            act_buf.append(action)
            rew_buf.append(reward)
            old_prob.append(old_p)

            # HER push
            her.push(obs, action, reward, next_obs, done, mc)

            ep_r         += reward
            ep_mc_scores.append(mc)
            step_count   += 1
            obs           = next_obs

        # PPO update
        if obs_buf:
            returns  = compute_returns(rew_buf, pol.gamma)
            ppo_loss = pol.update(obs_buf, act_buf, returns, old_prob)
        else:
            ppo_loss = 0.0

        # HER update (extra gradient steps from replay)
        if len(her) >= 64:
            her_batch = her.sample_her(32, rng)
            her_obs   = [e["obs"]    for e in her_batch]
            her_act   = [e["action"] for e in her_batch]
            her_rew   = [e["reward"] for e in her_batch]
            her_probs = [float(pol.probs(o)[a])
                         for o, a in zip(her_obs, her_act)]
            her_ret   = compute_returns(her_rew, pol.gamma)
            pol.update(her_obs, her_act, her_ret, her_probs)

        ep_count += 1
        ep_mc     = int(np.max(ep_mc_scores)) if ep_mc_scores else 0
        ep_truth  = float(env.truth_chain.truth_ratio)

        ep_rewards.append(ep_r)
        ep_metacogs.append(ep_mc)
        ep_truths.append(ep_truth)

        log_fh.write(json.dumps({
            "ep":     ep_count,
            "steps":  step_count,
            "reward": round(ep_r, 4),
            "metacog":ep_mc,
            "truth":  round(ep_truth, 3),
            "loss":   round(float(ppo_loss), 6),
            "domain": env._domain,
        }) + "\n")
        log_fh.flush()

        if verbose and ep_count % log_interval == 0:
            avg_r  = float(np.mean(ep_rewards[-log_interval:]))
            avg_mc = float(np.mean(ep_metacogs[-log_interval:]))
            avg_tr = float(np.mean(ep_truths[-log_interval:]))
            sps    = step_count / max(time.time() - t0, 1e-3)
            cfr_s  = env.cfr.get_strategy()
            top_a  = ACTION_NAMES[int(np.argmax(cfr_s))]
            print(
                f"Ep {ep_count:5d} | Step {step_count:8,d} | "
                f"R {avg_r:6.3f} | MC {avg_mc:5.1f} | Truth {avg_tr:.3f} | "
                f"Top: {top_a:<22s} | {sps:.0f} sps"
            )

        if step_count % save_interval == 0:
            env.save()
            pol.save(PPO_PATH)

    # Final save
    env.save()
    pol.save(PPO_PATH)
    log_fh.close()

    elapsed = time.time() - t0
    summary = {
        "total_steps":   step_count,
        "episodes":      ep_count,
        "elapsed_s":     round(elapsed, 1),
        "sps":           round(step_count / elapsed, 1),
        "mean_reward":   round(float(np.mean(ep_rewards)), 4),
        "max_reward":    round(float(np.max(ep_rewards)), 4),
        "mean_metacog":  round(float(np.mean(ep_metacogs[-100:])), 1),
        "max_metacog":   int(np.max(ep_metacogs)),
        "mean_truth":    round(float(np.mean(ep_truths[-100:])), 3),
        "cfr_avg":       {k: round(float(v), 3)
                          for k, v in zip(ACTION_NAMES, env.cfr.avg().tolist())},
        "her_buffer":    len(her),
    }

    if verbose:
        print(f"\n{'─'*64}")
        print(f"  Training complete!")
        print(f"  Steps: {step_count:,} | Episodes: {ep_count} | {elapsed:.1f}s")
        print(f"  Mean reward: {summary['mean_reward']} | Max MetaCog: {summary['max_metacog']}")
        print(f"  CFR: {summary['cfr_avg']}")
        print(f"{'─'*64}\n")

    return summary


# ══════════════════════════════════════════════════════════════════════════════
# EVALUATION
# ══════════════════════════════════════════════════════════════════════════════

EVAL_QUERIES = [
    "Ty Simpson PFF grades this season?",
    "Should I deploy this microservice to Render - CFR analysis?",
    "Dynasty trade: Bijan Robinson for 2× late 1sts?",
    "Visualize the OpenClaw 15-hook pipeline as a Mermaid diagram.",
    "Debug: why is my Python async loop 3× slower than expected?",
]

def evaluate(
    n:      int           = 5,
    db_url: Optional[str] = None,
    seed:   int           = 99,
) -> Dict:
    env = MetaGym(max_steps=25, db_url=db_url, seed=seed)
    pol = MetaPPOPolicy.load()
    env.load()

    rng    = np.random.default_rng(seed)
    scores = []

    print(f"\n{'─'*64}")
    print(f"  MetaGym v1 - Evaluation ({n} queries)")
    print(f"{'─'*64}")

    for i, query in enumerate(EVAL_QUERIES[:n]):
        # Inject query into env
        env._query  = query
        env._domain = classify_domain(query)
        obs, _      = env.reset()
        ep_r        = 0.0
        done        = False

        while not done:
            action = pol.sample(obs, rng)
            obs, r, term, trunc, info = env.step(action)
            ep_r += r
            done  = term or trunc

        s = env.get_summary()
        mc = s["metacog_score"]
        scores.append(mc)

        print(
            f"  Q{i+1}: '{query[:45]:<45s}'  "
            f"MetaCog {mc:3d}/100  "
            f"Truth {s['truth_ratio']:.3f}  "
            f"Domain: {s['domain']}"
        )

        # Full injection for canonical test
        if "Simpson" in query or "PFF" in query:
            print(f"\n  [Master Injection - '{query}']")
            inj = build_meta_injection(env, query)
            p   = json.loads(inj)
            print(f"    domain:     {p['domain']}")
            print(f"    metacog:    {p['metacog_score']}/100  (target: {p['target_metacog']})")
            print(f"    action:     {p['recommended_action']} ({p['action_confidence']:.1%})")
            print(f"    top5_gyms:  {p['active_gyms']['top5']}")
            print(f"    truth_ratio:{p['system_state']['truth_ratio']}")
            print(f"    directive:  {p['directive'][:120]}...")

    avg_mc = round(float(np.mean(scores)), 1)
    print(f"\n  Average MetaCog: {avg_mc}/100  (target: 98/100)")
    print(f"{'─'*64}\n")

    return {
        "scores":   scores,
        "avg_mc":   avg_mc,
        "target":   98,
        "pass":     avg_mc >= 90,
    }


# ══════════════════════════════════════════════════════════════════════════════
# DEMO
# ══════════════════════════════════════════════════════════════════════════════

def demo():
    print("\n=== MetaGym v1 - Quick Demo ===\n")
    env = MetaGym(max_steps=5, seed=0)
    obs, info = env.reset()
    print(f"Query:  {info['query']}")
    print(f"Domain: {info['domain']}")

    actions = [1, 5, 4]  # thought_forge, truth_audit, canvas_orchestrate
    for a in actions:
        obs, r, term, trunc, info = env.step(a)
        print(f"\nAction: {info['action_name']}")
        print(f"  MetaCog: {info['metacog_score']}/100")
        print(f"  Reward:  {r:.4f}")
        print(f"  Truth:   {info['truth_ratio']}")
        print(f"  Top3:    {info['gym_top3']}")
        print(f"  Directive: {info['directive'][:120]}")

    inj = build_meta_injection(env, "Ty Simpson PFF grades?")
    print("\n\nMaster Injection (preview):")
    print(json.dumps(json.loads(inj), indent=2)[:600] + "...")


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train MetaGym v1")
    parser.add_argument("--steps",     type=int, default=50_000)
    parser.add_argument("--seed",      type=int, default=42)
    parser.add_argument("--load",      action="store_true")
    parser.add_argument("--eval",      action="store_true")
    parser.add_argument("--eval-only", action="store_true")
    parser.add_argument("--demo",      action="store_true")
    parser.add_argument("--db-url",    type=str, default=None)
    args = parser.parse_args()

    if args.demo:
        demo()
        sys.exit(0)

    if args.eval_only:
        r = evaluate(db_url=args.db_url)
        with open(RESULTS_PATH, "w") as f:
            json.dump(r, f, indent=2)
        sys.exit(0)

    summary = train(
        total_steps=args.steps,
        seed=args.seed,
        load=args.load,
        db_url=args.db_url,
    )

    if args.eval:
        ev = evaluate(db_url=args.db_url)
        summary["eval"] = ev

    with open(RESULTS_PATH, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Results → {RESULTS_PATH}")
