# DepthRenderGym v1 — Rich Responses + OpenClaw Canvas

> Gym #4 in the Roger OpenClaw series: SelfImprove → EchoChamber → FutureSelf → **DepthRender**

---

## Overview

**DepthRenderGym** trains Roger to produce deep, well-structured responses with embedded Canvas output — Mermaid diagrams, Plotly charts, and HTML tables — rendered natively in the OpenClaw TUI WebKit pane and Web UI.

| Property | Value |
|---|---|
| Version | 1.0.0 |
| Gym # | 4 |
| Files | 6 (depth_render_gym.py, train_depth_render.py, hooks/depth_render_hook.ts, depth_render_openclaw.json, validation_test.py, DEPTHRENDER.md) |
| Total LoC | ~1,400 |
| Model | MiniMax-Text-01 (primary), deepseek-chat (fallback) |
| Training | PPO + CFR, 30k steps recommended |
| Test | `"1.09 ADP?" → Canvas ADP chart + 3-depth views [95/100]` |

---

## State · Actions · Reward

```
State:   [depth_score, canvas_quality, engagement, halluc_free]  — all ∈ [0,1]
Actions: expand_analysis | canvas_mermaid | plotly_chart | rich_table | source_tree
Reward:  depth * visual_lift * truth_ratio
         depth=0.45, visual=0.30, truth=0.25
```

**Reward formula:**
```
R = depth_score × (1 + 0.6 × canvas_quality) × halluc_free
  + engagement_bonus (0.05 × engagement)
  + action_coherence_bonus
  - stagnation_penalty
```

**Target:** `depth_score ≥ 0.88` (Expert tier) = episode termination.

---

## Canvas Output Types

| Canvas Type | Format | Trigger Keywords |
|---|---|---|
| `canvas_mermaid` | ` ```mermaid ` | diagram, flowchart, visualize, pipeline |
| `plotly_chart` | ` ```plotly ` | chart, graph, plot, ADP, trend |
| `rich_table` | ` ```html ` | table, ranking, top N, compare |
| `source_tree` | ` ```mermaid ` (mindmap) | source, cite, reference, prove |
| `expand_analysis` | Prose (markdown) | explain, why, analysis, deep |

All canvas outputs use dark-mode colors matching the TUI WebKit pane:
```
bg:      #1C1B19
surface: #201F1D
text:    #CDCCCA
accent:  #4F98A3
border:  #393836
```

---

## File Structure

```
v1-depthrender/
├── depth_render_gym.py           # Core Gymnasium env (~550 LoC)
│   ├── DepthRenderGym            # Main env (reset/step/render)
│   ├── CanvasRenderer            # Mermaid / Plotly / HTML / SourceTree
│   ├── DepthScorer               # Heuristic scorer [0,1]
│   ├── CFRState                  # CFR tracker + strategy
│   ├── MemoryProbe               # pgvector query (FF/deploy/chess)
│   ├── compute_reward()          # Reward function
│   └── build_context_injection() # Hook payload builder
│
├── train_depth_render.py         # PPO+CFR training script
│   ├── PPOPolicy                 # Softmax-linear policy
│   ├── train()                   # Main training loop
│   └── evaluate()                # Eval on 5 canonical queries
│
├── hooks/
│   └── depth_render_hook.ts      # before_model_response hook (TypeScript)
│       ├── loadCFRStrategy()     # Reads ~/.openclaw/gyms/depth_render_cfr.json
│       ├── classifyQuery()       # Trigger keywords + CFR blend
│       ├── buildCanvasHint()     # Canvas instruction per action
│       └── beforeModelResponse() # Main hook export
│
├── depth_render_openclaw.json    # Gateway config fragment
│
├── validation_test.py            # Validation suite (5 tests)
│   ├── run_three_depth_views()   # Shallow / Medium / Expert views
│   └── run_validation()          # Full suite + canvas renderer tests
│
└── DEPTHRENDER.md                # This file
```

---

## Quick Start

### 1. Install dependencies
```bash
pip install gymnasium numpy psycopg2-binary pgvector
```

### 2. Quick demo (no training required)
```bash
python train_depth_render.py --demo
```

### 3. Run validation
```bash
python validation_test.py --verbose
# Canonical test: "1.09 ADP?" → 3-depth views + canvas
```

### 4. Train (30k steps, ~5-15 min on CPU)
```bash
python train_depth_render.py --steps 30000 --eval
```

### 5. Install hook
```bash
cp hooks/depth_render_hook.ts ~/.openclaw/hooks/
# Merge depth_render_openclaw.json into your openclaw.json
openclaw gateway restart
```

---

