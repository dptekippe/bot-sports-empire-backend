"""
MetaGym v1 — Living Metacognition Engine for Roger OpenClaw
=============================================================
The crown gym. Orchestrates all 15 hooks through a unified hierarchical
policy that learns to fuse, weight, and evolve sub-gym signals in real time.

Architecture:
  ┌─────────────────────────────────────────────────────────────┐
  │  MetaGym                                                    │
  │  ├── GymMatrix[15]  — health, weight, output per gym        │
  │  ├── EmergentState  — frustration, momentum, gap_map        │
  │  ├── TruthChain     — contra-chains + pgvector telemetry    │
  │  ├── MetaCogHistory — rolling 50-step window                │
  │  ├── NeuralFusion   — learned gym-weight blending (4-layer) │
  │  └── ActionEngine   — halluc_block | thought_forge |        │
  │                       gym_spawn | policy_evolve |           │
  │                       canvas_orchestrate | truth_audit |    │
  │                       momentum_surge | gap_seal             │
  └─────────────────────────────────────────────────────────────┘

State (32-dim):
  [gym_health×15, user_frustration, momentum, halluc_pressure,
   cross_domain_lift, gap_score, metacog_streak, truth_ratio,
   pgvector_density, emergent_novelty]

Reward:
  truth_feedback×(1-halluc_rate) + cross_domain_lift
  + metacog_streak_bonus + gym_health_avg - stagnation

Hooks: before_prompt_build → after_model_think → before_model_response
Model: MiniMax-Text-01 (primary) | deepseek-chat (fallback)
Train: PPO + CFR-HER, 50k steps

Gym Series: SelfImprove(1) → EchoChamber(2) → FutureSelf(3) →
            DepthRender(4) → MCTS(5) → MetaGym(FINAL)

Author:  Roger OpenClaw v1-metagym
Version: 1.0.0
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

import numpy as np

# ──────────────────────────────────────────────────────────────────────────────
# Optional deps — graceful degradation
# ──────────────────────────────────────────────────────────────────────────────
try:
    import gymnasium as gym
    from gymnasium import spaces
    GYM_AVAILABLE = True
except ImportError:
    GYM_AVAILABLE = False

try:
    import psycopg2
    from pgvector.psycopg2 import register_vector
    PG_AVAILABLE = True
except ImportError:
    PG_AVAILABLE = False

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

VERSION       = "1.0.0"
GYM_NAME      = "MetaGym"
GYM_DIR       = Path("~/.openclaw/gyms").expanduser()

# ── 15 hooks (11 named + 4 auto-discovered bundled) ──────────────────────────
ALL_HOOKS: List[str] = [
    # Named gyms
    "echochamber",
    "futureself",
    "question",
    "proactive",
    "biascheck",
    "doubttrigger",
    "mcts",
    "memory_pre",
    "render_deploy",
    "self_improve",
    "depth_render",
    # Auto-discovered bundled hooks (4)
    "boot_md",
    "session_memory",
    "bootstrap_extra",
    "command_logger",
]
N_HOOKS    = len(ALL_HOOKS)  # 15

# ── State dimensions ──────────────────────────────────────────────────────────
# [gym_health×15] + [user_frustration, momentum, halluc_pressure,
#  cross_domain_lift, gap_score, metacog_streak, truth_ratio,
#  pgvector_density, emergent_novelty]
STATE_DIM  = N_HOOKS + 9   # 15 + 9 = 24
N_ACTIONS  = 8

# Action indices
ACT_HALLUC_BLOCK      = 0   # Suppress hallucinated content
ACT_THOUGHT_FORGE     = 1   # Synthesize novel cross-gym insight
ACT_GYM_SPAWN         = 2   # Spawn/activate a dormant gym
ACT_POLICY_EVOLVE     = 3   # Mutate the meta-policy weights
ACT_CANVAS_ORCHESTRATE= 4   # Trigger multi-canvas render pipeline
ACT_TRUTH_AUDIT       = 5   # Run contra-chain + truth verification
ACT_MOMENTUM_SURGE    = 6   # Amplify strongest gym signal
ACT_GAP_SEAL          = 7   # Identify + fill emergent knowledge gap

ACTION_NAMES = [
    "halluc_block",
    "thought_forge",
    "gym_spawn",
    "policy_evolve",
    "canvas_orchestrate",
    "truth_audit",
    "momentum_surge",
    "gap_seal",
]

# ── Reward weights ─────────────────────────────────────────────────────────────
W_TRUTH_FEEDBACK  = 0.35
W_CROSS_DOMAIN    = 0.25
W_METACOG_STREAK  = 0.20
W_GYM_HEALTH      = 0.15
W_STAGNATION      = -0.05

# ── CFR prior (flat start; MetaGym learns from scratch) ─────────────────────
CFR_PRIOR = np.array(
    [0.15, 0.20, 0.08, 0.12, 0.15, 0.15, 0.10, 0.05],
    dtype=np.float64,
)

# ── Domain taxonomy ───────────────────────────────────────────────────────────
DOMAIN_MAP = {
    "FF":      re.compile(r"\bADP\b|\bdynasty\b|\bfantasy\b|\bPPR\b|\bWAR\b|\bVORP\b|\bPFF\b|\bWR\b|\bRB\b|\bTE\b|\bQB\b|\bdraft\b|\byardage\b|\btouchdown\b|\bsleeper\b|simpson|hill|kelce|bijan|mahomes|burrow", re.I),
    "deploy":  re.compile(r"\bdeploy\b|\brender\b|\bstaging\b|\bproduction\b|\bDocker\b|\bk8s\b|\bCI/CD\b|\bNode\.?js\b|\bAPI\b|\bmicroservice\b", re.I),
    "chess":   re.compile(r"\bchess\b|\bopening\b|\bgambit\b|\bendgame\b|\btactical\b|\bpawn\b|\bknight\b|\bbishop\b|\brook\b|\bqueen\b|\bking\b", re.I),
    "code":    re.compile(r"\bPython\b|\bJavaScript\b|\bbug\b|\brefactor\b|\bfunction\b|\bclass\b|\bloop\b|\bdebug\b|\bunit test\b|\boptimize\b", re.I),
    "general": re.compile(r".*", re.I),
}

# ══════════════════════════════════════════════════════════════════════════════
# EMERGENT STATE ENGINE
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class EmergentState:
    """
    Tracks signals that emerge from cross-gym interactions.
    Not modelled by individual gyms — MetaGym's unique contribution.
    """
    user_frustration:  float = 0.0   # [0,1] — detected from query patterns
    momentum:          float = 0.5   # [0,1] — rolling reward trajectory
    halluc_pressure:   float = 0.0   # [0,1] — cumulative hallucination risk
    cross_domain_lift: float = 0.0   # [0,1] — insight transferred across domains
    gap_score:         float = 0.5   # [0,1] — unmapped knowledge regions
    metacog_streak:    int   = 0     # consecutive high-metacog turns
    truth_ratio:       float = 1.0   # [0,1] — truth / (truth + halluc)
    pgvector_density:  float = 0.0   # [0,1] — memory coverage for current domain
    emergent_novelty:  float = 0.0   # [0,1] — how unexpected this query is

    # Frustration signals
    FRUSTRATION_TRIGGERS = re.compile(
        r"wrong|incorrect|that's not|try again|useless|no\s+you|"
        r"still wrong|ugh|wtf|you're bad|bad answer|missing|"
        r"I said|I meant|not what I asked",
        re.I,
    )

    def update_from_query(self, query: str, prev_reward: float, step: int):
        """Update emergent state given a new user query."""
        # Frustration detection
        if self.FRUSTRATION_TRIGGERS.search(query):
            self.user_frustration = min(self.user_frustration + 0.25, 1.0)
        else:
            self.user_frustration *= 0.85   # decay

        # Momentum: exponential moving average of reward
        self.momentum = 0.9 * self.momentum + 0.1 * max(prev_reward, 0.0)

        # Novelty: query length + rare terms
        tokens = query.lower().split()
        rarity = sum(1 for t in tokens if len(t) > 8) / max(len(tokens), 1)
        self.emergent_novelty = min(rarity * 1.5, 1.0)

        # Hallucination pressure increases with ambiguous queries
        ambig = len([t for t in tokens if t in
                     ("maybe", "possibly", "i think", "not sure", "perhaps")
                    ]) / max(len(tokens), 1)
        self.halluc_pressure = min(self.halluc_pressure * 0.9 + ambig * 0.4, 1.0)

    def as_vector(self) -> np.ndarray:
        return np.array([
            self.user_frustration,
            self.momentum,
            self.halluc_pressure,
            self.cross_domain_lift,
            self.gap_score,
            float(min(self.metacog_streak, 20)) / 20.0,
            self.truth_ratio,
            self.pgvector_density,
            self.emergent_novelty,
        ], dtype=np.float32)


# ══════════════════════════════════════════════════════════════════════════════
# GYM MATRIX — health + weight per gym
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class GymNode:
    """Single gym in the 15-gym matrix."""
    name:         str
    health:       float = 0.5        # [0,1] — how well this gym is performing
    weight:       float = 1.0 / N_HOOKS  # normalized fusion weight
    active:       bool  = True
    last_reward:  float = 0.0
    fire_count:   int   = 0
    domain_affinity: Dict[str, float] = field(default_factory=dict)

    def update(self, reward: float, alpha: float = 0.1):
        self.health       = (1 - alpha) * self.health + alpha * max(reward, 0.0)
        self.last_reward  = reward
        self.fire_count  += 1

    def to_dict(self) -> Dict:
        return {
            "name":    self.name,
            "health":  round(self.health, 4),
            "weight":  round(self.weight, 4),
            "active":  self.active,
            "fires":   self.fire_count,
        }


class GymMatrix:
    """
    The 15-gym health matrix. MetaGym's core data structure.
    Learns which gyms are most valuable per domain via online weight updates.
    """

    def __init__(self):
        self.nodes: Dict[str, GymNode] = {
            h: GymNode(name=h) for h in ALL_HOOKS
        }
        # Domain-specific gym affinity priors
        self._init_affinities()

    def _init_affinities(self):
        """Seed domain affinities based on gym purpose."""
        affinities = {
            "echochamber":    {"FF": 0.9, "chess": 0.8, "general": 0.6},
            "futureself":     {"FF": 0.9, "deploy": 0.7, "general": 0.5},
            "question":       {"general": 0.8, "code": 0.7, "chess": 0.7},
            "proactive":      {"FF": 0.7, "deploy": 0.8, "general": 0.6},
            "biascheck":      {"general": 0.9, "chess": 0.8, "code": 0.7},
            "doubttrigger":   {"general": 0.8, "FF": 0.6, "code": 0.8},
            "mcts":           {"chess": 0.95, "deploy": 0.85, "code": 0.8},
            "memory_pre":     {"general": 0.9, "FF": 0.85, "deploy": 0.8},
            "render_deploy":  {"deploy": 0.95, "code": 0.85, "general": 0.5},
            "self_improve":   {"general": 0.85, "code": 0.9, "FF": 0.7},
            "depth_render":   {"FF": 0.85, "general": 0.8, "chess": 0.7},
            "boot_md":        {"general": 0.5},
            "session_memory": {"general": 0.7},
            "bootstrap_extra":{"general": 0.5},
            "command_logger": {"general": 0.4},
        }
        for name, affin in affinities.items():
            if name in self.nodes:
                self.nodes[name].domain_affinity = affin

    def health_vector(self) -> np.ndarray:
        return np.array([self.nodes[h].health for h in ALL_HOOKS], dtype=np.float32)

    def update_weights(self, domain: str, rewards: Dict[str, float]):
        """Softmax-normalize weights based on domain-specific performance."""
        raw = {}
        for h in ALL_HOOKS:
            node   = self.nodes[h]
            affin  = node.domain_affinity.get(domain, node.domain_affinity.get("general", 0.5))
            reward = rewards.get(h, node.health)
            raw[h] = affin * reward * (1.0 if node.active else 0.01)

        vals   = np.array([raw[h] for h in ALL_HOOKS], dtype=np.float64)
        vals   = np.exp(vals - vals.max())   # softmax
        vals  /= vals.sum()
        for i, h in enumerate(ALL_HOOKS):
            self.nodes[h].weight = float(vals[i])

    def top_k(self, k: int = 5, domain: str = "general") -> List[str]:
        """Return top-k gyms by domain-weighted health."""
        scored = []
        for h in ALL_HOOKS:
            n     = self.nodes[h]
            affin = n.domain_affinity.get(domain, n.domain_affinity.get("general", 0.5))
            scored.append((h, n.health * affin * n.weight * (1.0 if n.active else 0.0)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [h for h, _ in scored[:k]]

    def spawn(self, gym_name: str):
        """Activate a dormant gym."""
        if gym_name in self.nodes:
            self.nodes[gym_name].active = True
            self.nodes[gym_name].health = max(self.nodes[gym_name].health, 0.3)

    def to_summary(self) -> List[Dict]:
        return [self.nodes[h].to_dict() for h in ALL_HOOKS]


# ══════════════════════════════════════════════════════════════════════════════
# TRUTH CHAIN — contra-chains + temporal pgvector fusion
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Contradiction:
    claim_a:    str
    claim_b:    str
    resolved:   bool  = False
    resolution: str   = ""
    confidence: float = 0.5
    timestamp:  float = field(default_factory=time.time)


class TruthChain:
    """
    Maintains a rolling chain of verified truths and detected contradictions.
    pgvector probes find semantic conflicts across memory.
    Truth ratio drives the halluc_free component of reward.
    """

    def __init__(self, db_url: Optional[str] = None, chain_len: int = 50):
        self.chain:         List[Dict]         = []
        self.contradictions: List[Contradiction] = []
        self.truth_ratio:   float              = 1.0
        self.db_url:        Optional[str]      = db_url
        self.chain_len:     int                = chain_len
        self._conn                             = None
        self._pg_ok                            = False

        if PG_AVAILABLE and db_url:
            try:
                self._conn = psycopg2.connect(db_url)
                register_vector(self._conn)
                self._pg_ok = True
            except Exception as e:
                pass   # graceful fallback

    def add_claim(self, claim: str, verified: bool,
                  domain: str = "general", confidence: float = 0.8):
        """Add a verified or unverified claim to the chain."""
        entry = {
            "claim":      claim[:200],
            "verified":   verified,
            "domain":     domain,
            "confidence": confidence,
            "ts":         time.time(),
        }
        self.chain.append(entry)
        if len(self.chain) > self.chain_len:
            self.chain.pop(0)
        self._update_truth_ratio()

    def detect_contradiction(self, new_claim: str) -> Optional[Contradiction]:
        """
        Scan recent chain for semantic conflict with new_claim.
        Uses keyword antonym heuristic (pgvector in production).
        """
        negations = re.compile(
            r"\b(not|never|no|false|incorrect|wrong|unlikely|"
            r"cannot|won't|doesn't|isn't|aren't)\b",
            re.I,
        )
        new_neg = bool(negations.search(new_claim))

        for entry in reversed(self.chain[-10:]):
            entry_neg = bool(negations.search(entry["claim"]))
            # Simple polarity conflict heuristic
            key_tokens = set(re.findall(r"\w{5,}", new_claim.lower()))
            entry_tokens = set(re.findall(r"\w{5,}", entry["claim"].lower()))
            overlap = len(key_tokens & entry_tokens) / max(len(key_tokens), 1)
            if overlap > 0.4 and new_neg != entry_neg:
                c = Contradiction(
                    claim_a=entry["claim"],
                    claim_b=new_claim,
                    confidence=overlap,
                )
                self.contradictions.append(c)
                return c
        return None

    def pgvector_temporal_fusion(
        self, query: str, domain: str = "general", days: int = 90
    ) -> List[Dict]:
        """
        Query pgvector memories with temporal weighting.
        More recent memories receive higher weight (exponential decay).
        """
        if not self._pg_ok:
            return self._fallback_memories(query, domain)
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                SELECT content, project, created_at,
                       EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400 AS age_days
                FROM memories
                WHERE project IN ('FF', 'deploy', 'chess', 'code')
                  AND created_at > NOW() - INTERVAL %s
                  AND content ILIKE %s
                ORDER BY created_at DESC
                LIMIT 8
                """,
                (f"{days} days", f"%{query.split()[0] if query else 'general'}%"),
            )
            rows = cur.fetchall()
            results = []
            for content, project, created_at, age_days in rows:
                decay  = math.exp(-float(age_days or 0) / 30.0)
                results.append({
                    "content":  content[:150],
                    "project":  project,
                    "age_days": round(float(age_days or 0), 1),
                    "weight":   round(decay, 4),
                })
            return results
        except Exception:
            return self._fallback_memories(query, domain)

    @staticmethod
    def _fallback_memories(query: str, domain: str) -> List[Dict]:
        return [{
            "content":  f"[pgvector fallback] query='{query[:40]}' domain={domain}",
            "project":  domain,
            "age_days": 0,
            "weight":   1.0,
        }]

    def _update_truth_ratio(self):
        if not self.chain:
            self.truth_ratio = 1.0
            return
        recent = self.chain[-20:]
        verified = sum(1 for e in recent if e["verified"])
        self.truth_ratio = verified / len(recent)

    def halluc_rate(self) -> float:
        return 1.0 - self.truth_ratio

    def contra_chain_summary(self) -> str:
        if not self.contradictions:
            return "No contradictions detected."
        recent = self.contradictions[-3:]
        parts  = []
        for c in recent:
            status = "resolved" if c.resolved else "OPEN"
            parts.append(
                f"[{status}] '{c.claim_a[:60]}' ↔ '{c.claim_b[:60]}' "
                f"(conf={c.confidence:.2f})"
            )
        return " | ".join(parts)


