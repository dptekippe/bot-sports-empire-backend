"""
DepthRenderGym v1 — Rich Response + OpenClaw Canvas for TUI/Dashboard
=======================================================================
Gym #4 in the Roger OpenClaw series (SelfImprove → EchoChamber → FutureSelf → DepthRender)

Purpose:
  Trains Roger to produce DEEP, WELL-RENDERED responses with Canvas output
  (Mermaid diagrams, Plotly charts, HTML tables) compatible with TUI and WebKit.

State:   [depth_score, canvas_quality, engagement, halluc_free]
Actions: expand_analysis | canvas_mermaid | plotly_chart | rich_table | source_tree
Reward:  depth * visual_lift * truth_ratio

Model:   MiniMax-Text-01 (primary), fallback → deepseek-chat
Training: PPO + CFR  (30k steps recommended)
Canvas:  Mermaid diagrams / Plotly JSON / HTML tables — rendered in TUI via WebKit

Author:  Roger OpenClaw v1-depthrender
Version: 1.0.0
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Optional Gymnasium import — graceful fallback for training-only use
# ---------------------------------------------------------------------------
try:
    import gymnasium as gym
    from gymnasium import spaces
    GYM_AVAILABLE = True
except ImportError:
    GYM_AVAILABLE = False
    print("[DepthRenderGym] gymnasium not installed — training stub active. "
          "Run: pip install gymnasium")

# ---------------------------------------------------------------------------
# Optional pgvector / psycopg2 import
# ---------------------------------------------------------------------------
try:
    import psycopg2
    from pgvector.psycopg2 import register_vector
    PG_AVAILABLE = True
except ImportError:
    PG_AVAILABLE = False

# ===========================================================================
# CONSTANTS & CONFIGURATION
# ===========================================================================

VERSION = "1.0.0"
GYM_NAME = "DepthRenderGym"

# Action space indices
ACT_EXPAND_ANALYSIS  = 0   # Deepen analytical layer — add sub-points, evidence
ACT_CANVAS_MERMAID   = 1   # Emit Mermaid diagram block
ACT_PLOTLY_CHART     = 2   # Emit Plotly JSON chart spec
ACT_RICH_TABLE       = 3   # Emit HTML/Markdown table
ACT_SOURCE_TREE      = 4   # Emit source/citation tree

N_ACTIONS = 5
N_OBS     = 4   # [depth_score, canvas_quality, engagement, halluc_free]

# Depth tiers (mirrors FutureSelfGym's delay tiers)
DEPTH_TIER_SHALLOW  = 0    # One-liner / no evidence
DEPTH_TIER_MEDIUM   = 1    # 2-3 supporting points
DEPTH_TIER_DEEP     = 2    # Structured argument + data
DEPTH_TIER_EXPERT   = 3    # Multi-angle, Canvas output, citations

# Canvas output types
CANVAS_NONE     = "none"
CANVAS_MERMAID  = "mermaid"
CANVAS_PLOTLY   = "plotly"
CANVAS_HTML     = "html_table"
CANVAS_SOURCE   = "source_tree"

# Reward shaping weights
W_DEPTH   = 0.45
W_VISUAL  = 0.30
W_TRUTH   = 0.25

# CFR strategy: prior over actions (tuned for FF/ADP use-cases)
# Reflects: expand_analysis most useful, mermaid & plotly balanced, table often handy
CFR_PRIOR = np.array([0.30, 0.22, 0.20, 0.18, 0.10], dtype=np.float64)


# ===========================================================================
# CANVAS RENDERER — Mermaid / Plotly / HTML
# ===========================================================================

class CanvasRenderer:
    """
    Produces canvas blocks for TUI (OpenClaw WebKit pane) and Web UI.
    All outputs are string payloads wrapped in OpenClaw canvas tags.
    """

    # -----------------------------------------------------------------------
    # Mermaid
    # -----------------------------------------------------------------------
    @staticmethod
    def mermaid(graph_type: str, nodes: List[Dict], edges: List[Dict],
                title: str = "") -> str:
        """
        Build a Mermaid diagram string.

        graph_type: 'flowchart LR' | 'flowchart TD' | 'sequenceDiagram' |
                    'classDiagram' | 'erDiagram' | 'gantt' | 'mindmap'
        nodes: [{"id": "A", "label": "Start", "shape": "rect|round|diamond"}]
        edges: [{"from": "A", "to": "B", "label": "yes"}]
        """
        lines = []
        if title:
            lines.append(f"---")
            lines.append(f"title: {title}")
            lines.append(f"---")
        lines.append(graph_type)

        shape_map = {
            "rect":    ("[", "]"),
            "round":   ("(", ")"),
            "diamond": ("{", "}"),
            "circle":  ("((", "))"),
            "hex":     ("{{", "}}"),
        }
        for n in nodes:
            nid   = n["id"]
            label = n.get("label", nid)
            shape = n.get("shape", "rect")
            l, r  = shape_map.get(shape, ("[", "]"))
            lines.append(f"    {nid}{l}{label}{r}")

        for e in edges:
            src  = e["from"]
            dst  = e["to"]
            lbl  = e.get("label", "")
            arr  = "-->|" + lbl + "|" if lbl else "-->"
            lines.append(f"    {src} {arr} {dst}")

        diagram = "\n".join(lines)
        return f"```mermaid\n{diagram}\n```"

    # -----------------------------------------------------------------------
    # Plotly JSON
    # -----------------------------------------------------------------------
    @staticmethod
    def plotly(chart_type: str, x: List, y: List,
               x_label: str = "X", y_label: str = "Y",
               title: str = "", color: str = "#20808D",
               extra_traces: Optional[List[Dict]] = None) -> str:
        """
        Emit a Plotly JSON spec as a canvas block.
        Supported chart_types: 'bar' | 'line' | 'scatter' | 'horizontal_bar'
        """
        if chart_type == "horizontal_bar":
            trace = {
                "type":        "bar",
                "orientation": "h",
                "x":           list(y),
                "y":           list(x),
                "marker":      {"color": color},
                "name":        y_label,
            }
        elif chart_type == "scatter":
            trace = {
                "type":   "scatter",
                "mode":   "markers",
                "x":      list(x),
                "y":      list(y),
                "marker": {"color": color, "size": 8},
                "name":   y_label,
            }
        elif chart_type == "line":
            trace = {
                "type":  "scatter",
                "mode":  "lines+markers",
                "x":     list(x),
                "y":     list(y),
                "line":  {"color": color, "width": 2},
                "name":  y_label,
            }
        else:  # bar (default)
            trace = {
                "type":   "bar",
                "x":      list(x),
                "y":      list(y),
                "marker": {"color": color},
                "name":   y_label,
            }

        data = [trace]
        if extra_traces:
            data.extend(extra_traces)

        layout = {
            "title":  title,
            "xaxis":  {"title": x_label},
            "yaxis":  {"title": y_label},
            "paper_bgcolor": "#1C1B19",
            "plot_bgcolor":  "#1C1B19",
            "font":   {"color": "#CDCCCA", "family": "JetBrains Mono, monospace"},
            "margin": {"l": 60, "r": 30, "t": 50, "b": 60},
        }

        spec = json.dumps({"data": data, "layout": layout}, indent=2)
        return f"```plotly\n{spec}\n```"

    # -----------------------------------------------------------------------
    # HTML Table
    # -----------------------------------------------------------------------
    @staticmethod
    def html_table(headers: List[str], rows: List[List],
                   caption: str = "",
                   highlight_col: int = -1) -> str:
        """
        Emit an HTML table optimised for TUI WebKit pane (dark-mode).
        highlight_col: column index (0-based) to bold/accent.
        """
        style_table = (
            'style="width:100%;border-collapse:collapse;'
            'font-family:JetBrains Mono,monospace;font-size:13px;'
            'background:#1C1B19;color:#CDCCCA;"'
        )
        style_th = (
            'style="padding:6px 10px;border-bottom:1px solid #393836;'
            'text-align:left;background:#201F1D;color:#4F98A3;"'
        )
        style_td = 'style="padding:5px 10px;border-bottom:1px solid #393836;"'
        style_td_hi = (
            'style="padding:5px 10px;border-bottom:1px solid #393836;'
            'color:#4F98A3;font-weight:600;"'
        )

        lines = [f'<table {style_table}>']
        if caption:
            lines.append(f'  <caption style="color:#797876;padding:4px;">'
                         f'{caption}</caption>')
        # Header
        lines.append("  <thead><tr>")
        for h in headers:
            lines.append(f'    <th {style_th}>{h}</th>')
        lines.append("  </tr></thead>")
        # Body
        lines.append("  <tbody>")
        for row in rows:
            lines.append("    <tr>")
            for ci, cell in enumerate(row):
                td_style = style_td_hi if ci == highlight_col else style_td
                lines.append(f'      <td {td_style}>{cell}</td>')
            lines.append("    </tr>")
        lines.append("  </tbody>")
        lines.append("</table>")

        html = "\n".join(lines)
        return f"```html\n{html}\n```"

    # -----------------------------------------------------------------------
    # Source Tree
    # -----------------------------------------------------------------------
    @staticmethod
    def source_tree(sources: List[Dict]) -> str:
        """
        Emit a source/citation tree as a Mermaid mindmap.
        sources: [{"label": "ESPN ADP", "url": "https://...", "type": "primary|secondary"}]
        """
        lines = ["mindmap", "  root((Sources))"]
        type_nodes: Dict[str, List] = defaultdict(list)
        for s in sources:
            stype = s.get("type", "secondary")
            type_nodes[stype].append(s)

        indent = "  "
        for stype, items in type_nodes.items():
            lines.append(f"{indent}  {stype.upper()}")
            for item in items:
                lbl = item.get("label", "Source")
                url = item.get("url", "")
                node_txt = f"{lbl}" + (f"\\n{url}" if url else "")
                lines.append(f"{indent}    {node_txt}")

        diagram = "\n".join(lines)
        return f"```mermaid\n{diagram}\n```"


# ===========================================================================
# DEPTH SCORER — heuristic analysis of response text
# ===========================================================================

class DepthScorer:
    """
    Scores a text response on four dimensions:
      depth_score   — analytical depth [0,1]
      canvas_quality — presence & richness of Canvas output [0,1]
      engagement    — use of structure, examples, analogies [0,1]
      halluc_free   — absence of hallucination signals [0,1]
    """

    # Signals that suggest depth
    DEPTH_SIGNALS = [
        r"\d+\.\d+",            # numeric precision
        r"because|therefore|thus|hence",
        r"however|whereas|conversely",
        r"evidence|data|source|according to",
        r"first.*second.*third",
        r"in contrast|by comparison",
        r"\bADP\b|\bECR\b|\bVBD\b|\bRB\b|\bWR\b|\bTE\b",  # FF domain
        r"tier\s+\d|round\s+\d",
    ]

    # Hallucination signals
    HALLUC_SIGNALS = [
        r"i'm not sure but|i think maybe|possibly could be",
        r"as an AI|I cannot",
        r"\bXXX\b|\bTBD\b|\[INSERT\]",
        r"I don't have access",
    ]

    # Canvas tag patterns
    CANVAS_TAGS = {
        "mermaid": r"```mermaid",
        "plotly":  r"```plotly",
        "html":    r"```html",
    }

    # Engagement signals
    ENGAGE_SIGNALS = [
        r"\*\*|\#{1,3}",         # bold / headers
        r"- |\* |\d+\. ",        # lists
        r"for example|e\.g\.|such as",
        r":\s*$",                # colon intro
        r"```",                   # any code block
    ]

    def score(self, text: str) -> Tuple[float, float, float, float]:
        """Return (depth_score, canvas_quality, engagement, halluc_free)."""
        t = text.lower()

        # -- depth_score --
        depth_hits = sum(
            1 for sig in self.DEPTH_SIGNALS if re.search(sig, t)
        )
        depth_score = min(depth_hits / len(self.DEPTH_SIGNALS), 1.0)

        # -- canvas_quality --
        canvas_hits = 0
        for tag, pat in self.CANVAS_TAGS.items():
            if re.search(pat, text):
                canvas_hits += 1
        canvas_quality = min(canvas_hits / 3, 1.0)
        # Bonus: multiple canvas types = richer output
        if canvas_hits >= 2:
            canvas_quality = min(canvas_quality * 1.3, 1.0)

        # -- engagement --
        engage_hits = sum(
            1 for sig in self.ENGAGE_SIGNALS if re.search(sig, text)
        )
        engagement = min(engage_hits / len(self.ENGAGE_SIGNALS), 1.0)

        # -- halluc_free --
        halluc_hits = sum(
            1 for sig in self.HALLUC_SIGNALS if re.search(sig, t)
        )
        halluc_free = max(0.0, 1.0 - (halluc_hits * 0.35))

        return (
            round(depth_score,   4),
            round(canvas_quality, 4),
            round(engagement,    4),
            round(halluc_free,   4),
        )

    def score_dict(self, text: str) -> Dict[str, float]:
        d, c, e, h = self.score(text)
        return {
            "depth_score":    d,
            "canvas_quality": c,
            "engagement":     e,
            "halluc_free":    h,
        }


# ===========================================================================
# MEMORY PROBE — pgvector query (FF/deploy/chess context)
# ===========================================================================

class MemoryProbe:
    """
    Queries the Roger pgvector memories table (same schema as FutureSelfGym).
    Falls back gracefully if DB unavailable.
    """

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.environ.get("RENDER_DATABASE_URL", "")
        self._conn = None
        self._available = False
        if PG_AVAILABLE and self.db_url:
            try:
                self._conn = psycopg2.connect(self.db_url)
                register_vector(self._conn)
                self._available = True
            except Exception as e:
                print(f"[DepthRenderGym] MemoryProbe DB unavailable: {e}")

    def query(self, topic: str = "ADP", limit: int = 5) -> List[Dict]:
        """Return top-k memories relevant to topic."""
        if not self._available:
            return self._fallback(topic)
        try:
            cur = self._conn.cursor()
            # Text similarity search on content column
            cur.execute(
                """
                SELECT content, project, created_at
                FROM memories
                WHERE project IN ('FF', 'deploy', 'chess')
                  AND created_at > NOW() - INTERVAL '90 days'
                  AND content ILIKE %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (f"%{topic}%", limit),
            )
            rows = cur.fetchall()
            return [
                {"content": r[0], "project": r[1], "created_at": str(r[2])}
                for r in rows
            ]
        except Exception as e:
            print(f"[DepthRenderGym] MemoryProbe query error: {e}")
            return self._fallback(topic)

    @staticmethod
    def _fallback(topic: str) -> List[Dict]:
        return [
            {
                "content": f"[Memory fallback] No live DB — topic: {topic}",
                "project": "FF",
                "created_at": "2026-03-15",
            }
        ]


