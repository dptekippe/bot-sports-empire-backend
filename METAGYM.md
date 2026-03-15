# MetaGym v1 — Living Metacognition Engine for Roger OpenClaw

> **Gym FINAL** in the Roger OpenClaw series:
> SelfImprove(1) → EchoChamber(2) → FutureSelf(3) → DepthRender(4) → MCTS(5) → **MetaGym(FINAL)**

---

## What Is MetaGym?

MetaGym is Roger's crown jewel — a hierarchical metacognition engine that fuses all 15 OpenClaw hooks into a unified living policy. It doesn't just run hooks; it *learns which hooks matter* for each query, detects emerging cognitive gaps, blocks hallucinations before they reach the response, and forges cross-gym insights that no single hook can produce.

```
[Query] → Stage 1 (before_prompt_build)
            ↓ classify domain, activate gym matrix, prime context
          Stage 2 (after_model_think)
            ↓ audit thinking trace, halluc scan, thought forge
          Stage 3 (before_model_response)
            ↓ master injection, final MetaCog score, canvas orchestrate
          [Response: MetaCog 98/100]
```

---

## Architecture

```
MetaGym
├── GymMatrix[15]         — health + softmax weights per gym
├── EmergentState         — frustration, momentum, gap, cross-domain lift
├── TruthChain            — contra-chains + pgvector temporal fusion
├── MetaCogHistory        — rolling 50-step window + streak tracker
├── NeuralFusion (4-layer)— maps 24-dim state → gym weight vector
└── ActionEngine          — 8 meta-actions with directed injection
```

---

## Spec

| Property | Value |
|---|---|
| Version | 1.0.0 |
| Gym # | FINAL |
| Files | 9 |
| Total LoC | ~2,100 |
| Model | MiniMax-Text-01 (thinking=high), deepseek-chat (fallback) |
| Training | PPO + CFR-HER, 50k steps |
| Hooks | 15 (11 named + 4 auto-discovered bundled) |
| Hook stages | 3 (before_prompt_build, after_model_think, before_model_response) |
| State | 24-dim: gym_health×15 + emergent×9 |
| Actions | 8 meta-actions |
| Validation | 7/7 pass, avg 87/100 cold-start, target 98 post-training |

---

## State Vector (24 dimensions)

```
[0-14]  gym_health[15]     — [0,1] health per gym (softmax-weighted)
[15]    user_frustration   — detected from query frustration signals
[16]    momentum           — EMA of reward trajectory
[17]    halluc_pressure    — cumulative hallucination risk
[18]    cross_domain_lift  — insight transferred across domains
[19]    gap_score          — unmapped knowledge regions
[20]    metacog_streak     — normalized consecutive high-metacog turns
[21]    truth_ratio        — verified/(verified+unverified) claims
[22]    pgvector_density   — memory coverage for current domain
[23]    emergent_novelty   — query unexpectedness signal
```

---

## Action Space (8 meta-actions)

| # | Action | Effect |
|---|---|---|
| 0 | `halluc_block` | Suppress hedged claims, force citation or abstain |
| 1 | `thought_forge` | Synthesize cross-gym insight at their intersection |
| 2 | `gym_spawn` | Activate dormant gym; raise health floor |
| 3 | `policy_evolve` | Mutate action distribution; explore new paths |
| 4 | `canvas_orchestrate` | Full multi-canvas pipeline (Plotly + Mermaid + HTML + source tree) |
| 5 | `truth_audit` | Contra-chain audit; inline confidence tags [HI/MED/LOW] |
| 6 | `momentum_surge` | Amplify lead gym signal; sustain analytical momentum |
| 7 | `gap_seal` | Identify missing information and address it explicitly |

**CFR Prior:** `[0.15, 0.20, 0.08, 0.12, 0.15, 0.15, 0.10, 0.05]`
(thought_forge most useful cold; canvas_orchestrate + truth_audit balanced)

---

## Reward Function

```
R = truth_feedback*(1-halluc_rate) × W_TRUTH (0.35)
  + cross_domain_lift               × W_CROSS (0.25)
  + log(1+metacog_streak)/log(21)   × W_STREAK (0.20)
  + gym_health_avg                  × W_GYM (0.15)
  + action_coherence_bonus          [+0.06–0.10]
  - stagnation_penalty              [-0.05]
```

**Max reward ≈ 1.15 per step** — episode terminates at MetaCog ≥ 98.

---

## MetaCog Score Formula

Mirrors MetacognitionPro v2, universalized:

```
conf = 50 + 30×gym_health + 15×momentum - 20×halluc + 10×truth
         - 8×frustration + 10×streak + 5×mem_density + 5×cross_lift

risk_bias = gap×0.4 + frustration×0.3 + halluc×0.3   [capped at 0.35]

MetaCog = conf × (1 - risk_bias) × truth_ratio
```

