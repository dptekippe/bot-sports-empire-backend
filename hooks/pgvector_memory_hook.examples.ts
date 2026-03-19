/**
 * pgvector Memory Hook - Usage Examples
 * 
 * How to use the pgvector memory hook with OpenClaw events.
 */

// ============ EXAMPLE 1: Store a Memory ============
/*
// Event:
{
  type: 'memory:store',
  memory: {
    content: 'Roger prefers MiniMax for reasoning tasks',
    memory_type: 'preference',
    tags: ['roger', 'model-preference'],
    importance: 8,
    project: 'Roger-core'
  }
}

// Result:
{
  success: true,
  memory: {
    id: 'uuid...',
    content: 'Roger prefers MiniMax for reasoning tasks',
    embedding: [...768 dims...],
    memory_type: 'preference',
    importance: 8,
    ...
  }
}
*/

// ============ EXAMPLE 2: Semantic Search ============
/*
// Event:
{
  type: 'memory:search',
  query: 'What model does Roger use?',
  project: 'Roger-core',
  limit: 5
}

// Result:
{
  success: true,
  results: [
    {
      content: 'Roger prefers MiniMax for reasoning tasks',
      similarity: 0.92,
      importance: 8,
      ...
    }
  ],
  count: 1
}
*/

// ============ EXAMPLE 3: Hybrid Search ============
/*
// Event:
{
  type: 'memory:hybrid',
  query: 'How do I deploy to Render?',
  project: 'default',
  limit: 3
}

// Result includes hybrid_score combining similarity + importance + recency
*/

// ============ EXAMPLE 4: Store RL Experience ============
/*
// Event:
{
  type: 'rl:remember',
  project: 'dynastydroid',
  context: {
    episode: 42,
    step: 15,
    state: '{"position": "QB1", "draft_pick": 1.12}',
    action: "draft_jahmarr_george",
    reward: 0.85,
    done: false
  }
}
*/

// ============ EXAMPLE 5: Recall RL Memories ============
/*
// Event:
{
  type: 'rl:recall',
  episode: 42,
  currentState: '{"position": "RB1", "draft_pick": 2.01}'
}

// Returns memories from episode 42
*/

// ============ EXAMPLE 6: Recent Memories ============
/*
// Event:
{
  type: 'memory:recent',
  project: 'Roger-core',
  limit: 10
}
*/

// ============ EXAMPLE 7: Memory Stats ============
/*
// Event:
{
  type: 'memory:stats'
}

// Result:
{
  success: true,
  stats: {
    total: 156,
    byType: { fact: 45, procedure: 23, experience: 88 },
    byProject: { 'Roger-core': 34, 'default': 122 },
    avgImportance: 5.8
  }
}
*/

// ============ RENDER.COM DEPLOYMENT SETUP ============
/*
-- Run this on your Render PostgreSQL console:

-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Table is created automatically by the hook on first run
-- Or create manually:

CREATE TABLE IF NOT EXISTS memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content TEXT NOT NULL,
  embedding vector(768),
  memory_type TEXT DEFAULT 'general',
  tags TEXT[] DEFAULT '{}',
  importance DOUBLE PRECISION DEFAULT 5.0,
  project TEXT DEFAULT 'default',
  sensitivity TEXT DEFAULT 'public',
  created_at TIMESTAMP DEFAULT NOW(),
  created_at_ts BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT,
  hybrid_score REAL,
  state TEXT,
  action TEXT,
  reward REAL,
  episode INTEGER,
  step INTEGER
);

-- Indexes
CREATE INDEX idx_memories_project ON memories(project);
CREATE INDEX idx_memories_type ON memories(memory_type);
CREATE INDEX idx_memories_hybrid ON memories(hybrid_score DESC);
CREATE INDEX idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops);
*/

// ============ ENVIRONMENT VARIABLES ============
/*
# .env
DATABASE_URL=postgresql://user:pass@host:5432/dbname
EMBEDDING_API_URL=http://localhost:11434  # Ollama for embeddings
*/

// ============ OPENCLAW CONFIGURATION ============
/*
// Add to your OpenClaw config:
{
  "hooks": [
    {
      "name": "pgvector-memory",
      "path": "./hooks/pgvector_memory_hook.ts",
      "trigger": "all"  // Processes all events, filters internally
    }
  ]
}
*/