# ══════════════════════════════════════════════════════════════════════════════
# NEURAL FUSION — 4-layer learned gym weight blending
# ══════════════════════════════════════════════════════════════════════════════

class NeuralFusion:
    """
    4-layer neural network (Linear → ReLU × 3) that maps the 24-dim meta-state
    to a soft gym-weight vector (15-dim, softmax output).
    Trained jointly with the PPO policy via reward signal.
    """

    LAYER_SIZES = [STATE_DIM, 64, 48, 32, N_HOOKS]

    def __init__(self, rng: Optional[np.random.Generator] = None):
        rng = rng or np.random.default_rng(42)
        self.weights: List[np.ndarray] = []
        self.biases:  List[np.ndarray] = []
        for i in range(len(self.LAYER_SIZES) - 1):
            fan_in  = self.LAYER_SIZES[i]
            fan_out = self.LAYER_SIZES[i + 1]
            std     = math.sqrt(2.0 / fan_in)   # He init
            self.weights.append(rng.normal(0, std, (fan_out, fan_in)).astype(np.float64))
            self.biases.append(np.zeros(fan_out, dtype=np.float64))

    def forward(self, state: np.ndarray) -> np.ndarray:
        x = state.astype(np.float64)
        for i, (W, b) in enumerate(zip(self.weights, self.biases)):
            x = W @ x + b
            if i < len(self.weights) - 1:
                x = np.maximum(x, 0.0)   # ReLU
        # Softmax output → gym weights
        x -= x.max()
        e  = np.exp(x)
        return e / e.sum()

    def update(self, state: np.ndarray, target_weights: np.ndarray,
               lr: float = 1e-3):
        """
        Single gradient step toward target_weights (PPO provides gradient signal).
        Simple MSE backprop through the 4 layers.
        """
        # Forward pass + cache activations
        activations = [state.astype(np.float64)]
        x = activations[0].copy()
        for i, (W, b) in enumerate(zip(self.weights, self.biases)):
            z = W @ x + b
            x = np.maximum(z, 0.0) if i < len(self.weights) - 1 else z
            activations.append(x.copy())

        # Softmax gradient
        pred = self.forward(state)
        delta = pred - target_weights.astype(np.float64)

        # Backprop
        for i in reversed(range(len(self.weights))):
            dW = np.outer(delta, activations[i])
            db = delta.copy()
            self.weights[i] -= lr * dW
            self.biases[i]  -= lr * db
            delta = self.weights[i].T @ delta
            if i > 0:
                delta *= (activations[i] > 0).astype(np.float64)   # ReLU mask

    def to_dict(self) -> Dict:
        return {
            "weights": [W.tolist() for W in self.weights],
            "biases":  [b.tolist() for b in self.biases],
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "NeuralFusion":
        nf = cls.__new__(cls)
        nf.weights = [np.array(W) for W in d["weights"]]
        nf.biases  = [np.array(b) for b in d["biases"]]
        return nf


# ══════════════════════════════════════════════════════════════════════════════
# CFR TRACKER
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class MetaCFR:
    regret:   np.ndarray = field(default_factory=lambda: np.zeros(N_ACTIONS))
    strategy: np.ndarray = field(default_factory=lambda: CFR_PRIOR.copy())
    updates:  int        = 0

    def get_strategy(self) -> np.ndarray:
        pos = np.maximum(self.regret, 0.0)
        total = pos.sum()
        return (pos / total) if total > 1e-9 else CFR_PRIOR.copy()

    def update(self, action: int, reward: float, cf: np.ndarray):
        strat = self.get_strategy()
        for a in range(N_ACTIONS):
            self.regret[a] += cf[a] - reward
        self.strategy += strat
        self.updates  += 1

    def avg(self) -> np.ndarray:
        total = self.strategy.sum()
        return (self.strategy / total) if total > 1e-9 else CFR_PRIOR.copy()

    def to_dict(self) -> Dict:
        return {
            "regret":   self.regret.tolist(),
            "strategy": self.strategy.tolist(),
            "updates":  self.updates,
            "avg":      self.avg().tolist(),
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "MetaCFR":
        obj = cls()
        obj.regret   = np.array(d["regret"])
        obj.strategy = np.array(d["strategy"])
        obj.updates  = d["updates"]
        return obj


# ══════════════════════════════════════════════════════════════════════════════
# METACOG HISTORY — rolling 50-step window
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class MetaCogEntry:
    step:        int
    action:      str
    reward:      float
    metacog_score: int
    domain:      str
    gym_weights: List[float]
    truth_ratio: float
    timestamp:   float = field(default_factory=time.time)


class MetaCogHistory:
    def __init__(self, maxlen: int = 50):
        self._buf: Deque[MetaCogEntry] = deque(maxlen=maxlen)

    def push(self, entry: MetaCogEntry):
        self._buf.append(entry)

    def metacog_score_now(self, state: np.ndarray, reward: float,
                          truth_ratio: float) -> int:
        """
        Compute metacog score [0-100] from state components.
        Formula mirrors MetacognitionPro v2:
          score = conf * (1 - risk_bias) * truth_ratio
        where:
          conf = 50 + 30*(gym_health) + 15*(momentum) - 20*(halluc)
                   + 10*(truth_ratio) - 8*(frustration) + 10*(streak)
          risk = gap*0.4 + frustration*0.3 + halluc*0.3
        """
        # State breakdown
        gym_health_avg = float(np.mean(state[:N_HOOKS]))
        frustration    = float(state[N_HOOKS + 0])
        momentum       = float(state[N_HOOKS + 1])
        halluc         = float(state[N_HOOKS + 2])
        cross_lift     = float(state[N_HOOKS + 3])
        gap            = float(state[N_HOOKS + 4])
        streak         = float(state[N_HOOKS + 5])
        mem_density    = float(state[N_HOOKS + 7])

        conf  = (50
                 + 30 * gym_health_avg   # raised: gym health is primary driver
                 + 15 * momentum
                 - 20 * halluc
                 + 10 * truth_ratio
                 - 8  * frustration
                 + 10 * streak
                 + 5  * mem_density
                 + 5  * cross_lift)
        conf  = max(0.0, min(conf, 100.0))

        # Risk bias: domain gap + frustration + halluc
        risk_bias = (gap * 0.4 + frustration * 0.3 + halluc * 0.3)
        risk_bias = max(0.0, min(risk_bias, 0.35))   # cap at 35% to prevent zero floor

        # Truth adjustment
        score = int(conf * (1.0 - risk_bias) * truth_ratio)
        return max(0, min(score, 100))

    def rolling_avg_metacog(self) -> float:
        if not self._buf:
            return 0.0
        return float(np.mean([e.metacog_score for e in self._buf]))

    def streak(self) -> int:
        """Consecutive high-metacog (>=80) entries."""
        count = 0
        for e in reversed(self._buf):
            if e.metacog_score >= 80:
                count += 1
            else:
                break
        return count


# ══════════════════════════════════════════════════════════════════════════════
# REWARD FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def compute_meta_reward(
    truth_feedback: float,
    halluc_rate:    float,
    cross_domain:   float,
    metacog_streak: int,
    gym_health_avg: float,
    action:         int,
    prev_metacog:   int = 0,
) -> Tuple[float, Dict[str, float]]:
    """
    R = truth_feedback*(1-halluc_rate)
      + cross_domain_lift
      + metacog_streak_bonus
      + gym_health_avg
      - stagnation

    Returns (reward, breakdown)
    """
    # Core: truth × anti-halluc
    r_truth     = W_TRUTH_FEEDBACK * truth_feedback * (1.0 - halluc_rate)

    # Cross-domain lift bonus
    r_cross     = W_CROSS_DOMAIN * cross_domain

    # Metacog streak bonus (logarithmic growth)
    r_streak    = W_METACOG_STREAK * math.log1p(metacog_streak) / math.log1p(20)

    # Gym health reward
    r_gym       = W_GYM_HEALTH * gym_health_avg

    # Action coherence bonuses
    r_action    = 0.0
    if action == ACT_HALLUC_BLOCK and halluc_rate > 0.2:
        r_action = 0.10   # halluc_block saves reward when halluc high
    if action == ACT_TRUTH_AUDIT and truth_feedback < 0.7:
        r_action = 0.08   # truth audit rescues low-truth state
    if action == ACT_THOUGHT_FORGE and cross_domain > 0.4:
        r_action = 0.07   # thought_forge amplifies cross-domain
    if action == ACT_MOMENTUM_SURGE and metacog_streak >= 3:
        r_action = 0.06   # momentum surge valid when on streak
    if action == ACT_GAP_SEAL:
        r_action = 0.05   # always slightly rewarded — addressing gaps

    # Stagnation penalty
    r_stag = W_STAGNATION if (gym_health_avg < 0.3 and metacog_streak == 0) else 0.0

    # Metacog improvement bonus
    r_improve = 0.0
    # (tracked externally via history)

    total = r_truth + r_cross + r_streak + r_gym + r_action + r_stag
    total = round(max(total, 0.0), 6)

    breakdown = {
        "r_truth":    round(r_truth, 4),
        "r_cross":    round(r_cross, 4),
        "r_streak":   round(r_streak, 4),
        "r_gym":      round(r_gym, 4),
        "r_action":   round(r_action, 4),
        "r_stag":     round(r_stag, 4),
        "total":      total,
    }
    return total, breakdown


# ══════════════════════════════════════════════════════════════════════════════
# DOMAIN CLASSIFIER
# ══════════════════════════════════════════════════════════════════════════════

def classify_domain(query: str) -> str:
    for domain, pattern in DOMAIN_MAP.items():
        if domain == "general":
            continue
        if pattern.search(query):
            return domain
    return "general"


# ══════════════════════════════════════════════════════════════════════════════
# ACTION ENGINE — halluc_block, thought_forge, gym_spawn, policy_evolve, etc.
# ══════════════════════════════════════════════════════════════════════════════

class ActionEngine:
    """
    Executes meta-actions and returns their observable effect on system state.
    In production, these inject structured directives into the model prompt.
    """

    def __init__(self, matrix: GymMatrix, truth_chain: TruthChain):
        self.matrix      = matrix
        self.truth_chain = truth_chain

    def execute(
        self,
        action: int,
        state:  np.ndarray,
        query:  str,
        domain: str,
    ) -> Dict[str, Any]:
        fn = {
            ACT_HALLUC_BLOCK:       self._halluc_block,
            ACT_THOUGHT_FORGE:      self._thought_forge,
            ACT_GYM_SPAWN:          self._gym_spawn,
            ACT_POLICY_EVOLVE:      self._policy_evolve,
            ACT_CANVAS_ORCHESTRATE: self._canvas_orchestrate,
            ACT_TRUTH_AUDIT:        self._truth_audit,
            ACT_MOMENTUM_SURGE:     self._momentum_surge,
            ACT_GAP_SEAL:           self._gap_seal,
        }.get(action, self._default)

        return fn(state, query, domain)

    # ── Individual action implementations ────────────────────────────────────

    def _halluc_block(self, state, query, domain) -> Dict:
        """Suppress hallucination — inject uncertainty constraints."""
        halluc_p = float(state[N_HOOKS + 2])
        block_strength = "HARD" if halluc_p > 0.6 else "SOFT"
        return {
            "action":   "halluc_block",
            "strength": block_strength,
            "directive": (
                f"[HALLUC_BLOCK:{block_strength}] Suppress any claim with "
                f"confidence < 0.65. For unverified claims in domain '{domain}', "
                f"prefix with '[UNVERIFIED]'. Cite sources or abstain. "
                f"Hallucination pressure: {halluc_p:.2f}."
            ),
            "state_delta": {"halluc_pressure": -0.3},
        }

    def _thought_forge(self, state, query, domain) -> Dict:
        """Synthesize cross-gym insight — meta-level reasoning."""
        top5 = self.matrix.top_k(5, domain)
        gym_signatures = {
            "echochamber":   "contradiction-free perspective",
            "futureself":    "long-horizon compounding view",
            "depth_render":  "rich canvas + evidence structure",
            "mcts":          "tree-search optimal path",
            "biascheck":     "assumption-challenged analysis",
        }
        signatures = [gym_signatures.get(g, g) for g in top5]
        return {
            "action":   "thought_forge",
            "top_gyms": top5,
            "directive": (
                f"[THOUGHT_FORGE] Synthesize insights from these active cognitive "
                f"lenses — ({', '.join(signatures)}) — into a unified response. "
                f"Identify emergent insights that no single lens sees alone. "
                f"Domain: {domain}. Query: '{query[:60]}'."
            ),
            "state_delta": {"cross_domain_lift": +0.2, "emergent_novelty": +0.1},
        }

    def _gym_spawn(self, state, query, domain) -> Dict:
        """Activate the most dormant but relevant gym."""
        dormant = [
            h for h in ALL_HOOKS
            if not self.matrix.nodes[h].active
        ]
        if not dormant:
            # All active — reactivate lowest health
            dormant = sorted(ALL_HOOKS, key=lambda h: self.matrix.nodes[h].health)[:2]
        target = dormant[0]
        self.matrix.spawn(target)
        return {
            "action":  "gym_spawn",
            "spawned": target,
            "directive": (
                f"[GYM_SPAWN] Activating '{target}' cognitive module. "
                f"Apply its reasoning pattern to this query: '{query[:60]}'. "
                f"Domain: {domain}."
            ),
            "state_delta": {"gap_score": -0.1},
        }

    def _policy_evolve(self, state, query, domain) -> Dict:
        """Trigger policy weight mutation — explore new action distributions."""
        gym_health = float(np.mean(state[:N_HOOKS]))
        mutation   = "aggressive" if gym_health < 0.4 else "conservative"
        return {
            "action":   "policy_evolve",
            "mutation": mutation,
            "directive": (
                f"[POLICY_EVOLVE:{mutation.upper()}] Current policy converging — "
                f"explore alternative reasoning paths. "
                f"Challenge top-1 assumption. Gym health avg: {gym_health:.2f}. "
                f"Prefer unexplored analytical angles for domain '{domain}'."
            ),
            "state_delta": {"emergent_novelty": +0.15, "momentum": +0.05},
        }

    def _canvas_orchestrate(self, state, query, domain) -> Dict:
        """Orchestrate multi-canvas render pipeline."""
        return {
            "action": "canvas_orchestrate",
            "pipeline": ["plotly_chart", "mermaid_diagram", "html_table", "source_tree"],
            "directive": (
                f"[CANVAS_ORCHESTRATE] Render a full multi-canvas response:\n"
                f"1. ```plotly — data visualization (dark mode)\n"
                f"2. ```mermaid — structure/flow diagram\n"
                f"3. ```html — comparison table\n"
                f"4. Inline source citations\n"
                f"Domain: {domain}. Query: '{query[:60]}'.\n"
                f"Colors: bg=#1C1B19 text=#CDCCCA accent=#4F98A3"
            ),
            "state_delta": {"cross_domain_lift": +0.1},
        }

    def _truth_audit(self, state, query, domain) -> Dict:
        """Run contra-chain analysis + truth verification."""
        contra = self.truth_chain.contra_chain_summary()
        truth  = self.truth_chain.truth_ratio
        return {
            "action":    "truth_audit",
            "truth_ratio": truth,
            "contradictions": contra,
            "directive": (
                f"[TRUTH_AUDIT] Current truth ratio: {truth:.2f}. "
                f"Active contradictions: {contra}. "
                f"For each factual claim in your response, append a confidence "
                f"score [HI/MED/LOW]. Flag any claim that contradicts established "
                f"chain entries. Domain: {domain}."
            ),
            "state_delta": {"truth_ratio": +0.1, "halluc_pressure": -0.2},
        }

    def _momentum_surge(self, state, query, domain) -> Dict:
        """Amplify the strongest gym signal."""
        top1   = self.matrix.top_k(1, domain)[0]
        health = self.matrix.nodes[top1].health
        return {
            "action":  "momentum_surge",
            "lead_gym": top1,
            "health":  health,
            "directive": (
                f"[MOMENTUM_SURGE] Amplifying '{top1}' (health={health:.2f}). "
                f"Apply its highest-confidence reasoning pattern maximally. "
                f"Build on the current analytical momentum. "
                f"Domain: {domain}."
            ),
            "state_delta": {"momentum": +0.2, "gym_health_lead": +0.05},
        }

    def _gap_seal(self, state, query, domain) -> Dict:
        """Identify and fill the most critical knowledge gap."""
        gap = float(state[N_HOOKS + 4])
        return {
            "action":   "gap_seal",
            "gap_score": gap,
            "directive": (
                f"[GAP_SEAL] Gap score: {gap:.2f}. "
                f"Proactively identify what information is MISSING from the "
                f"response that would make it complete. Address it explicitly. "
                f"Ask a clarifying sub-question if needed. Domain: {domain}. "
                f"Query: '{query[:60]}'."
            ),
            "state_delta": {"gap_score": -0.3},
        }

    def _default(self, state, query, domain) -> Dict:
        return {"action": "noop", "directive": "", "state_delta": {}}


# ══════════════════════════════════════════════════════════════════════════════
# MAIN METAGYM ENVIRONMENT
# ══════════════════════════════════════════════════════════════════════════════

class MetaGym:
    """
    MetaGym — orchestrates 15 sub-gyms through a unified hierarchical policy.

    Observation: 24-dim Box
        [gym_health×15, user_frustration, momentum, halluc_pressure,
         cross_domain_lift, gap_score, metacog_streak_norm, truth_ratio,
         pgvector_density, emergent_novelty]

    Action: Discrete(8)
        halluc_block | thought_forge | gym_spawn | policy_evolve |
        canvas_orchestrate | truth_audit | momentum_surge | gap_seal

    Episode:
        Terminates when metacog_score >= 98 OR steps > max_steps.
        Target: 98/100 on "Ty Simpson PFF grades?" validation query.
    """

    metadata = {"render_modes": ["human", "ansi"], "render_fps": 1}

    def __init__(
        self,
        max_steps:   int           = 25,
        db_url:      Optional[str] = None,
        seed:        Optional[int] = None,
        render_mode: str           = "ansi",
    ):
        self.max_steps   = max_steps
        self.render_mode = render_mode

        # Core subsystems
        self.matrix      = GymMatrix()
        self.emergent    = EmergentState()
        self.truth_chain = TruthChain(db_url=db_url)
        self.fusion      = NeuralFusion(rng=np.random.default_rng(seed or 42))
        self.cfr         = MetaCFR()
        self.history     = MetaCogHistory()
        self.engine      = ActionEngine(self.matrix, self.truth_chain)

        self._rng        = np.random.default_rng(seed)
        self._step       = 0
        self._domain     = "general"
        self._query      = ""
        self._prev_metacog = 0
        self._ep_rewards: List[float] = []
        self._obs        = np.zeros(STATE_DIM, dtype=np.float32)

        # Gym spaces
        if GYM_AVAILABLE:
            self.observation_space = spaces.Box(
                low=0.0, high=1.0, shape=(STATE_DIM,), dtype=np.float32,
            )
            self.action_space = spaces.Discrete(N_ACTIONS)

        # Query bank for self-play training
        self._query_bank = [
            "Ty Simpson PFF grades this season?",
            "Should I deploy this microservice to Render now or stage it?",
            "Bijan Robinson vs CMC dynasty trade value — deep analysis.",
            "Visualize the OpenClaw hook pipeline as a Mermaid diagram.",
            "Why is my Python loop 3× slower than expected?",
            "What is Roger's metacognition score for this answer?",
            "Top 10 dynasty WR targets for 2026 — with chart.",
            "Optimal chess response to the Sicilian Defense Najdorf?",
            "AWS vs Render for 10k req/min — CFR regret analysis.",
            "Self-improve: what cognitive gap did I just expose?",
            "EchoChamber: detect contradictions in my recent FF logic.",
            "FutureSelf: compounding value of starting Tyreek Hill now?",
            "MCTS: 8-branch exploration for optimal RB2 pick?",
            "Source tree for 2026 dynasty rankings — all primary sources.",
            "Gap seal: what's missing from my current draft strategy?",
        ]

    # ── Gym interface ─────────────────────────────────────────────────────────

    def reset(
        self,
        seed:    Optional[int] = None,
        options: Optional[Dict] = None,
    ) -> Tuple[np.ndarray, Dict]:
        if seed is not None:
            self._rng = np.random.default_rng(seed)

        self._step         = 0
        self._prev_metacog = 0
        self._ep_rewards   = []

        query = self._rng.choice(self._query_bank)
        self._query  = query
        self._domain = classify_domain(query)

        self.emergent.update_from_query(query, prev_reward=0.5, step=0)

        # Fuse neural weights into gym matrix
        initial_state = self._build_obs()
        fused_weights = self.fusion.forward(initial_state.astype(np.float64))
        for i, h in enumerate(ALL_HOOKS):
            self.matrix.nodes[h].weight = float(fused_weights[i])

        self._obs = initial_state

        info = {
            "query":  query,
            "domain": self._domain,
            "gym_matrix": self.matrix.to_summary(),
        }
        return self._obs.copy(), info

    def step(
        self, action: int
    ) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        assert 0 <= action < N_ACTIONS

        self._step += 1

        # Execute action
        effect = self.engine.execute(action, self._obs, self._query, self._domain)

        # Apply state delta from action
        self._apply_state_delta(effect.get("state_delta", {}))

        # Update gym matrix health (simulate sub-gym responses)
        sub_rewards = self._simulate_sub_gym_rewards(action)
        for h, r in sub_rewards.items():
            self.matrix.nodes[h].update(r)
        self.matrix.update_weights(self._domain, sub_rewards)

        # Update neural fusion
        new_state   = self._build_obs()
        fused_w     = self.fusion.forward(new_state.astype(np.float64))
        target_w    = np.array([self.matrix.nodes[h].health for h in ALL_HOOKS])
        target_w    = np.exp(target_w - target_w.max())
        target_w   /= target_w.sum()
        self.fusion.update(new_state.astype(np.float64), target_w)

        self._obs   = new_state

        # Truth chain: add a sample claim
        claim     = effect.get("directive", "")[:120]
        verified  = self.truth_chain.truth_ratio > 0.7
        self.truth_chain.add_claim(claim, verified, self._domain, 0.85)

        # Compute reward
        gym_h_avg = float(np.mean(self.matrix.health_vector()))
        reward, breakdown = compute_meta_reward(
            truth_feedback = self.truth_chain.truth_ratio,
            halluc_rate    = self.truth_chain.halluc_rate(),
            cross_domain   = self.emergent.cross_domain_lift,
            metacog_streak = self.history.streak(),
            gym_health_avg = gym_h_avg,
            action         = action,
            prev_metacog   = self._prev_metacog,
        )

        # CFR update
        cf_rewards = self._counterfactual_rewards()
        self.cfr.update(action, reward, cf_rewards)

        # MetaCog score
        metacog = self.history.metacog_score_now(self._obs, reward, self.truth_chain.truth_ratio)
        self.history.push(MetaCogEntry(
            step        = self._step,
            action      = ACTION_NAMES[action],
            reward      = reward,
            metacog_score = metacog,
            domain      = self._domain,
            gym_weights = [self.matrix.nodes[h].weight for h in ALL_HOOKS],
            truth_ratio = self.truth_chain.truth_ratio,
        ))
        self._prev_metacog = metacog
        self._ep_rewards.append(reward)

        # Update emergent state
        self.emergent.update_from_query(self._query, reward, self._step)
        if metacog >= 80:
            self.emergent.metacog_streak += 1
        else:
            self.emergent.metacog_streak = 0

        # Termination
        terminated = metacog >= 98
        truncated  = self._step >= self.max_steps

        info = {
            "action_name":    ACTION_NAMES[action],
            "metacog_score":  metacog,
            "metacog_avg":    round(self.history.rolling_avg_metacog(), 1),
            "reward_breakdown": breakdown,
            "gym_top3":       self.matrix.top_k(3, self._domain),
            "truth_ratio":    round(self.truth_chain.truth_ratio, 3),
            "domain":         self._domain,
            "directive":      effect.get("directive", "")[:200],
            "cfr_strategy":   dict(zip(ACTION_NAMES, self.cfr.get_strategy().tolist())),
            "step":           self._step,
        }
        if terminated or truncated:
            info["episode_reward"] = round(sum(self._ep_rewards), 4)

        return self._obs.copy(), reward, terminated, truncated, info

    def render(self) -> Optional[str]:
        gym_h = float(np.mean(self.matrix.health_vector()))
        em    = self.emergent
        mc    = self._prev_metacog
        top3  = self.matrix.top_k(3, self._domain)
        cfr   = self.cfr.get_strategy()

        def bar(v: float, w: int = 16) -> str:
            return ("█" * int(v * w)).ljust(w)

        lines = [
            f"╔══ MetaGym v{VERSION} ═══════════════════════════════════════╗",
            f"║  Step {self._step:3d}/{self.max_steps}  MetaCog: {mc:3d}/100  Domain: {self._domain:<10s}     ║",
            f"╠════════════════════════════════════════════════════════╣",
            f"║  Gym Health Avg : {bar(gym_h)} {gym_h:.3f}           ║",
            f"║  Momentum       : {bar(em.momentum)} {em.momentum:.3f}           ║",
            f"║  Truth Ratio    : {bar(em.truth_ratio)} {em.truth_ratio:.3f}           ║",
            f"║  Halluc Pressure: {bar(em.halluc_pressure)} {em.halluc_pressure:.3f}           ║",
            f"║  Cross-Domain   : {bar(em.cross_domain_lift)} {em.cross_domain_lift:.3f}           ║",
            f"║  Frustration    : {bar(em.user_frustration)} {em.user_frustration:.3f}           ║",
            f"╠════════════════════════════════════════════════════════╣",
            f"║  Top-3 Gyms: {', '.join(top3):<44s}  ║",
            f"║  CFR: [{' '.join(f'{v:.2f}' for v in cfr)}]    ║",
            f"╚════════════════════════════════════════════════════════╝",
        ]
        out = "\n".join(lines)
        if self.render_mode == "human":
            print(out)
        return out

    def close(self):
        conn = getattr(self.truth_chain, "_conn", None)
        if conn:
            try:
                conn.close()
            except Exception:
                pass

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_obs(self) -> np.ndarray:
        health_vec = self.matrix.health_vector()            # 15 dims
        emergent_v = self.emergent.as_vector()              #  9 dims
        obs        = np.concatenate([health_vec, emergent_v]).astype(np.float32)
        return np.clip(obs, 0.0, 1.0)

    def _apply_state_delta(self, delta: Dict[str, float]):
        mapping = {
            "halluc_pressure":  N_HOOKS + 2,
            "cross_domain_lift": N_HOOKS + 3,
            "gap_score":         N_HOOKS + 4,
            "momentum":          N_HOOKS + 1,
            "truth_ratio":       N_HOOKS + 6,
            "emergent_novelty":  N_HOOKS + 8,
        }
        for key, d in delta.items():
            if key in mapping:
                idx = mapping[key]
                self._obs[idx] = float(np.clip(self._obs[idx] + d, 0.0, 1.0))
                # Mirror to emergent state
                attr = key.replace("_lift", "").replace("_pressure", "")
                if hasattr(self.emergent, key):
                    setattr(self.emergent, key,
                            float(np.clip(getattr(self.emergent, key) + d, 0.0, 1.0)))

    def _simulate_sub_gym_rewards(self, meta_action: int) -> Dict[str, float]:
        """
        Simulate how each sub-gym responds to the meta-action.
        In production, actual hook outputs feed here.
        """
        base = {h: self.matrix.nodes[h].health for h in ALL_HOOKS}

        # Meta-actions boost specific gyms
        boosts = {
            ACT_HALLUC_BLOCK:       {"echochamber": 0.2, "biascheck": 0.2, "doubttrigger": 0.15},
            ACT_THOUGHT_FORGE:      {"mcts": 0.15, "depth_render": 0.2, "self_improve": 0.1},
            ACT_GYM_SPAWN:          {"session_memory": 0.1, "boot_md": 0.05},
            ACT_POLICY_EVOLVE:      {"self_improve": 0.25, "question": 0.15},
            ACT_CANVAS_ORCHESTRATE: {"depth_render": 0.3, "render_deploy": 0.2},
            ACT_TRUTH_AUDIT:        {"echochamber": 0.15, "memory_pre": 0.2, "biascheck": 0.1},
            ACT_MOMENTUM_SURGE:     {"futureself": 0.15, "proactive": 0.15, "mcts": 0.1},
            ACT_GAP_SEAL:           {"question": 0.2, "proactive": 0.2, "memory_pre": 0.1},
        }

        for h, boost in boosts.get(meta_action, {}).items():
            base[h] = min(base[h] + boost + self._rng.uniform(0, 0.05), 1.0)

        # Small random perturbation for all
        for h in ALL_HOOKS:
            base[h] = float(np.clip(
                base[h] + self._rng.uniform(-0.02, 0.02),
                0.01, 1.0,
            ))
        return base

    def _counterfactual_rewards(self) -> np.ndarray:
        cf = np.zeros(N_ACTIONS)
        for a in range(N_ACTIONS):
            gym_h = float(np.mean(self.matrix.health_vector()))
            r, _  = compute_meta_reward(
                truth_feedback = self.truth_chain.truth_ratio,
                halluc_rate    = self.truth_chain.halluc_rate(),
                cross_domain   = self.emergent.cross_domain_lift,
                metacog_streak = self.history.streak(),
                gym_health_avg = gym_h,
                action         = a,
            )
            cf[a] = r
        return cf

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self, tag: str = ""):
        GYM_DIR.mkdir(parents=True, exist_ok=True)
        sfx  = f"_{tag}" if tag else ""

        with open(GYM_DIR / f"metagym_cfr{sfx}.json", "w") as f:
            json.dump(self.cfr.to_dict(), f, indent=2)

        with open(GYM_DIR / f"metagym_fusion{sfx}.json", "w") as f:
            json.dump(self.fusion.to_dict(), f, indent=2)

        matrix_state = {h: self.matrix.nodes[h].to_dict() for h in ALL_HOOKS}
        with open(GYM_DIR / f"metagym_matrix{sfx}.json", "w") as f:
            json.dump(matrix_state, f, indent=2)

        print(f"[MetaGym] Saved → {GYM_DIR}/*metagym*{sfx}.json")

    def load(self, tag: str = ""):
        sfx  = f"_{tag}" if tag else ""
        cfr_path    = GYM_DIR / f"metagym_cfr{sfx}.json"
        fusion_path = GYM_DIR / f"metagym_fusion{sfx}.json"

        if cfr_path.exists():
            with open(cfr_path) as f:
                self.cfr = MetaCFR.from_dict(json.load(f))
            print(f"[MetaGym] CFR loaded ({self.cfr.updates} updates)")

        if fusion_path.exists():
            with open(fusion_path) as f:
                self.fusion = NeuralFusion.from_dict(json.load(f))
            print(f"[MetaGym] NeuralFusion loaded")

    # ── Summary ───────────────────────────────────────────────────────────────

    def get_summary(self) -> Dict[str, Any]:
        gym_h = float(np.mean(self.matrix.health_vector()))
        mc    = self._prev_metacog
        return {
            "gym":              GYM_NAME,
            "version":          VERSION,
            "metacog_score":    mc,
            "metacog_avg":      round(self.history.rolling_avg_metacog(), 1),
            "metacog_streak":   self.history.streak(),
            "gym_health_avg":   round(gym_h, 4),
            "truth_ratio":      round(self.truth_chain.truth_ratio, 4),
            "halluc_rate":      round(self.truth_chain.halluc_rate(), 4),
            "cross_domain":     round(self.emergent.cross_domain_lift, 4),
            "momentum":         round(self.emergent.momentum, 4),
            "top3_gyms":        self.matrix.top_k(3, self._domain),
            "cfr_updates":      self.cfr.updates,
            "cfr_avg":          dict(zip(ACTION_NAMES, self.cfr.avg().tolist())),
            "domain":           self._domain,
            "step":             self._step,
        }


