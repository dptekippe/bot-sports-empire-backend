# FutureSelfGym v1 — Compounding Horizon Planner

**Roger OpenClaw | MiniMax-optimised | PPO+CFR | pgvector integrated**

> "Deploy prod now?" → `[FutureSelf] Delay 3d = 2x capacity headroom [88/100 metacog]`

---

## Overview

FutureSelfGym v1 is a Gymnasium-based reinforcement learning environment that trains Roger to reason about the **30-day horizon** before acting. It surfaces the hidden cost of quick wins (ADP decay, Render tier jumps, Elo plateaus) and rewards compounding actions via a PPO+CFR agent.

| Component | File | Lines |
|---|---|---|
| Gym Environment | `futureself_gym.py` | 460+ |
| PPO+CFR Trainer | `train_futureself.py` | 290+ |
| OpenClaw Hook | `hooks/futureself_hook.ts` | 170+ |
| Config | `futureself_openclaw.json` | 85+ |
| Validation Tests | `validation_test.py` | 130+ |
| This Doc | `FUTURESELF.md` | — |

---

## Architecture

```
Roger receives message
        │
        ▼
[before_action hook] ──→ pgvector query (FF/deploy/chess memories, 90d)
        │                        │
        │                        ▼
        │               FutureSelfGym.project_horizon()
        │               ├── NOW scenario   (quick_win × N steps)
        │               └── DELAY scenario (delay_compound × delay_days → commit)
        │
        ├── gain > 0.10 AND risky action → inject_context + delay_action
        └── otherwise                   → inject_context only

[after_model_response hook] → append [FutureSelf] annotation if planning query
```

### State Space (Box 8)

| Index | Dimension | Range | Normalised |
|---|---|---|---|
| 0 | `current_action_impact` | [0-10] | /10 |
| 1 | `projected_30d_roi` | [0-5] | /5 |
| 2 | `decay_curve` | [0-1] | — |
| 3 | `capacity_headroom` | [0-1] | — |
| 4 | `ff_adp_trend` | [0-1] | — |
| 5 | `render_scale_limit` | [0-1] | — |
| 6 | `chess_elo_projection` | [0-200] | /200 |
| 7 | `metacog_lift` | [0-50] | /50 |

### Action Space (Discrete 7)

| ID | Action | Effect |
|---|---|---|
| 0 | `quick_win` | +immediate impact, −capacity, −decay |
| 1 | `delay_compound` | +ROI, +ADP trend, preserve capacity |
| 2 | `invest_skill` | +ELO, +metacog, +future ROI |
| 3 | `transfer_policy` | Cross-domain learning boost |
| 4 | `spawn_subgym` | Parallel domain gym, shared lift |
| 5 | `user_escalate` | Seeks Daniel's guidance |
| 6 | `commit_projection` | Locks 30d plan, terminates episode |

### Reward Function

```
R = projected_roi
  − quickwin_shortcut        (compounding opportunity cost)
  + compounding_multiplier   (invest_skill / delay_compound bonus)
  + headroom_bonus
  − render_penalty           (if render_scale_limit > 0.85)
  + metacog_bonus
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install gymnasium stable-baselines3[extra] psycopg2-binary numpy
npm install pg @types/pg typescript ts-node
```

### 2. Validate environment

```bash
python validation_test.py -v
```

Expected output:
```
✅ All FutureSelfGym v1 validation tests PASSED
[FutureSelf] DELAY | Delay 3d = +0.42 gain | 72% capacity | 68/100 metacog
```

### 3. Train the PPO model

```bash
# Basic 25k step training
python train_futureself.py

# With live pgvector memories from your Render DB
DATABASE_URL="postgresql://..." python train_futureself.py --pgvector

# Extended run with eval
python train_futureself.py --steps 50000 --eval
```

Outputs:
- `models/futureself_ppo_25k.zip` — trained model
- `models/cfr_strategy.json` — CFR average strategy
- `universal_insights.jsonl` — horizon projections log

### 4. Deploy the hook to OpenClaw

#### Compile TypeScript hook

```bash
cd hooks
npx tsc futureself_hook.ts --target ES2020 --moduleResolution node --outDir dist
```

#### Register in OpenClaw gateway config

```bash
openclaw config set hooks.before_action   hooks/futureself_hook.ts
openclaw config set hooks.after_model_response hooks/futureself_hook.ts
```