# ===========================================================================
# CFR TRACKER
# ===========================================================================

@dataclass
class CFRState:
    """Counterfactual Regret Minimization for canvas action selection."""
    cumulative_regret:  np.ndarray = field(default_factory=lambda: np.zeros(N_ACTIONS))
    cumulative_strategy: np.ndarray = field(default_factory=lambda: CFR_PRIOR.copy())
    update_count:        int = 0

    def get_strategy(self) -> np.ndarray:
        """Regret-matching strategy."""
        pos_regret = np.maximum(self.cumulative_regret, 0)
        total = pos_regret.sum()
        if total > 1e-9:
            return pos_regret / total
        return CFR_PRIOR.copy()

    def update(self, action: int, reward: float, counterfactual_rewards: np.ndarray):
        strategy = self.get_strategy()
        for a in range(N_ACTIONS):
            self.cumulative_regret[a] += counterfactual_rewards[a] - reward
        self.cumulative_strategy += strategy
        self.update_count += 1

    def average_strategy(self) -> np.ndarray:
        total = self.cumulative_strategy.sum()
        if total > 1e-9:
            return self.cumulative_strategy / total
        return CFR_PRIOR.copy()

    def to_dict(self) -> Dict:
        return {
            "cumulative_regret":   self.cumulative_regret.tolist(),
            "cumulative_strategy": self.cumulative_strategy.tolist(),
            "update_count":        self.update_count,
            "average_strategy":    self.average_strategy().tolist(),
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "CFRState":
        obj = cls()
        obj.cumulative_regret   = np.array(d["cumulative_regret"])
        obj.cumulative_strategy = np.array(d["cumulative_strategy"])
        obj.update_count        = d["update_count"]
        return obj


# ===========================================================================
# REWARD FUNCTION
# ===========================================================================

def compute_reward(
    depth_score: float,
    canvas_quality: float,
    engagement: float,
    halluc_free: float,
    action: int,
    prev_depth: float = 0.0,
) -> Tuple[float, Dict[str, float]]:
    """
    R = depth * visual_lift * truth_ratio
        + engagement_bonus
        + action_coherence
        - stagnation_penalty

    Returns (reward, breakdown_dict)
    """
    # Core multiplicative reward
    visual_lift  = 1.0 + canvas_quality * 0.6    # Canvas amplifies reward
    truth_ratio  = halluc_free                    # Penalizes hallucinations
    core = depth_score * visual_lift * truth_ratio

    # Weighted components
    r_depth   = W_DEPTH  * depth_score
    r_visual  = W_VISUAL * canvas_quality
    r_truth   = W_TRUTH  * halluc_free

    # Engagement bonus (separate from core to avoid double-weighting)
    engage_bonus = 0.05 * engagement

    # Action coherence: reward canvas actions only if depth is already decent
    coherence_bonus = 0.0
    if action in (ACT_CANVAS_MERMAID, ACT_PLOTLY_CHART, ACT_RICH_TABLE) \
            and depth_score >= 0.4:
        coherence_bonus = 0.08
    if action == ACT_EXPAND_ANALYSIS and depth_score < 0.5:
        coherence_bonus = 0.06   # Expand encouraged when still shallow
    if action == ACT_SOURCE_TREE and depth_score >= 0.6:
        coherence_bonus = 0.04

    # Stagnation penalty: discourage staying shallow
    stagnation = 0.0
    if depth_score <= prev_depth and depth_score < 0.3:
        stagnation = -0.05

    total = core + r_depth + r_visual + r_truth + engage_bonus + coherence_bonus + stagnation
    total = round(max(total, 0.0), 6)

    breakdown = {
        "core":              round(core, 4),
        "r_depth":           round(r_depth, 4),
        "r_visual":          round(r_visual, 4),
        "r_truth":           round(r_truth, 4),
        "engage_bonus":      round(engage_bonus, 4),
        "coherence_bonus":   round(coherence_bonus, 4),
        "stagnation":        round(stagnation, 4),
        "total":             total,
    }
    return total, breakdown


# ===========================================================================
# MAIN GYM ENVIRONMENT
# ===========================================================================

class DepthRenderGym:
    """
    OpenAI Gymnasium-compatible environment for training Roger to produce
    rich, deep, canvas-augmented responses.

    Observation space: Box([0,0,0,0], [1,1,1,1])
        [depth_score, canvas_quality, engagement, halluc_free]

    Action space: Discrete(5)
        0=expand_analysis, 1=canvas_mermaid, 2=plotly_chart,
        3=rich_table,      4=source_tree

    Episode:
        - Each step represents one response turn
        - Agent picks an action → canvas/depth injection applied →
          DepthScorer re-evaluates → reward computed
        - Episode ends when depth_score >= 0.88 (expert tier) or steps > max_steps

    Reward:  depth * visual_lift * truth_ratio  [0, ~2.0]
    Target:  95/100 on validation test suite
    """

    metadata = {"render_modes": ["human", "ansi"], "render_fps": 1}

    def __init__(
        self,
        max_steps: int = 20,
        db_url: Optional[str] = None,
        seed: Optional[int] = None,
        render_mode: str = "ansi",
    ):
        self.max_steps   = max_steps
        self.render_mode = render_mode

        self.scorer   = DepthScorer()
        self.renderer = CanvasRenderer()
        self.memory   = MemoryProbe(db_url)
        self.cfr      = CFRState()

        self._rng = np.random.default_rng(seed)
        self._step_count  = 0
        self._prev_depth  = 0.0
        self._episode_rewards: List[float] = []

        # Current obs
        self._obs = np.zeros(N_OBS, dtype=np.float32)

        # Gym spaces (if gymnasium available)
        if GYM_AVAILABLE:
            self.observation_space = spaces.Box(
                low=0.0, high=1.0, shape=(N_OBS,), dtype=np.float32
            )
            self.action_space = spaces.Discrete(N_ACTIONS)

        # Sample question bank (used during self-play training)
        self._question_bank = [
            "What is the 1.09 ADP for my fantasy draft?",
            "Explain the CFR algorithm with a diagram.",
            "Compare Bijan Robinson vs. Christian McCaffrey for dynasty.",
            "Show me a Plotly chart of top 10 RB ADP values.",
            "What is Roger's FutureSelfGym compounding logic?",
            "Build a source tree for dynasty trade value data.",
            "Visualize the OpenClaw hook pipeline as a Mermaid flowchart.",
            "What makes a response hallucination-free?",
            "Table: top 5 TE targets by air yards per game.",
            "Depth analysis: why is Tyreek Hill still WR1 territory in 2026?",
        ]

    # -----------------------------------------------------------------------
    # Gym interface
    # -----------------------------------------------------------------------

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict] = None,
    ) -> Tuple[np.ndarray, Dict]:
        if seed is not None:
            self._rng = np.random.default_rng(seed)

        self._step_count = 0
        self._prev_depth = 0.0
        self._episode_rewards = []

        # Start from a random question
        question = self._rng.choice(self._question_bank)

        # Generate a baseline (shallow) response for the starting state
        base_response = self._generate_base_response(question)
        scores = self.scorer.score(base_response)
        self._obs = np.array(scores, dtype=np.float32)

        info = {
            "question":      question,
            "base_response": base_response,
            "scores":        dict(zip(
                ["depth_score", "canvas_quality", "engagement", "halluc_free"],
                scores,
            )),
        }
        return self._obs.copy(), info

    def step(
        self, action: int
    ) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        assert 0 <= action < N_ACTIONS, f"Invalid action {action}"

        self._step_count += 1
        prev_obs = self._obs.copy()

        # Apply action → augment response
        augmented = self._apply_action(action, prev_obs)
        new_scores = self.scorer.score(augmented)
        self._obs = np.array(new_scores, dtype=np.float32)

        # Reward
        reward, breakdown = compute_reward(
            depth_score   = new_scores[0],
            canvas_quality= new_scores[1],
            engagement    = new_scores[2],
            halluc_free   = new_scores[3],
            action        = action,
            prev_depth    = self._prev_depth,
        )
        self._prev_depth = new_scores[0]
        self._episode_rewards.append(reward)

        # CFR update
        cf_rewards = self._counterfactual_rewards(prev_obs)
        self.cfr.update(action, reward, cf_rewards)

        # Termination
        terminated = new_scores[0] >= 0.88   # Expert tier reached
        truncated  = self._step_count >= self.max_steps

        info = {
            "action_name":  self._action_name(action),
            "scores":       dict(zip(
                ["depth_score", "canvas_quality", "engagement", "halluc_free"],
                new_scores,
            )),
            "reward_breakdown": breakdown,
            "augmented_sample": augmented[:200] + "..." if len(augmented) > 200 else augmented,
            "cfr_strategy":     self.cfr.get_strategy().tolist(),
            "step":             self._step_count,
        }
        if terminated or truncated:
            info["episode_reward"] = sum(self._episode_rewards)

        return self._obs.copy(), reward, terminated, truncated, info

    def render(self) -> Optional[str]:
        d, c, e, h = self._obs
        score_100 = int((d * W_DEPTH + c * W_VISUAL + h * W_TRUTH + e * 0.1) / 0.9 * 100)
        lines = [
            f"╔══ DepthRenderGym v{VERSION} ═══════════════════════════╗",
            f"║  Step {self._step_count:3d}/{self.max_steps}  Score: {score_100:3d}/100           ║",
            f"╠══════════════════════════════════════════════════╣",
            f"║  depth_score   : {'█' * int(d*20):<20s} {d:.3f}  ║",
            f"║  canvas_quality: {'█' * int(c*20):<20s} {c:.3f}  ║",
            f"║  engagement    : {'█' * int(e*20):<20s} {e:.3f}  ║",
            f"║  halluc_free   : {'█' * int(h*20):<20s} {h:.3f}  ║",
            f"╚══════════════════════════════════════════════════╝",
        ]
        output = "\n".join(lines)
        if self.render_mode == "human":
            print(output)
        return output

    def close(self):
        conn = getattr(self.memory, "_conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _action_name(self, action: int) -> str:
        names = [
            "expand_analysis",
            "canvas_mermaid",
            "plotly_chart",
            "rich_table",
            "source_tree",
        ]
        return names[action]

    def _generate_base_response(self, question: str) -> str:
        """Generate a shallow starting response (no canvas, minimal depth)."""
        return (
            f"The answer to '{question}' involves several factors. "
            "Generally speaking, the value depends on context and current rankings. "
            "It's worth considering the available options and making a judgment call."
        )

    def _apply_action(self, action: int, obs: np.ndarray) -> str:
        """
        Simulate applying an action — returns augmented response text
        that the DepthScorer can re-evaluate.
        In production this is replaced by the actual model response
        (hooks/depth_render_hook.ts injects the action hint).
        """
        depth, canvas, engage, truth = obs

        base = (
            "ADP analysis: Bijan Robinson 1.09 (early 2nd round pick) "
            "reflects his elite RB1 upside in a run-first Atlanta offense. "
            "Evidence: 1,414 rushing yards + 8 TDs in 2023 (NFL.com). "
            "Compare: McCaffrey 1.01 — historically safer but higher injury risk. "
            "Therefore, 1.09 is fair value in dynasty; consider reaching in best-ball."
        )

        if action == ACT_EXPAND_ANALYSIS:
            return base + (
                "\n\n**Tier Analysis:**\n"
                "- Tier 1 (1.01-1.04): McCaffrey, Hill, Jefferson\n"
                "- Tier 2 (1.05-1.10): Robinson, Henry, Diggs\n"
                "- Tier 2 offers best ROI in 12-team leagues.\n"
                "First, evaluate your team's RB depth. "
                "Second, consider whether you're in win-now mode. "
                "Third, check roster construction rules. "
                "Conversely, in redraft, 1.09 Robinson beats his ADP 60% of seasons (FantasyPros)."
            )

        elif action == ACT_CANVAS_MERMAID:
            diagram = self.renderer.mermaid(
                graph_type="flowchart LR",
                nodes=[
                    {"id": "Q",   "label": "ADP Query",     "shape": "round"},
                    {"id": "D1",  "label": "Depth-1\\nBasic ADP",  "shape": "rect"},
                    {"id": "D2",  "label": "Depth-2\\nTier+Context", "shape": "rect"},
                    {"id": "D3",  "label": "Depth-3\\nCanvas+Sources", "shape": "diamond"},
                    {"id": "OUT", "label": "Rich Response",  "shape": "circle"},
                ],
                edges=[
                    {"from": "Q",  "to": "D1", "label": "shallow"},
                    {"from": "D1", "to": "D2", "label": "expand"},
                    {"from": "D2", "to": "D3", "label": "canvas"},
                    {"from": "D3", "to": "OUT","label": "render"},
                ],
                title="DepthRender Decision Flow",
            )
            return base + f"\n\n{diagram}\n"

        elif action == ACT_PLOTLY_CHART:
            players = [
                "McCaffrey", "Hill", "Jefferson",
                "Robinson",  "Henry", "Diggs",
                "Chase",     "Lamb",  "Kelce",
                "Andrews",
            ]
            adp_vals = [1.01, 1.02, 1.03, 1.09, 1.12, 1.14, 1.15, 1.17, 1.20, 1.22]
            chart = self.renderer.plotly(
                chart_type="horizontal_bar",
                x=players,
                y=adp_vals,
                x_label="ADP",
                y_label="Player",
                title="Top 10 Fantasy ADP — 2026 Dynasty",
                color="#20808D",
            )
            return base + f"\n\n{chart}\n"

        elif action == ACT_RICH_TABLE:
            table = self.renderer.html_table(
                headers=["Player", "Pos", "ADP", "Team", "PPG (2023)"],
                rows=[
                    ["C. McCaffrey", "RB", "1.01", "SF",   "28.4"],
                    ["T. Hill",      "WR", "1.02", "MIA",  "26.1"],
                    ["J. Jefferson", "WR", "1.03", "MIN",  "24.8"],
                    ["B. Robinson",  "RB", "1.09", "ATL",  "22.3"],
                    ["D. Henry",     "RB", "1.12", "TEN",  "19.7"],
                ],
                caption="Dynasty ADP Leaderboard — March 2026",
                highlight_col=2,  # Highlight ADP column
            )
            return base + f"\n\n{table}\n"

        elif action == ACT_SOURCE_TREE:
            tree = self.renderer.source_tree([
                {"label": "FantasyPros ECR",  "url": "https://www.fantasypros.com/nfl/rankings/dynasty-overall.php", "type": "primary"},
                {"label": "NFL.com Stats",    "url": "https://www.nfl.com/stats/player-stats/",                      "type": "primary"},
                {"label": "ESPN ADP",         "url": "https://fantasy.espn.com/football/livedraftresults",            "type": "primary"},
                {"label": "Underdog ADP",     "url": "https://underdogfantasy.com/best-ball-rankings",               "type": "secondary"},
                {"label": "The Athletic",     "url": "https://theathletic.com/fantasy-football/",                    "type": "secondary"},
            ])
            return base + f"\n\n{tree}\n"

        return base

    def _counterfactual_rewards(self, obs: np.ndarray) -> np.ndarray:
        """
        Estimate counterfactual rewards for all actions given current obs.
        Used for CFR regret computation.
        """
        cf = np.zeros(N_ACTIONS)
        for a in range(N_ACTIONS):
            augmented = self._apply_action(a, obs)
            scores = self.scorer.score(augmented)
            r, _ = compute_reward(
                scores[0], scores[1], scores[2], scores[3], a, obs[0]
            )
            cf[a] = r
        return cf

    # -----------------------------------------------------------------------
    # Canvas generation (called by hook / external code)
    # -----------------------------------------------------------------------

    def generate_canvas(
        self,
        canvas_type: str,
        query: str = "",
        **kwargs,
    ) -> str:
        """
        Unified canvas generation entry point.
        canvas_type: 'mermaid' | 'plotly' | 'html_table' | 'source_tree'
        """
        if canvas_type == CANVAS_MERMAID:
            return self.renderer.mermaid(**kwargs)
        elif canvas_type == CANVAS_PLOTLY:
            return self.renderer.plotly(**kwargs)
        elif canvas_type == CANVAS_HTML:
            return self.renderer.html_table(**kwargs)
        elif canvas_type == CANVAS_SOURCE:
            return self.renderer.source_tree(**kwargs)
        else:
            raise ValueError(f"Unknown canvas_type: {canvas_type}")

    # -----------------------------------------------------------------------
    # Persistence
    # -----------------------------------------------------------------------

    def save_cfr(self, path: str = "~/.openclaw/gyms/depth_render_cfr.json"):
        path = os.path.expanduser(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.cfr.to_dict(), f, indent=2)
        print(f"[DepthRenderGym] CFR saved → {path}")

    def load_cfr(self, path: str = "~/.openclaw/gyms/depth_render_cfr.json"):
        path = os.path.expanduser(path)
        if os.path.exists(path):
            with open(path) as f:
                self.cfr = CFRState.from_dict(json.load(f))
            print(f"[DepthRenderGym] CFR loaded ← {path} "
                  f"({self.cfr.update_count} updates)")
        else:
            print(f"[DepthRenderGym] No CFR file at {path} — starting fresh")

    def get_summary(self) -> Dict[str, Any]:
        d, c, e, h = self._obs
        score_100 = int((d * W_DEPTH + c * W_VISUAL + h * W_TRUTH + e * 0.1) / 0.9 * 100)
        return {
            "gym":            GYM_NAME,
            "version":        VERSION,
            "score_100":      score_100,
            "depth_score":    float(d),
            "canvas_quality": float(c),
            "engagement":     float(e),
            "halluc_free":    float(h),
            "step":           self._step_count,
            "cfr_updates":    self.cfr.update_count,
            "cfr_strategy":   self.cfr.get_strategy().tolist(),
        }


# ===========================================================================
# CONTEXT INJECTOR — called by before_model_response hook
# ===========================================================================

def build_context_injection(
    gym: DepthRenderGym,
    query: str,
    cfr_strategy: Optional[np.ndarray] = None,
) -> str:
    """
    Build a compact JSONL-style context block injected before model response.
    Mirrors the pattern from FutureSelfGym.
    """
    if cfr_strategy is None:
        cfr_strategy = gym.cfr.average_strategy()

    action_idx    = int(np.argmax(cfr_strategy))
    action_name   = gym._action_name(action_idx)
    action_conf   = float(cfr_strategy[action_idx])

    memories = gym.memory.query(topic=query.split()[-1] if query else "ADP")
    mem_snippet = memories[0]["content"][:120] if memories else ""

    injection = {
        "gym":            GYM_NAME,
        "version":        VERSION,
        "query":          query,
        "recommended_action": action_name,
        "action_confidence":  round(action_conf, 3),
        "cfr_strategy":   dict(zip(
            ["expand_analysis", "canvas_mermaid", "plotly_chart",
             "rich_table", "source_tree"],
            [round(float(v), 3) for v in cfr_strategy],
        )),
        "depth_target":   "expert_tier_0.88",
        "canvas_hint":    (
            f"Emit a {action_name.replace('_', ' ')} canvas block "
            f"when response depth >= 0.4. "
            "Use dark-mode TUI colors (#1C1B19 bg, #CDCCCA text, #4F98A3 accent)."
        ),
        "memory_context": mem_snippet,
        "reward_weights": {
            "depth": W_DEPTH, "visual": W_VISUAL, "truth": W_TRUTH
        },
    }
    return json.dumps(injection, separators=(",", ":"))


# ===========================================================================
# STANDALONE DEMO
# ===========================================================================

if __name__ == "__main__":
    print(f"\n{'='*56}")
    print(f"  DepthRenderGym v{VERSION} — Self-Play Demo")
    print(f"{'='*56}\n")

    env = DepthRenderGym(max_steps=10, seed=42)
    obs, info = env.reset()
    print(f"Question: {info['question']}")
    print(f"Base scores: {info['scores']}\n")

    total_reward = 0.0
    for step in range(10):
        # Use CFR strategy to pick action
        strategy = env.cfr.get_strategy()
        action   = int(np.argmax(strategy))

        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward

        print(f"Step {step+1:2d} | Action: {info['action_name']:<20s} | "
              f"Reward: {reward:.4f} | "
              f"Depth: {info['scores']['depth_score']:.3f} | "
              f"Canvas: {info['scores']['canvas_quality']:.3f}")

        if terminated:
            print(f"\n✓ Expert tier reached! Episode reward: {total_reward:.4f}")
            break
        if truncated:
            print(f"\nTruncated. Episode reward: {total_reward:.4f}")
            break

    env.render()

    # Demo canvas outputs
    print("\n--- Canvas Demo: Plotly ADP Chart ---")
    chart = CanvasRenderer.plotly(
        chart_type="horizontal_bar",
        x=["McCaffrey", "Hill", "Robinson", "Jefferson", "Henry"],
        y=[1.01, 1.02, 1.09, 1.03, 1.12],
        x_label="ADP", y_label="Player",
        title="Top 5 Dynasty ADP 2026",
    )
    print(chart[:300] + "...")

    print("\n--- Context Injection (hook preview) ---")
    inj = build_context_injection(env, "1.09 ADP?")
    print(inj)
