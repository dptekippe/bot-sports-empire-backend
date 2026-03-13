# Draft RL Environment - Perplexity Recommendation

Date: March 13, 2026

## 0. Decide What You're Optimizing

Pick one clean reward target first (don't mix too many):

**Option A:** Season-long fantasy points in 2025 scored by the drafted roster

**Option B:** Points above an ADP baseline or above a simple heuristic bot

Define as a function:
```
reward(draft_trajectory) -> float
```

Input: full draft for one team (all picks, roster) plus simulated season outcome
Output: a single scalar (e.g., team_fantasy_points – baseline_points)

---

## 1. Turn Your Draft Sim Into an Environment

You already have:
- A 12-team, 20-round superflex TEP snake draft sim with realistic ADP-based picks

Wrap as an environment object:

```python
class DraftEnv:
    def reset(self, agent_slot, season_year) -> state:
        # build league, ADP, schedule; assign Roger's team position
        # return initial state for Roger
    
    def step(self, action) -> (state, reward, done, info):
        # apply Roger's pick, let bots pick, advance draft
```

### Key Design Choices:

**State representation:**
- Current round, pick number, your team slot
- Your roster counts by position and projected points
- Available player pool (top N players + features like ADP, position, projected points)

**Action space:**
- Pick a player from the remaining pool
- Index into top K available (e.g., top 50 by ADP)

**Episode:**
- One full draft (20 rounds) for one team
- Reward given at end after simulating season

---

## 2. Define the Reward Function Precisely

Start with simple, end-of-episode reward:

1. Run DynastyDroid season sim on drafted rosters
2. Compute:
   - `team_points` = sum(points for players in starting lineup each week)
   - `baseline_points` = mean of all 12 teams, or points of "pure ADP" bot
3. Reward: `reward = team_points - baseline_points`

**Later enhancements:**
- Interim reward for building legal, complete roster (no holes by round 12)
- Penalty for drafting players who never crack starting lineup (dead bench)

---

## 3. Connect Roger to the Environment

Roger is the policy, env is the world.

### 3.1. State → Prompt Adapter

Prompt format:
```
Top N available players with ADP, position, projections.
Your current roster, positional needs, league settings.
Return ONLY the player_id you choose from this list.
```

### 3.2. Logging Trajectories

For each simulated draft episode, log:
- `states`: serialized representation (JSON with player features, roster)
- `actions`: which player he picked (index or ID)
- `final_reward`: scalar reward from season sim
- Optional: per-pick auxiliary rewards

Store as JSONL for RL training.

---

## 4. Choose RL Training Style

### Path A: "RL over a small policy head" (PPO / REINFORCE)
- Treat Roger as mostly fixed
- Learn lightweight network that biases his choices
- Build small network: state → distribution over candidate players
- Use PPO or REINFORCE on logged trajectories
- Easier than fine-tuning full LLM

### Path B: RLHF / RLVR loop around Roger
- Use environment + deterministic reward as verifier
- Generate multiple draft trajectories with Roger
- Score with reward function
- Use for RLHF / RLVR fine-tuning

---

## Implementation Status (Mar 13, 2026)

- [x] DraftEnv class created
- [x] 8 bot strategies implemented
- [x] ADP-based player pool
- [x] Reward calculation
- [ ] Roger integration (mock LLM)
- [ ] Real MiniMax integration
- [ ] Trajectory logging
