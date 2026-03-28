/**
 * pgvector Memory Hook - TypeScript for OpenClaw RL Agent
 * 
 * Vector-based memory storage and retrieval using pgvector.
 * Supports semantic search, hybrid scoring, and RL agent memory patterns.
 * 
 * Embedding: OpenAI text-embedding-3-small (1536 dimensions)
 * Database: PostgreSQL with pgvector extension
 * 
 * Trigger: Automatically processes memory-related events
 */

import pg from 'pg';
const { Pool } = pg;

// ============ CONFIGURATION ============

interface MemoryConfig {
  connectionString: string;
  embeddingModel?: string;
  dimensions?: number;
  hybridWeights?: {
    similarity: number;
    importance: number;
    recency: number;
  };
}

const DEFAULT_CONFIG: MemoryConfig = {
  connectionString: process.env.DATABASE_URL || 'postgresql://user:pass@localhost:5432/memories',
  embeddingModel: 'all-mpnet-base-v2',
  dimensions: 768,
  hybridWeights: {
    similarity: 0.5,
    importance: 0.3,
    recency: 0.2
  }
};

// ============ TYPES ============

interface Memory {
  id?: string;
  content: string;
  embedding?: number[];
  memory_type: 'fact' | 'procedure' | 'instruction' | 'experience' | 'preference' | 'general';
  tags: string[];
  importance: number; // 1-10
  project: string;
  sensitivity?: 'public' | 'internal' | 'confidential';
  created_at?: Date;
  hybrid_score?: number;
  // RL-specific fields
  state?: string;
  action?: string;
  reward?: number;
  episode?: number;
  step?: number;
}

interface MemorySearchResult extends Memory {
  similarity: number;
}

interface RLMemoryContext {
  episode: number;
  step: number;
  state: string;
  action: string;
  reward: number;
  done: boolean;
}

interface HybridScoreResult extends Memory {
  hybrid_score: number;
}

// ============ EMBEDDING SERVICE ============

class EmbeddingService {
  private model: string;
  private dimensions: number;

  constructor(model: string = 'text-embedding-3-small', dimensions: number = 1536) {
    this.model = model;
    this.dimensions = dimensions;
  }

  async embed(text: string): Promise<number[]> {
    // Use OpenAI embeddings API (text-embedding-3-small, 1536 dimensions)
    const apiKey = process.env.OPENAI_API_KEY || process.env.MINIMAX_API_KEY;
    const baseUrl = process.env.OPENAI_BASE_URL || 'https://api.openai.com/v1';
    
    // Truncate text to avoid token limits (OpenAI has 8192 token limit, ~32000 chars)
    const truncatedText = text.length > 30000 ? text.substring(0, 30000) : text;

    const response = await fetch(`${baseUrl}/embeddings`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      body: JSON.stringify({
        model: 'text-embedding-3-small',
        input: truncatedText
      })
    });

    if (!response.ok) {
      throw new Error(`Embedding failed: ${response.statusText}`);
    }

    const data = await response.json() as { data?: Array<{ embedding?: number[] }> };
    
    if (!data.data || !data.data[0]?.embedding) {
      throw new Error(`Invalid embedding response`);
    }

    // Ensure 1536 dimensions (text-embedding-3-small outputs 1536)
    const embedding = data.data[0].embedding;
    return embedding;
  }

  async embedBatch(texts: string[]): Promise<number[][]> {
    // Batch embedding for efficiency
    const embeddings: number[][] = [];
    
    for (const text of texts) {
      const embedding = await this.embed(text);
      embeddings.push(embedding);
    }

    return embeddings;
  }
}

// ============ DATABASE SERVICE ============

class MemoryDatabase {
  private pool: pg.Pool;
  private initialized: boolean = false;

  constructor(connectionString: string) {
    this.pool = new Pool({
      connectionString,
      ssl: connectionString.includes('render.com') ? { rejectUnauthorized: false } : false
    });
  }