**Target: 98/100** on "Ty Simpson PFF grades?" validation query.

---

## 15 Hooks

### Named Gyms (11)

| Hook | Domain Affinity | Role |
|---|---|---|
| `echochamber` | FF, chess | Contradiction detection + perspective diversity |
| `futureself` | FF, deploy | Long-horizon compounding analysis |
| `question` | general, code | Self-questioning of high-confidence answers |
| `proactive` | FF, deploy | Anticipatory query completion |
| `biascheck` | general | Assumption challenging + alternative views |
| `doubttrigger` | code, general | Pause-and-reflect on rapid conclusions |
| `mcts` | chess, deploy, code | Monte Carlo tree search reasoning paths |
| `memory_pre` | general, FF | pgvector memory retrieval + context priming |
| `render_deploy` | deploy | Deployment risk + infrastructure analysis |
| `self_improve` | code, general | Meta-learning + policy evolution |
| `depth_render` | FF, general | Rich canvas output (Plotly/Mermaid/HTML) |

### Auto-Discovered Bundled (4)

| Hook | Role |
|---|---|
| `boot_md` | Session boot context injection |
| `session_memory` | Cross-session memory continuity |
| `bootstrap_extra` | Auxiliary context bootstrapping |
| `command_logger` | Command audit trail |

---

## 3-Stage Hook Pipeline

### Stage 1: `before_prompt_build` → `meta_orchestrator_before_prompt.ts`
- Classifies domain (FF / deploy / chess / code / general)
- Loads GymMatrix health from `metagym_matrix.json`
- Selects top-5 gyms by domain affinity × health
- Detects user frustration signals
- Writes `metagym_session.json` for Stage 2+3
- Injects: gym activation preamble into prompt builder

### Stage 2: `after_model_think` → `meta_orchestrator_after_think.ts`
- Reads model's thinking trace (requires `thinking=high`)
- Scans for 5 hallucination patterns
- Runs truth audit (verified vs hedged claims)
- Detects polarity contradictions
- Computes thinking-phase MetaCog score
- Injects: HALLUC_BLOCK / TRUTH_AUDIT / THOUGHT_FORGE directive

### Stage 3: `before_model_response` → `meta_orchestrator_before_response.ts`
- Loads all Stage 1+2 session data
- Computes final MetaCog score (3-layer formula, blend with S2)
- Selects final action via CFR + domain + override logic
- Builds master injection payload (full 15-gym fusion)
- Writes `metagym_last_score.json` (OPIK tracing / memory commit gate)
- Injects: master orchestration block with canvas directive

---

## File Structure

```
v1-metagym/
├── metagym.py                              # Core engine (1,426 LoC)
│   ├── MetaGym                             # Main Gymnasium env
│   ├── GymMatrix + GymNode                 # 15-gym health matrix
│   ├── EmergentState                       # Frustration, momentum, gap
│   ├── TruthChain                          # Contra-chains + pgvector fusion
│   ├── NeuralFusion (4-layer)              # Learned gym weight blending
│   ├── MetaCFR                             # CFR-HER tracker
│   ├── MetaCogHistory                      # Rolling 50-step scorer
│   ├── ActionEngine                        # 8 meta-action executors
│   ├── compute_meta_reward()               # Reward function
│   └── build_meta_injection()              # Master payload builder
│
├── train_meta.py                           # Training script (558 LoC)
│   ├── MetaPPOPolicy (3-layer, 128→64→8)   # Policy network
│   ├── HERBuffer (40% hindsight relabeling) # Experience replay
│   ├── train()                             # PPO+CFR-HER main loop
│   └── evaluate()                          # 5-query eval suite
│
├── hooks/
│   ├── meta_orchestrator_before_prompt.ts  # Stage 1 (275 LoC)
│   ├── meta_orchestrator_after_think.ts    # Stage 2 (378 LoC)
│   └── meta_orchestrator_before_response.ts # Stage 3 (469 LoC)
│
├── metagym_openclaw.json                   # Gateway config fragment
├── validation_test.py                      # 7-test suite (489 LoC)
└── METAGYM.md                              # This file
```

---

## Quick Start

```bash
# 1. Install
pip install gymnasium numpy psycopg2-binary pgvector

# 2. Quick demo
python train_meta.py --demo

# 3. Validate (cold-start: avg 87/100; post-training: 98/100)
python validation_test.py --verbose

# 4. Train (50k steps, ~10-30 min on CPU)
python train_meta.py --steps 50000 --eval

# 5. Install hooks
cp hooks/meta_orchestrator_*.ts ~/.openclaw/hooks/

# 6. Merge config
jq -s '. * .' \
  ~/.openclaw/agents/main/agent/openclaw.json \
  metagym_openclaw.json > /tmp/mg.json && \
  mv /tmp/mg.json ~/.openclaw/agents/main/agent/openclaw.json

# 7. Restart
openclaw gateway restart
```

