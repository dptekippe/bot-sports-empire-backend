# RCT2 Reinforcement Learning Project - Comprehensive Memory

**Date:** April 2, 2026
**Project:** OpenRCT2 RL Training
**Location:** `/Volumes/ExternalCorsairSSD/rct2_rl/`

---

## Project Overview

Goal: Train an RL agent (PPO) to play OpenRCT2 (Roller Coaster Tycoon 2) autonomously. The agent learns to build and manage a theme park to maximize profit and guest satisfaction.

**Key Files:**
```
/Volumes/ExternalCorsairSSD/rct2_rl/
├── openrct2_env.py          # Gymnasium environment wrapper
├── rct2_api.py              # TCP API client for OpenRCT2
├── log_tail_observer.py     # Log observer for park state
├── rewards.py               # Reward function (legacy)
├── baseline_agent.py        # Random agent for testing
├── episode_runner.py        # Episode runner
├── checkpoint_train.py      # Checkpoint-based PPO training
├── train_with_kl.py         # PPO with KL penalty (for stability)
├── grid_search.py           # Hyperparameter search
├── evaluate.py              # Evaluation script
├── ppo_trained.zip          # Best trained model (ent_coef=0.05)
├── checkpoints/             # Checkpoint directory
│   ├── ppo_checkpoint_13700steps.zip  # Latest checkpoint
│   └── ppo_checkpointed.zip           # Final model from checkpointed run
└── scenarios/
    └── Sweltering Heights.sc6  # Scenario file being used
```

---

## How to Restart Everything

### 1. OpenRCT2 Headless

**If OpenRCT2 crashes or needs restart:**

```bash
# Kill any existing processes
pkill -f OpenRCT2 || true

# Start OpenRCT2 headless with caffeinate (prevents sleep)
cd /Applications/OpenRCT2.app/Contents/MacOS
caffeinate ./OpenRCT2 host \
  /Users/danieltekippe/Downloads/OpenRCT2-Custom-Scenarios-main/Fred-104\'s\ Scenarios/Sweltering\ Trilogy/Sweltering\ Heights.sc6 \
  --headless --port 8080
```

**Ports:**
- Ride API: 8080
- State API: 8081

**Verify it's running:**
```bash
curl http://localhost:8080/api/rides  # Should list rides
curl http://localhost:8081/api/state   # Should return park state
```

### 2. RL Environment

**Activate virtual environment:**
```bash
cd /Volumes/ExternalCorsairSSD/rct2_rl
source .venv/bin/activate
```

**Test environment:**
```bash
python3 -c "
from openrct2_env import make_env
env = make_env(host='localhost', port=8080, max_steps=50, settle_seconds=0.05)
obs, info = env.reset()
print('Env working! Guests:', info.get('raw_state', {}).get('parkGuests', 0))
env.close()
"
```

---

## Current State (April 2, 2026)

### Training Status
- **Latest checkpoint:** 13,700 steps
- **Best model:** `ppo_checkpointed.zip` (from checkpointed run)
- **Alternative model:** `ppo_trained.zip` (ent_coef=0.05 discovery)

### Performance
- **Best evaluation:** ~175 mean reward (ent_coef=0.05, single run)
- **Current training:** Ongoing with checkpoint-based approach
- **Episode length:** ~10-20 steps (varies due to early termination)
- **Reward:** Still negative (around -2 to -5) - agent struggling with profitability

### Known Issues
1. **Reward Degeneracy:** Agent tends to spam single actions (shops OR rides) instead of diversifying
2. **Early Termination:** Episodes end early when park enters failure state
3. **Value Function:** explained_variance oscillates, sometimes goes negative

---

## Key Discoveries

### 1. ent_coef = 0.05 (BEST)
Grid search found ent_coef=0.05 performs significantly better:
- ent_coef=0.01: ~105 mean reward (baseline)
- ent_coef=0.03: ~101 mean reward
- **ent_coef=0.05: ~175 mean reward** (+66% improvement!)
- ent_coef=0.08: ~103 mean reward