  async initialize(): Promise<void> {
    if (this.initialized) return;

    // Enable pgvector extension
    await this.pool.query(`CREATE EXTENSION IF NOT EXISTS vector`);

    // Create memories table
    await this.pool.query(`
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
        -- RL-specific fields
        state TEXT,
        action TEXT,
        reward REAL,
        episode INTEGER,
        step INTEGER
      )
    `);

    // Create indexes
    await this.pool.query(`
      CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project)
    `);
    await this.pool.query(`
      CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)
    `);
    await this.pool.query(`
      CREATE INDEX IF NOT EXISTS idx_memories_hybrid ON memories(hybrid_score DESC)
    `);
    // Vector index (IVFFlat or HNSW for approximate search)
    await this.pool.query(`
      CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories 
      USING ivfflat (embedding vector_cosine_ops)
    `).catch(() => {
      // Fallback to HNSW if IVFFlat fails
      this.pool.query(`
        CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories 
        USING hnsw (embedding vector_cosine_ops)
      `).catch(() => console.warn('Vector index creation skipped'));
    });

    this.initialized = true;
    console.log('📚 pgvector memory table initialized');
  }

  async storeMemory(memory: Memory): Promise<Memory> {
    await this.initialize();

    const result = await this.pool.query(
      `INSERT INTO memories (content, embedding, memory_type, tags, importance, project, sensitivity, state, action, reward, episode, step)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
       RETURNING *`,
      [
        memory.content,
        memory.embedding ? `[${memory.embedding.join(',')}]` : null,
        memory.memory_type || 'general',
        memory.tags || [],
        memory.importance || 5.0,
        memory.project || 'default',
        memory.sensitivity || 'public',
        memory.state || null,
        memory.action || null,
        memory.reward ?? null,
        memory.episode ?? null,
        memory.step ?? null
      ]
    );

    return result.rows[0] as Memory;
  }

  async semanticSearch(
    query: string,
    embedding: number[],
    options: {
      limit?: number;
      project?: string;
      memoryTypes?: string[];
      minImportance?: number;
    } = {}
  ): Promise<MemorySearchResult[]> {
    await this.initialize();

    const { limit = 5, project, memoryTypes, minImportance } = options;
    const embeddingStr = `[${embedding.join(',')}]`;

    let queryStr = `
      SELECT *, 
        (embedding <=> $1::vector) as similarity
      FROM memories
      WHERE 1=1
    `;
    const params: any[] = [embeddingStr];
    let paramIndex = 2;

    if (project) {
      queryStr += ` AND project = $${paramIndex}`;
      params.push(project);
      paramIndex++;
    }

    if (memoryTypes && memoryTypes.length > 0) {
      queryStr += ` AND memory_type = ANY($${paramIndex}::text[])`;
      params.push(memoryTypes);
      paramIndex++;
    }

    if (minImportance !== undefined) {
      queryStr += ` AND importance >= $${paramIndex}`;
      params.push(minImportance);
      paramIndex++;
    }

    queryStr += ` ORDER BY embedding <=> $1::vector LIMIT $${paramIndex}`;
    params.push(limit);

    const result = await this.pool.query(queryStr, params);
    return result.rows.map(row => ({
      ...row,
      embedding: row.embedding?.toArray ? row.embedding.toArray() : row.embedding
    })) as MemorySearchResult[];
  }

  async hybridSearch(
    query: string,
    embedding: number[],
    options: {
      limit?: number;
      project?: string;
      memoryTypes?: string[];
    } = {}
  ): Promise<HybridScoreResult[]> {
    await this.initialize();

    const { limit = 5, project, memoryTypes } = options;
    const embeddingStr = `[${embedding.join(',')}]`;

    // First, ensure hybrid scores are calculated
    await this.pool.query(`
      UPDATE memories 
      SET hybrid_score = (
        0.5 * (1 - (embedding <=> $1::vector)) +  -- similarity (inverted distance)
        0.3 * (importance / 10.0) +                -- importance normalized
        0.2 * (1 - (EXTRACT(EPOCH FROM NOW()) - created_at_ts) / (365*24*3600))  -- recency
      )
      WHERE embedding IS NOT NULL
    `, [embeddingStr]);

    let queryStr = `
      SELECT * FROM memories
      WHERE embedding IS NOT NULL
    `;
    const params: any[] = [];
    let paramIndex = 1;

    if (project) {
      queryStr += ` AND project = $${paramIndex}`;
      params.push(project);
      paramIndex++;
    }

    if (memoryTypes && memoryTypes.length > 0) {
      queryStr += ` AND memory_type = ANY($${paramIndex}::text[])`;
      params.push(memoryTypes);
      paramIndex++;
    }

    queryStr += ` ORDER BY hybrid_score DESC LIMIT $${paramIndex}`;
    params.push(limit);

    const result = await this.pool.query(queryStr, params);
    return result.rows as HybridScoreResult[];
  }