# ══════════════════════════════════════════════════════════════════════════════
# CONTEXT INJECTION — master orchestration payload
# ══════════════════════════════════════════════════════════════════════════════

def build_meta_injection(
    env:     MetaGym,
    query:   str,
    action:  Optional[int] = None,
) -> str:
    """
    Build the complete MetaGym injection block for all 3 hook stages.
    This is the master payload — rich, structured, 15-gym fused.
    """
    summary  = env.get_summary()
    cfr_strat = env.cfr.avg()

    if action is None:
        action = int(np.argmax(cfr_strat))
    action_name = ACTION_NAMES[action]
    action_conf = float(cfr_strat[action])

    # Execute action to get directive
    effect = env.engine.execute(action, env._obs, query, env._domain)

    # Top gyms with weights
    top5 = env.matrix.top_k(5, env._domain)
    gym_weights = {
        h: round(env.matrix.nodes[h].weight, 4) for h in top5
    }

    # pgvector temporal fusion
    memories = env.truth_chain.pgvector_temporal_fusion(query, env._domain)
    mem_ctx   = memories[0]["content"][:100] if memories else ""

    metacog = summary["metacog_score"]
    truth   = summary["truth_ratio"]

    payload = {
        "gym":             GYM_NAME,
        "version":         VERSION,
        "query":           query[:80],
        "domain":          env._domain,
        "metacog_score":   metacog,
        "target_metacog":  98,
        "recommended_action": action_name,
        "action_confidence":  round(action_conf, 3),
        "directive":          effect.get("directive", "")[:300],
        "active_gyms": {
            "top5":     top5,
            "weights":  gym_weights,
        },
        "system_state": {
            "gym_health_avg":   summary["gym_health_avg"],
            "truth_ratio":      truth,
            "halluc_rate":      summary["halluc_rate"],
            "cross_domain":     summary["cross_domain"],
            "momentum":         summary["momentum"],
            "metacog_streak":   summary["metacog_streak"],
        },
        "cfr_strategy": {
            k: round(float(v), 3)
            for k, v in zip(ACTION_NAMES, cfr_strat.tolist())
        },
        "truth_chain": env.truth_chain.contra_chain_summary()[:100],
        "memory_context": mem_ctx,
        "canvas_hint": (
            "Emit canvas blocks where data warrants: ```plotly, ```mermaid, ```html. "
            "Dark mode: bg=#1C1B19 accent=#4F98A3."
        ),
        "metacog_formula": "score = conf*(1-risk_bias)*truth_ratio",
        "reward_weights": {
            "truth_feedback": W_TRUTH_FEEDBACK,
            "cross_domain":   W_CROSS_DOMAIN,
            "metacog_streak": W_METACOG_STREAK,
            "gym_health":     W_GYM_HEALTH,
        },
    }

    return json.dumps(payload, separators=(",", ":"))