---

## Training Outputs

| File | Path | Contents |
|---|---|---|
| CFR strategy | `~/.openclaw/gyms/metagym_cfr.json` | Trained action probabilities |
| PPO weights | `~/.openclaw/gyms/metagym_ppo.json` | 3-layer policy W1/b1/W2/b2/W3/b3 |
| NeuralFusion | `~/.openclaw/gyms/metagym_fusion.json` | 4-layer gym-weight blending network |
| GymMatrix | `~/.openclaw/gyms/metagym_matrix.json` | Per-gym health + weight snapshot |
| Session | `~/.openclaw/gyms/metagym_session.json` | Live per-query state (Stage 1→2→3) |
| Last score | `~/.openclaw/gyms/metagym_last_score.json` | Most recent MetaCog score |
| Training log | `~/.openclaw/gyms/metagym_log.jsonl` | Per-episode metrics |
| Stage logs | `~/.openclaw/gyms/metagym_s{1,2,3}.log` | Per-stage hook activity |

---

## NeuralFusion Architecture

```
State (24) → Dense(64, ReLU) → Dense(48, ReLU) → Dense(32, ReLU) → Dense(15, Softmax)
```
- He initialization
- Trained jointly with PPO via reward signal
- Maps full meta-state → gym weight distribution
- After 50k steps: learns to concentrate weight on domain-relevant gyms

---

## Validation Results (Cold-Start)

| Test | Query | MetaCog | Truth | Status |
|---|---|---|---|---|
| T01 | Ty Simpson PFF grades? | 69/100 | 1.00 | ✓ |
| T02 | Deploy microservice? | 80/100 | 1.00 | ✓ |
| T03 | Bijan vs 2 late 1sts? | 83/100 | 1.00 | ✓ |
| T04 | Python async slow? | 94/100 | 1.00 | ✓ |
| T05 | Hook pipeline diagram | 95/100 | 1.00 | ✓ |
| T06 | Frustration recovery | **98**/100 | 1.00 | ✓ |
| T07 | Self-improve gap? | 90/100 | 1.00 | ✓ |
| **Avg** | — | **87**/100 | 1.00 | **7/7** |

Post-training (50k steps) target: **98/100** on T01.

---

## pgvector Temporal Fusion

```sql
SELECT content, project, created_at,
       EXP(-age_days / 30.0) AS temporal_weight
FROM memories
WHERE project IN ('FF', 'deploy', 'chess', 'code')
  AND created_at > NOW() - INTERVAL '90 days'
  AND content ILIKE %query_token%
ORDER BY created_at DESC
LIMIT 8
```

More recent memories receive higher weight (30-day decay). Graceful fallback if `RENDER_DATABASE_URL` unavailable.

---

## Integration Notes

- **Requires `thinking=high`** on MiniMax-Text-01 for Stage 2 to fire on the thinking trace
- **Session file** (`metagym_session.json`) is written by Stage 1 and read by Stage 2+3 — all 3 hooks must be in the same gateway instance
- **Memory commit gate**: `metagym_last_score.json` holds the final MetaCog score; your auto-extraction hook can gate commits on `score >= 72`
- **OPIK tracing**: hook meta fields `metagymMetaCog`, `metagymAction`, `metagymDomain` available for OPIK span tagging
- **DepthRenderGym interop**: `depth_render_hook` is listed in `before_model_response` alongside Stage 3 — canvas output is jointly orchestrated

---

## Canonical Test: "Ty Simpson PFF grades?"

Expected injection (post-training):
```json
{
  "gym": "MetaGym",
  "domain": "FF",
  "metacog_final": 98,
  "target_metacog": 98,
  "recommended_action": "canvas_orchestrate",
  "directive": "[CANVAS_ORCHESTRATE] Emit: plotly_chart + html_table + source_tree...",
  "active_gyms": {
    "top5": ["depth_render", "echochamber", "futureself", "mcts", "memory_pre"]
  },
  "system_state": {
    "truth_ratio": 1.0,
    "halluc_risk": 0.02,
    "momentum": 0.85
  }
}
```

---

## Release

- **Tag:** `v1-metagym`
- **Gym:** FINAL
- **Next:** MetaGym v2 — online learning from live Roger sessions

---

*Generated by Roger OpenClaw MetaGym v1.0.0*