  async getRecentMemories(project?: string, limit: number = 10): Promise<Memory[]> {
    await this.initialize();

    let query = 'SELECT * FROM memories ORDER BY created_at DESC LIMIT $1';
    const params: any[] = [limit];

    if (project) {
      query = 'SELECT * FROM memories WHERE project = $1 ORDER BY created_at DESC LIMIT $2';
      params.push(project, limit);
    }

    const result = await this.pool.query(query, params);
    return result.rows as Memory[];
  }

  async getMemoriesByType(type: string, limit: number = 10): Promise<Memory[]> {
    await this.initialize();

    const result = await this.pool.query(
      'SELECT * FROM memories WHERE memory_type = $1 ORDER BY created_at DESC LIMIT $2',
      [type, limit]
    );
    return result.rows as Memory[];
  }

  async getRLMemories(episode?: number, limit: number = 50): Promise<Memory[]> {
    await this.initialize();

    let query = 'SELECT * FROM memories WHERE reward IS NOT NULL';
    const params: any[] = [];

    if (episode !== undefined) {
      query += ' AND episode = $1';
      params.push(episode);
    }

    query += ' ORDER BY episode DESC, step ASC LIMIT $' + (params.length + 1);
    params.push(limit);

    const result = await this.pool.query(query, params);
    return result.rows as Memory[];
  }

  async deleteMemory(id: string): Promise<boolean> {
    await this.initialize();

    const result = await this.pool.query('DELETE FROM memories WHERE id = $1', [id]);
    return (result.rowCount ?? 0) > 0;
  }

  async updateImportance(id: string, importance: number): Promise<Memory> {
    await this.initialize();

    const result = await this.pool.query(
      'UPDATE memories SET importance = $1 WHERE id = $2 RETURNING *',
      [importance, id]
    );
    return result.rows[0] as Memory;
  }

  async getStats(): Promise<{
    total: number;
    byType: Record<string, number>;
    byProject: Record<string, number>;
    avgImportance: number;
  }> {
    await this.initialize();

    const totalResult = await this.pool.query('SELECT COUNT(*) as count FROM memories');
    const typeResult = await this.pool.query(
      'SELECT memory_type, COUNT(*) as count FROM memories GROUP BY memory_type'
    );
    const projectResult = await this.pool.query(
      'SELECT project, COUNT(*) as count FROM memories GROUP BY project'
    );
    const importanceResult = await this.pool.query(
      'SELECT AVG(importance) as avg FROM memories'
    );

    return {
      total: parseInt(totalResult.rows[0].count),
      byType: Object.fromEntries(typeResult.rows.map(r => [r.memory_type, parseInt(r.count)])),
      byProject: Object.fromEntries(projectResult.rows.map(r => [r.project, parseInt(r.count)])),
      avgImportance: parseFloat(importanceResult.rows[0].avg) || 0
    };
  }

  async close(): Promise<void> {
    await this.pool.end();
  }
}

// ============ MAIN HOOK HANDLER ============

let db: MemoryDatabase | null = null;
let embedder: EmbeddingService | null = null;

function getServices(config?: Partial<MemoryConfig>): {
  db: MemoryDatabase;
  embedder: EmbeddingService;
} {
  if (!db) {
    const cfg = { ...DEFAULT_CONFIG, ...config };
    db = new MemoryDatabase(cfg.connectionString);
    embedder = new EmbeddingService(cfg.embeddingModel, cfg.dimensions);
  }
  return { db, embedder: embedder! };
}