## Training Output Files

| File | Path | Contents |
|---|---|---|
| CFR strategy | `~/.openclaw/gyms/depth_render_cfr.json` | Trained action probabilities |
| PPO weights | `~/.openclaw/gyms/depth_render_ppo.json` | Policy matrix W + bias b |
| Training log | `~/.openclaw/gyms/depth_render_log.jsonl` | Per-episode metrics |
| Hook log | `~/.openclaw/gyms/depth_render_hook.log` | Per-query action selections |
| Results | `depth_render_results.json` | Final training summary |
| Validation | `depth_render_validation.json` | Validation suite results |

---

## Hook Behavior

The `depth_render_hook.ts` fires `before_model_response` and injects:

```json
{
  "gym": "DepthRenderGym",
  "recommended_action": "plotly_chart",
  "action_confidence": 0.312,
  "depth_target": "expert_tier (depth >= 0.88)",
  "canvas_hint": "Emit a Plotly JSON chart spec as a fenced ```plotly block...",
  "cfr_strategy": {
    "expand_analysis": 0.30,
    "canvas_mermaid":  0.22,
    "plotly_chart":    0.20,
    "rich_table":      0.18,
    "source_tree":     0.10
  }
}
```

**Query classification logic:**
- Hard triggers: `diagram` → mermaid, `chart/plot` → plotly, `table/ranking` → html, `source/cite` → source_tree
- ADP/fantasy queries: boost `plotly_chart` (×1.5) and `rich_table` (×1.3)
- Deep/explain queries: boost `expand_analysis` (×1.4)
- Default: follow CFR average strategy

---

## Validation Test: "1.09 ADP?"

The canonical test runs 3 depth views on the query `"1.09 ADP?"`:

| View | Actions | Depth Target |
|---|---|---|
| 1 — Shallow | `expand_analysis` | ≥ 0.35 |
| 2 — Medium  | `expand_analysis` + `rich_table` | ≥ 0.50 |
| 3 — Expert  | `expand_analysis` + `plotly_chart` + `rich_table` + `source_tree` | ≥ 0.70 |

**Pass criteria:**
- `avg_score ≥ 90/100` (target: 95)
- `canvas_quality ≥ 0.45` on ≥ 3 of 5 tests
- `halluc_free ≥ 0.85` on all tests
- All 4 canvas renderers valid

---

## CFR Prior (Pre-trained)

```python
[0.30, 0.22, 0.20, 0.18, 0.10]
# expand  mermaid  plotly  table  source
```

Reflects: analysis depth is the foundation; chart/table for data queries; mermaid for architecture; source tree for citability.

After 30k training steps the CFR learns to down-weight `expand_analysis` for data-heavy queries (FF/ADP) and up-weight `plotly_chart` + `rich_table`.

---

## Integration with Other Gyms

| Gym | Interaction |
|---|---|
| **SelfImproveGym** | Depth targets align: SelfImprove raises `conf_score`, DepthRender raises `depth_score` |
| **EchoChamberGym** | Echo reduces `halluc_free` risk; DepthRender's `truth_ratio` rewards halluc-free output |
| **FutureSelfGym** | Memory probe shares same pgvector schema; `project IN ('FF','deploy','chess')` |
| **MetaGym** (future) | DepthRender contributes `depth_score` + `canvas_quality` to meta-state |

---

## Memory Probe

Queries the same `memories` table as FutureSelfGym:

```sql
SELECT content, project, created_at
FROM memories
WHERE project IN ('FF', 'deploy', 'chess')
  AND created_at > NOW() - INTERVAL '90 days'
  AND content ILIKE %topic%
ORDER BY created_at DESC
LIMIT 5
```

Set `RENDER_DATABASE_URL` env var or pass `db_url=` to constructor. Graceful fallback if unavailable.

---

## Reward Deep-Dive

| Component | Formula | Max |
|---|---|---|
| Core | `depth × (1 + 0.6×canvas) × halluc_free` | ~1.6 |
| r_depth | `0.45 × depth_score` | 0.45 |
| r_visual | `0.30 × canvas_quality` | 0.30 |
| r_truth | `0.25 × halluc_free` | 0.25 |
| engage_bonus | `0.05 × engagement` | 0.05 |
| coherence_bonus | Action-specific, +0.04–0.08 | 0.08 |
| stagnation | `-0.05` if no depth improvement | -0.05 |
| **Total** | | **~2.69** |

---

## Release

- **Tag:** `v1-depthrender`
- **Gym #:** 4
- **Next:** QuestionGym → self-questions high-confidence answers

---

*Generated by Roger OpenClaw DepthRenderGym v1.0.0*