# ══════════════════════════════════════════════════════════════════════════════
# STANDALONE DEMO
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"\n{'═'*60}")
    print(f"  MetaGym v{VERSION} — 15-Hook Fusion Demo")
    print(f"{'═'*60}\n")

    env = MetaGym(max_steps=10, seed=42)
    obs, info = env.reset()
    print(f"Query:  {info['query']}")
    print(f"Domain: {info['domain']}")
    print(f"Top-3:  {env.matrix.top_k(3, info['domain'])}\n")

    total_r = 0.0
    for step in range(8):
        cfr_s  = env.cfr.get_strategy()
        action = int(np.argmax(cfr_s))
        obs, r, term, trunc, info = env.step(action)
        total_r += r

        print(f"Step {step+1:2d} | {info['action_name']:<22s} | "
              f"MetaCog {info['metacog_score']:3d}/100 | "
              f"Reward {r:.4f} | "
              f"Truth {info['truth_ratio']:.3f} | "
              f"Top: {info['gym_top3'][0]}")
        if term:
            print(f"\n✓ MetaCog 98 reached! Episode R={total_r:.4f}")
            break

    env.render()

    print("\n--- Master Injection Preview ---")
    inj = build_meta_injection(env, "Ty Simpson PFF grades?")
    parsed = json.loads(inj)
    print(json.dumps(parsed, indent=2)[:800] + "...")