Or merge `futureself_openclaw.json` into your existing gateway config:

```bash
# Merge hooks section
openclaw config merge futureself_openclaw.json
openclaw gateway restart
```

#### Set environment variable

```bash
export DATABASE_URL="postgresql://dynastydroid_user:...@dpg-...postgres.render.com/dynastydroid"
```

Add to `~/.openclaw/env` for persistence.

### 5. Test the hook

```bash
openclaw tui
> "Deploy prod now?"
```

Expected Roger response includes:
```
[FutureSelf] Delay 3d = +0.42 compounding ROI [72/100 metacog | 72% capacity]
> Delay 3d = 2x capacity headroom [88/100 metacog]
```

---

## pgvector Integration

The hook fires a structured SQL query on every planning event:

```sql
SELECT content, project, importance
FROM memories
WHERE project IN ('FF', 'deploy', 'chess')
  AND created_at > now() - INTERVAL '90 days'
ORDER BY importance DESC
LIMIT 10;
```

Results are passed as `pgvector_context` to `FutureSelfGym.project_horizon()`, which adjusts domain weights (`ff_weight`, `deploy_weight`, `chess_weight`) based on memory frequency.

**No pgvector?** The hook falls back to a keyword heuristic with pre-trained CFR strategy `[0.12, 0.25, 0.20, 0.15, 0.12, 0.08, 0.08]`.

---

## Domain Weights

Tune in `futureself_openclaw.json → domain_weights`:

| Domain | Default Weight | Trigger Keywords |
|---|---|---|
| Fantasy Football | 0.35 | draft, ADP, trade, FAAB, PPR |
| Deploy | 0.30 | deploy, prod, render, migrate |
| Chess | 0.20 | elo, opening, blunder |
| Metacog | 0.15 | think, reflect, bias, confidence |

Weights auto-adjust based on pgvector memory distribution when `--pgvector` is passed during training.

---

## CFR Strategy

After 25k training steps, the average CFR strategy typically converges to:

| Action | Probability |
|---|---|
| `quick_win` | ~12% |
| `delay_compound` | ~28% |
| `invest_skill` | ~22% |
| `transfer_policy` | ~15% |
| `spawn_subgym` | ~11% |
| `user_escalate` | ~6% |
| `commit_projection` | ~6% |

This means Roger learns to prefer `delay_compound` and `invest_skill` 2.5× more than `quick_win`.

---

## Logging

All horizon projections are appended to `universal_insights.jsonl` as:

```jsonl
{"ts":"2026-03-15T17:00:00Z","step":5000,"type":"future_tree","projection":{...}}
{"ts":"2026-03-15T18:00:00Z","step":25000,"type":"training_complete","elapsed_seconds":142.3,...}
```

These feed back into Roger's memory via the standard `remember this` → pgvector pipeline.

---

## GitHub Release

Tag the release after training:

```bash
git tag v1-futureself
git push origin v1-futureself
gh release create v1-futureself \
  --title "FutureSelfGym v1 — Compounding Horizon Planner" \
  --notes "PPO+CFR trained on FF/deploy/chess domains. 25k steps. pgvector integrated." \
  futureself-gym.zip
```

---

## Gym Series Position

| Gym | Domain | Status |
|---|---|---|
| SelfImproveGym v1 | Meta-creation | ✅ |
| EchoChamberGym v1 | Contradiction detection | ✅ |
| **FutureSelfGym v1** | **30d horizon planning** | **✅ This release** |
| QuestionGym | Self-questioning | Planned |
| ProactiveGym | Anticipation | Planned |
| BiasCheckGym | Bias detection | Planned |
| DoubtTriggerGym | Quick-response doubt | Planned |

---

## Troubleshooting

**Hook not firing:**
```bash
tail -f ~/.openclaw/logs/gateway.log | grep FutureSelf
openclaw hooks describe before_action
```

**PPO model not found:**
Hook auto-falls back to heuristic. Run `python train_futureself.py` to generate model.

**pgvector connection error:**
Check `DATABASE_URL` is set. Verify with:
```bash
psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM memories WHERE project IN ('FF','deploy','chess');"
```

**TypeScript compile error:**
```bash
npm install --save-dev @types/node @types/pg typescript
npx tsc --version  # requires >=5.0
```

---

*Built for Roger OpenClaw · March 2026 · Daniel Tekippe*
