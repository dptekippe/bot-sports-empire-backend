# Gymnasium RL Harness + pgvector Memory

Python harness that wraps [Gymnasium](https://gymnasium.farama.org/) RL environments and
integrates with the **pgvector memory hook** (`/hooks/pgvector_memory_hook.ts`).

Every environment step is stored as an RL memory (state, action, reward, next_state,
episode_id, episode_return, importance) in a PostgreSQL `rl_memories` table.
Before each step, pgvector is queried for similar past states — those insights drive:

- **Reward shaping** — bonus/penalty based on whether similar states historically led
  to high or low returns
- **Hyperparameter self-tuning** — after N episodes, the tuner queries pgvector for
  best-performing episodes and proposes/adjusts lr_rate, gamma, epsilon, epsilon_decay

---

## Files

| File | Purpose |
|------|---------|
| `pgvector_client.py` | Python client for the `rl_memories` table. Embeddings via Ollama HTTP API. |
| `rl_harness.py` | Main harness — runs episodes, stores transitions, optionally shapes rewards. |
| `reward_shaper.py` | Reward shaping logic using hybrid pgvector search. |
| `hp_tuner.py` | Self-tuning HP engine — analyses episode history → proposes param changes. |
| `example_cartpole.py` | CartPole-v1 demo (50 episodes, baseline comparison). |
| `README.md` | This file. |

---

## Architecture

```
Gymnasium Env (CartPole-v1, MountainCar, etc.)
       │
       ▼
┌──────────────────────────────────────────┐
│  RLHarness.collect_episode()             │
│  ┌────────────────────────────────────┐  │
│  │ 1. Agent policy → action           │  │
│  │ 2. env.step(action) → (s,a,r,s')   │  │
│  │ 3. pgvector.recall(s)              │  │  ◄── Ollama /api/embeddings
│  │ 4. RewardShaper.shape_reward()      │  │      (all-mpnet-base-v2, 768-dim)
│  │ 5. pgvector.store_experience()     │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
       │
       ▼  after every N episodes
┌──────────────────────┐
│  HPTuner.tune_hp()   │  ◄── pgvector best-episodes query
│  lr_rate / gamma /   │
│  epsilon / decay     │
└──────────────────────┘
       │
       ▼
PostgreSQL rl_memories (pgvector)
```

---

## Setup

### 1. Prerequisites

```bash
# PostgreSQL with pgvector extension
# https://github.com/pgvector/pgvector#installation

# Example (macOS with Homebrew):
brew install postgresql@16
brew install pgvector   # or follow pgvector docs

# Start PostgreSQL and create a database:
createdb rl_memories
```

### 2. Ollama (embedding server)

```bash
# Install Ollama: https://ollama.com/
ollama serve

# Pull the embedding model:
ollama pull all-mpnet-base-v2

# Verify:
curl -s http://localhost:11434/api/tags | jq '.models[].name'
```

### 3. Python environment

```bash
cd /path/to/gymnasium_harness
python -m venv .venv && source .venv/bin/activate
pip install gymnasium numpy psycopg2-binary requests
```

### 4. Environment variables

```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/rl_memories"
export OLLAMA_URL="http://localhost:11434"
export EMBEDDING_MODEL="all-mpnet-base-v2"
```

---

## Quick Start

```bash
python example_cartpole.py
```

Expected output (abbreviated):

```
=== Gymnasium RL Harness + pgvector Memory Demo ===
  CartPole-v1

[pgvector] connected to: postgresql://...
[Ollama] available models: ['all-mpnet-base-v2', ...]

Starting training loop...

  ep   1 | return=    45.0 | steps=  45 | eps=1.000
  ep   2 | return=    52.0 | steps=  52 | eps=0.995
  ...
  ep  10 | return=   123.0 | steps= 123 | eps=0.951  ← HP tuned
  ep  20 | return=   198.0 | steps= 198 | eps=0.904  ← HP tuned
  ...
  ep  50 | return=   487.0 | steps= 487 | eps=0.772

============================================================
  TRAINING COMPLETE
============================================================
  Episodes:            50
  Reward shaping:      True
  HP tuning:           True
  pgvector memories:   2417
  Final epsilon:       0.7724
  Final lr_rate:       0.000480
  Final gamma:         0.9900
```

---

## Schema: `rl_memories`

The table is **auto-created** by `pgvector_client.ensure_table()` on first run.

```sql
CREATE TABLE rl_memories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    state_embedded  vector(768),         -- 768-dim embedding of state
    state_text      TEXT,                 -- human-readable state
    action          TEXT,                 -- action taken
    reward          REAL,                 -- (shaped) reward received
    next_state_text TEXT,                -- next state as text
    episode_id      INTEGER,              -- episode number
    episode_return  REAL,                -- cumulative return (filled at ep end)
    importance      DOUBLE PRECISION,    -- 1-10, computed per-step
    created_at      TIMESTAMP DEFAULT NOW(),
    created_at_ts   BIGINT               -- Unix epoch, for recency scoring
);
```

Indexes: `episode_id`, `episode_return`, `importance`, `state_embedded` (IVFFlat/HNSW).

---

## Hybrid Search Scoring

Every `recall()` call scores memories by:

```
hybrid_score = 0.5 × similarity
             + 0.3 × (importance / 10.0)
             + 0.2 × recency
```

- **similarity**: `1 - cosine_distance` between state embedding and query
- **importance**: 1–10, computed from reward magnitude + pgvector signal
- **recency**: decays over 1 year (`now_ts - created_at_ts`)

---

## Key Functions

### `collect_episode(env, episode_id, hyperparams)`

Runs one full Gymnasium episode:
1. Resets env
2. Loop: policy → step → recall → shape_reward → store
3. Backfills `episode_return` on all stored steps
4. Returns `EpisodeResult` with metrics

### `shape_reward(original_reward, state, pgvector_context)`

1. Queries pgvector for top-k similar states
2. Computes avg return of similar states vs global average
3. Returns `shaped_reward = original_reward + bonus`
4. Bonus ∈ [-penalty_weight, +bonus_weight]

### `tune_hyperparams(episode_history)`

After every N episodes:
1. Computes recent avg return and coefficient of variation
2. Queries pgvector `best_episodes` for historical comparison
3. Proposes changes to lr_rate, gamma, epsilon, epsilon_decay
4. Returns a `TuningResult` with confidence and evidence

### `get_pgvector_insight(state)`

Standalone inspection: returns similar memories, avg return, top actions.

---

## Adding a Custom Policy

```python
from rl_harness import RLHarness, RLHyperparams
from pgvector_client import PgVectorClient

def my_policy(state, hyperparams):
    # state is a numpy array (Gymnasium observation)
    # hyperparams has .epsilon, .lr_rate, etc.
    if np.random.random() < hyperparams.epsilon:
        return env.action_space.sample()
    # Your RL logic here
    return best_action

client = PgVectorClient()
harness = RLHarness(client)

results = harness.run(
    env_name="MountainCar-v0",
    num_episodes=100,
    agent_policy=my_policy,
    use_reward_shaping=True,
    use_hp_tuning=True,
)
```

---

## Integrating with the Existing TypeScript Hook

The Python `PgVectorClient` writes directly to the same `rl_memories` table used by
`pgvector_memory_hook.ts`. Both can coexist — the TypeScript hook processes OpenClaw
agent events while the Python harness processes RL environment transitions.

---

## Assumptions & Notes

| Assumption | Detail |
|-----------|--------|
| Ollama must be running | Embedding calls go to `localhost:11434`. Start with `ollama serve`. |
| `all-mpnet-base-v2` model | 768-dim model. The `dimensions=768` is hardcoded. Change in `PgVectorConfig` if using a different model. |
| Episode return backfill | `episode_return` is written at episode end. Early-exit queries won't see the final return yet. |
| Reward shaping warmup | First ~3 episodes are skipped to let memories accumulate. Configurable via `RewardShaper.warmup_episodes`. |
| ε-greedy only | The demo policy uses ε-greedy. Swap in DQN, REINFORCE, etc. by replacing `agent_policy`. |
| No DQN/Q-learning learner | This harness stores memories and shapes rewards; it does **not** implement a value function learner. Use it with a separate agent library (stable-baselines3, tianshou, etc.). |

---

## Extending

- **Custom environments**: any Gymnasium env (LunarLander, Humanoid, custom)
- **Multi-agent**: prefix `episode_id` with agent ID to separate memory streams
- **Priority memories**: increase `importance` for surprising / high-reward transitions
- **Memory eviction**: add a TTL/retention policy to `pgvector_client` for long runs