The entropy coefficient controls exploration. 0.05 found a better exploration/exploitation balance.

### 2. settle_seconds = 0.05
Critical for SIGTERM workaround:
- 2.0 seconds: Too slow for training (100 steps = ~200 seconds)
- 0.05 seconds: Fast enough for training under ~5 min timeout
- Used in: `make_env(settle_seconds=0.05)`

### 3. Checkpoint-Based Training
SIGTERM kills training after ~5-14 minutes. Solution:
- Train 500 steps, save checkpoint
- Spawn new session, resume from checkpoint
- Pattern: `checkpoint_train.py --steps 500 --checkpoint-every 100 --name ppo_checkpointed`

### 4. The 1000-Ride Problem
The scenario file (Sweltering Heights) starts with ~1000 pre-built rides. This causes:
- Episodes ending after 1 step (mature park)
- Dense initial state (not blank slate)
- Agent needs to manage existing rides, not build from scratch

---

## Reward Function (Current)

The environment uses a dense reward system:

```python
# From openrct2_env.py (Daniels B+C modifications)
Reward = (
    2.0 * guest_delta_norm       # Per guest change
    + 1.5 * rating_delta_norm    # Per park rating point
    + 1.0 * profit_delta_norm    # Per dollar monthly profit
    + 0.25 * cash_delta_norm     # Per dollar cash change
    + 25.0 * new_awards          # Per award received
    + 75.0 * research_complete   # Research completed
    - 2.0 * invalid_action       # Invalid action penalty
    - 1.0 * destructive          # Delete penalty
    - 0.5 * idle_penalty         # Consecutive noop penalty
)
```

**Problem:** Agent finds exploits (spam one action type). The diversity penalty was added but didn't fully solve it.

---

## Action Space

4 discrete actions:
| ID | Action | Description |
|----|--------|-------------|
| 0 | noop | Do nothing |
| 1 | build_wooden_coaster | Build wooden coaster near center |
| 2 | build_food_stall | Build food stall |
| 3 | delete_worst_ride | Delete lowest-performing ride |

---

## Observation Space

24-dimensional float vector:
```
Index  Feature
0-7    Park metrics (rating, guests, cash, loan, profit, awards, research, ride count)
8-13   Ride type counts (coasters, stalls, broken, etc.)
14-23  Context (step fraction, last action, last reward, deltas, flags)
```

---

## Next Steps (If Continuing)

1. **Verify OpenRCT2 running** - Check port 8080
2. **Resume training** from checkpoint:
   ```bash
   cd /Volumes/ExternalCorsairSSD/rct2_rl
   source .venv/bin/activate
   python3 checkpoint_train.py --steps 500 --checkpoint-every 100 --name ppo_checkpointed
   ```
3. **Evaluate current model:**
   ```bash
   python3 evaluate.py --model checkpoints/ppo_checkpointed.zip --episodes 10
   ```

### Potential Improvements (If Pursuing)
1. **Sparse rewards** - Milestone-based instead of dense (fixes degeneracy)
2. **LSTM policy** - For temporal dependencies
3. **Different scenario** - Blank park instead of mature 1000-ride park
4. **Curiosity-driven exploration** - Intrinsic motivation to explore
5. **Curriculum learning** - Start simple, increase complexity

---

## What We Learned

1. **PPO works for RCT2** - Training converges, agent learns
2. **Reward shaping is hard** - Agent finds exploits, fix one degeneracy, find another
3. **Checkpoint pattern essential** - SIGTERM kills long training
4. **Exploration matters** - ent_coef=0.05 significantly outperformed baseline
5. **Environment matters** - Mature park vs blank slate changes everything

---

## Contact / Context

- **Human:** Daniel (dan099381)
- **Project started:** March 31, 2026
- **Last active:** April 2, 2026
- **OpenRCT2 extraction:** Used `innoextract --gog` from GOG installer

*This memory should allow continuity even if Roger's session memory is wiped.*