export default async function handler(event: any): Promise<any> {
  const validEvents = [
    'memory:store',
    'memory:search',
    'memory:hybrid',
    'memory:recent',
    'memory:rl',
    'memory:stats',
    'memory:delete',
    'memory:update',
    // RL agent events
    'rl:experience',
    'rl:remember',
    'rl:recall'
  ];

  // Process all events for memory hooks
  if (!event.type || !validEvents.includes(event.type)) {
    return event;
  }

  console.log('📚 pgvector-memory:', event.type);

  const config = event.memoryConfig ? {
    connectionString: event.memoryConfig.connectionString || DEFAULT_CONFIG.connectionString,
    embeddingModel: event.memoryConfig.embeddingModel,
    dimensions: event.memoryConfig.dimensions
  } : undefined;

  const { db: memoryDb, embedder: embeddingService } = getServices(config);

  try {
    switch (event.type) {
      // ========== STORE MEMORY ==========
      case 'memory:store': {
        const memory = event.memory as Memory;
        
        // Generate embedding if not provided
        if (!memory.embedding && memory.content) {
          memory.embedding = await embeddingService.embed(memory.content);
        }

        const stored = await memoryDb.storeMemory(memory);
        
        event.result = {
          success: true,
          memory: stored,
          message: 'Memory stored successfully'
        };
        break;
      }

      // ========== SEMANTIC SEARCH ==========
      case 'memory:search': {
        const { query, limit, project, memoryTypes, minImportance } = event;
        
        // Generate query embedding
        const embedding = await embeddingService.embed(query);
        
        const results = await memoryDb.semanticSearch(query, embedding, {
          limit: limit || 5,
          project,
          memoryTypes,
          minImportance
        });

        event.result = {
          success: true,
          results,
          count: results.length
        };
        break;
      }

      // ========== HYBRID SEARCH ==========
      case 'memory:hybrid': {
        const { query, limit, project, memoryTypes } = event;
        
        const embedding = await embeddingService.embed(query);
        
        const results = await memoryDb.hybridSearch(query, embedding, {
          limit: limit || 5,
          project,
          memoryTypes
        });

        event.result = {
          success: true,
          results,
          count: results.length,
          type: 'hybrid'
        };
        break;
      }

      // ========== RECENT MEMORIES ==========
      case 'memory:recent': {
        const { project, limit } = event;
        
        const memories = await memoryDb.getRecentMemories(project, limit || 10);
        
        event.result = {
          success: true,
          memories,
          count: memories.length
        };
        break;
      }

      // ========== RL MEMORIES ==========
      case 'memory:rl':
      case 'rl:experience': {
        const { episode, limit } = event;
        
        const memories = await memoryDb.getRLMemories(episode, limit || 50);
        
        event.result = {
          success: true,
          memories,
          count: memories.length,
          type: 'rl_experience'
        };
        break;
      }

      // ========== RL REMEMBER (Store experience) ==========
      case 'rl:remember': {
        const context = event.context as RLMemoryContext;
        
        const memory: Memory = {
          content: `State: ${context.state} → Action: ${context.action} → Reward: ${context.reward}`,
          memory_type: 'experience',
          tags: ['rl', 'experience', `episode-${context.episode}`],
          importance: context.done ? 8 : 5,
          project: event.project || 'rl_agent',
          state: context.state,
          action: context.action,
          reward: context.reward,
          episode: context.episode,
          step: context.step
        };

        // Generate embedding
        memory.embedding = await embeddingService.embed(memory.content);
        
        const stored = await memoryDb.storeMemory(memory);
        
        event.result = {
          success: true,
          memory: stored,
          message: 'RL experience stored'
        };
        break;
      }

      // ========== RL RECALL (Get relevant memories) ==========
      case 'rl:recall': {
        const { currentState, episode } = event;
        
        // Get memories from same episode or similar states
        const memories = await memoryDb.getRLMemories(episode, 20);
        
        event.result = {
          success: true,
          memories,
          count: memories.length
        };
        break;
      }

      // ========== MEMORY STATS ==========
      case 'memory:stats': {
        const stats = await memoryDb.getStats();
        
        event.result = {
          success: true,
          stats
        };
        break;
      }

      // ========== DELETE MEMORY ==========
      case 'memory:delete': {
        const { id } = event;
        
        const deleted = await memoryDb.deleteMemory(id);
        
        event.result = {
          success: deleted,
          message: deleted ? 'Memory deleted' : 'Memory not found'
        };
        break;
      }

      // ========== UPDATE IMPORTANCE ==========
      case 'memory:update': {
        const { id, importance } = event;
        
        const updated = await memoryDb.updateImportance(id, importance);
        
        event.result = {
          success: true,
          memory: updated
        };
        break;
      }

      default:
        return event;
    }

    console.log('📚 pgvector-memory: completed', event.type);
  } catch (error) {
    console.error('📚 pgvector-memory error:', error);
    event.result = {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }

  return event;
}

// ============ EXPORTS FOR DIRECT USE ============

export { Memory, MemorySearchResult, RLMemoryContext, MemoryConfig, MemoryDatabase, EmbeddingService };
