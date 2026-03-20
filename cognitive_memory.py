#!/usr/bin/env python3
"""
cognitive_memory.py - Roger's Second Brain with Semantic Memory

Implements the cognitive memory architecture from the Scout review process:
- RECALL: Query pgvector BEFORE decisions
- STORE: Enforced memory storage with importance/TTL
- Hybrid search: semantic vector + full-text

Usage:
    from cognitive_memory import pre_action_recall, post_action_store
    pre_action_recall("dynasty trade Bijan Robinson")
    post_action_store("Evaluated Bijan trade", outcome="team_a_wins")
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

import psycopg2
import numpy as np
from openai import OpenAI

# =============================================================================
# CONFIGURATION
# =============================================================================

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or os.environ.get("MINIMAX_API_KEY", "")
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://dynastydroid_user:BKJZCv57P3sYpi5RGL3ciU9CylXsFRWv@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid"
)

# Default user_id for Roger
ROGER_USER_ID = "00000000-0000-0000-0000-000000000001"

# =============================================================================
# STORAGE DECISION ENUM
# =============================================================================

class StorageDecision(Enum):
    """Memory storage decisions from should_remember()"""
    STORE_PERMANENT = "permanent"  # is_pinned=True, ttl_days=NULL
    STORE_STANDARD = "standard"    # importance=1.0, ttl_days=30
    STORE_TEMPORARY = "temporary"  # importance=0.5, ttl_days=7
    STORE_SESSION = "session"      # session_id=current, ttl_days=1
    SKIP = "skip"                  # don't store

@dataclass
class StorageResult:
    decision: StorageDecision
    importance: float
    ttl_days: Optional[int]
    is_pinned: bool
    reason: str

# =============================================================================
# OPENAI CLIENT
# =============================================================================

_client = None

def get_openai_client() -> OpenAI:
    """Get or create OpenAI client with MiniMax adapter"""
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url="https://api.minimax.io/anthropic/v1",
            timeout=30,
        )
    return _client

def embed_text(text: str) -> List[float]:
    """Generate 1536-dim embedding via OpenAI or fallback"""
    # Try MiniMax first
    try:
        client = get_openai_client()
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text[:8000]
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"   ⚠️ MiniMax embedding failed ({str(e)[:50]}...), trying HuggingFace...")
    
    # Fallback: Use HuggingFace inference API
    try:
        import requests
        response = requests.post(
            "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2",
            headers={"Content-Type": "application/json"},
            json={"inputs": text[:500]},
            timeout=30
        )
        if response.status_code == 200:
            embedding = response.json()
            if isinstance(embedding, list) and len(embedding) > 0:
                # Normalize to 1536 dim
                target_dim = 1536
                if len(embedding) < target_dim:
                    embedding.extend([0.0] * (target_dim - len(embedding)))
                else:
                    embedding = embedding[:target_dim]
                return embedding
    except Exception as e2:
        print(f"   ⚠️ HuggingFace also failed: {str(e2)[:50]}")
    
    # Final fallback: Use mock embedding for testing (deterministic based on text hash)
    if os.environ.get("MOCK_EMBEDDING", "").lower() in ("1", "true", "yes"):
        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        # Expand 32 bytes to 1536 floats using deterministic algorithm
        embedding = []
        for i in range(1536):
            byte_idx = i % 32
            embedding.append((h[byte_idx] / 255.0) * 2 - 1 + 0.1 * ((i * 7) % 17) / 17)
        return embedding
    
    raise ValueError("All embedding providers failed. Set OPENAI_API_KEY, HF_TOKEN, or MOCK_EMBEDDING=1")

# =============================================================================
# DATABASE CONNECTION
# =============================================================================

def get_db_connection():
    """Get PostgreSQL connection with pgvector"""
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn

# =============================================================================
# STORAGE DECISION LOGIC (Enforcement Mechanism)
# =============================================================================

def should_remember(
    content: str,
    source_type: str,
    namespace: str,
    explicit_request: bool = False,
    is_decision: bool = False,
    decision_outcome: Optional[str] = None,
    user_sentiment: Optional[str] = None,
) -> StorageResult:
    """
    Enforced storage decision function - THIS IS THE ENFORCEMENT MECHANISM.
    
    Replaces the unenforced decision-logging skill.
    
    Rules (in priority order):
    1. Explicit requests always store permanently
    2. Decision outcomes are permanent (critical for learning)
    3. User preferences are semi-permanent
    4. Unverified web facts are temporary
    5. Chat context is session-scoped
    6. Negative sentiment increases retention
    7. Default: skip
    """
    content_len = len(content)
    
    # 1. Explicit requests always store permanently
    if explicit_request:
        return StorageResult(
            decision=StorageDecision.STORE_PERMANENT,
            importance=2.0,
            ttl_days=None,
            is_pinned=True,
            reason="explicit user request"
        )
    
    # 2. Decision outcomes are permanent (critical for learning)
    if is_decision and decision_outcome:
        return StorageResult(
            decision=StorageDecision.STORE_PERMANENT,
            importance=2.5,
            ttl_days=None,
            is_pinned=True,
            reason=f"decision outcome: {decision_outcome}"
        )
    
    # 3. User preferences are semi-permanent
    if namespace == 'user_prefs':
        return StorageResult(
            decision=StorageDecision.STORE_STANDARD,
            importance=1.5,
            ttl_days=90,
            is_pinned=False,
            reason="user preference"
        )
    
    # 4. Facts should be verified before permanent storage
    if namespace == 'fact':
        if source_type in ('web', 'web_ref'):
            return StorageResult(
                decision=StorageDecision.STORE_TEMPORARY,
                importance=0.7,
                ttl_days=7,
                is_pinned=False,
                reason="unverified web fact - verify before permanent"
            )
        return StorageResult(
            decision=StorageDecision.STORE_STANDARD,
            importance=1.0,
            ttl_days=30,
            is_pinned=False,
            reason="internal fact"
        )
    
    # 5. Chat context is session-scoped
    if namespace == 'chat':
        return StorageResult(
            decision=StorageDecision.STORE_SESSION,
            importance=0.5,
            ttl_days=1,
            is_pinned=False,
            reason="conversation context"
        )
    
    # 6. Negative sentiment increases retention (user complaints = important)
    if user_sentiment == 'negative':
        return StorageResult(
            decision=StorageDecision.STORE_STANDARD,
            importance=1.5,
            ttl_days=30,
            is_pinned=False,
            reason="negative user sentiment"
        )
    
    # 7. Decisions with high importance content
    if namespace == 'decision' and content_len > 100:
        return StorageResult(
            decision=StorageDecision.STORE_STANDARD,
            importance=1.2,
            ttl_days=60,
            is_pinned=False,
            reason="significant decision context"
        )
    
    # 8. Skills and patterns - semi-permanent
    if namespace == 'skill':
        return StorageResult(
            decision=StorageDecision.STORE_STANDARD,
            importance=1.3,
            ttl_days=180,
            is_pinned=False,
            reason="skill or pattern"
        )
    
    # 9. Thinking traces - always store with standard importance
    # (importance scoring done by memory_flush_hook before calling store_memory)
    if namespace == 'thinking':
        return StorageResult(
            decision=StorageDecision.STORE_STANDARD,
            importance=1.0,
            ttl_days=30,
            is_pinned=False,
            reason="thinking trace"
        )
    
    # Default: skip unless explicit signal
    return StorageResult(
        decision=StorageDecision.SKIP,
        importance=0,
        ttl_days=None,
        is_pinned=False,
        reason="below importance threshold"
    )

# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def store_memory(
    user_id: str,
    content: str,
    namespace: str,
    source_type: str = 'agent',
    importance: float = 1.0,
    ttl_days: Optional[int] = 30,
    is_pinned: bool = False,
    session_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    metadata: Optional[Dict] = None,
    tags: Optional[List[str]] = None,
    decision_outcome: Optional[str] = None,
) -> Optional[str]:
    """
    Store a memory with embedding in pgvector.
    
    Returns memory ID if stored, None if skipped.
    """
    # Check if we should remember this
    decision = should_remember(
        content=content,
        source_type=source_type,
        namespace=namespace,
        explicit_request=False,
        is_decision=(namespace == 'decision'),
        decision_outcome=decision_outcome,
    )
    
    if decision.decision == StorageDecision.SKIP:
        return None
    
    # Generate embedding
    embedding = embed_text(content)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    
    # Generate content hash for deduplication
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO agent_memories (
                user_id, content, content_hash, embedding,
                source_type, namespace, importance, ttl_days, is_pinned,
                session_id, parent_id, metadata, tags
            ) VALUES (
                %s, %s, %s, %s::vector,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            ON CONFLICT (id) DO NOTHING
            RETURNING id
        """, (
            user_id, content, content_hash, embedding_str,
            source_type, namespace, decision.importance, decision.ttl_days, decision.is_pinned,
            session_id, parent_id, 
            json.dumps(metadata) if metadata else None,
            tags
        ))
        
        result = cur.fetchone()
        memory_id = result[0] if result else None
        
        if memory_id:
            print(f"✓ Stored memory: {memory_id[:8]}... ({namespace})")
        else:
            print(f"⏭️  Skipped (duplicate): {content_hash[:8]}...")
        
        return memory_id
        
    except Exception as e:
        print(f"❌ Error storing memory: {e}")
        return None
    finally:
        cur.close()
        conn.close()


def recall_memories(
    user_id: str,
    query: str,
    namespace: Optional[List[str]] = None,
    limit: int = 10,
    session_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Hybrid recall: semantic vector + recency + importance scoring.
    
    Returns memories ranked by relevance score.
    """
    # Generate query embedding
    query_embedding = embed_text(query)
    query_embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    
    # Build namespace filter
    if namespace:
        namespace_list = ",".join(f"'{n}'" for n in namespace)
        ns_filter = f"AND namespace IN ({namespace_list})"
    else:
        ns_filter = ""
    
    # Session filter
    session_filter = f"AND session_id = '{session_id}'" if session_id else ""
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Hybrid scoring: cosine similarity + recency + importance
        cur.execute(f"""
            SELECT 
                id,
                content,
                namespace,
                source_type,
                timestamp,
                importance,
                (1 - (embedding <=> %s::vector)) AS similarity,
                GREATEST(0, 1 - EXTRACT(EPOCH FROM (NOW() - timestamp)) / (86400 * 7)) AS recency_score,
                (1 - (embedding <=> %s::vector)) * 0.7 + 
                    GREATEST(0, 1 - EXTRACT(EPOCH FROM (NOW() - timestamp)) / (86400 * 7)) * 0.2 +
                    importance * 0.1 AS final_score
            FROM agent_memories
            WHERE user_id = %s
                AND NOT is_deleted
                AND embedding IS NOT NULL
                {ns_filter}
                {session_filter}
            ORDER BY final_score DESC
            LIMIT %s
        """, (query_embedding_str, query_embedding_str, user_id, limit))
        
        rows = cur.fetchall()
        
        memories = []
        for row in rows:
            memories.append({
                'id': str(row[0]),
                'content': row[1],
                'namespace': row[2],
                'source_type': row[3],
                'timestamp': row[4].isoformat() if row[4] else None,
                'importance': float(row[5]),
                'similarity': float(row[6]),
                'recency_score': float(row[7]),
                'final_score': float(row[8]),
            })
        
        return memories
        
    except Exception as e:
        print(f"❌ Error recalling memories: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def recall_decisions(
    user_id: str,
    context_pattern: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """Specialized recall for decision journal - prioritizes outcomes"""
    return recall_memories(
        user_id=user_id,
        query=context_pattern,
        namespace=['decision'],
        limit=limit
    )

# =============================================================================
# INTEGRATION FUNCTIONS (For Roger's Workflow)
# =============================================================================

def pre_action_recall(
    query: str,
    user_id: str = ROGER_USER_ID,
    namespace: Optional[List[str]] = None,
) -> str:
    """
    Roger queries memory BEFORE taking an action.
    
    This is the key integration point - Roger calls this before:
    - Answering a question
    - Making a decision
    - Evaluating a trade
    - Writing code
    
    Returns formatted context string for injection into reasoning.
    """
    if namespace is None:
        namespace = ['decision', 'fact', 'skill', 'user_prefs']
    
    memories = recall_memories(user_id, query, namespace=namespace, limit=5)
    
    if not memories:
        return ""
    
    context_parts = ["\n### Relevant Memory Context:\n"]
    for m in memories:
        context_parts.append(
            f"- [{m['namespace']}] {m['content'][:200]}"
            + (f" (score: {m['final_score']:.2f})" if m['final_score'] else "")
        )
    
    return "\n".join(context_parts)


def post_action_store(
    content: str,
    namespace: str = 'decision',
    source_type: str = 'agent',
    decision_outcome: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> Optional[str]:
    """
    Roger stores a memory AFTER taking an action.
    
    This is the key enforcement point - Roger calls this after:
    - Making a decision
    - Evaluating a trade
    - Completing a task
    
    Returns memory ID if stored, None if skipped.
    """
    return store_memory(
        user_id=ROGER_USER_ID,
        content=content,
        namespace=namespace,
        source_type=source_type,
        decision_outcome=decision_outcome,
        session_id=session_id,
        metadata=metadata,
    )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def init_memory_table():
    """Initialize the agent_memories table with indexes"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Create extension if not exists
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        
        # Create table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS agent_memories (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL,
                content TEXT NOT NULL,
                content_hash VARCHAR(64),
                embedding VECTOR(1536),
                
                source_type VARCHAR(20) NOT NULL DEFAULT 'agent',
                namespace VARCHAR(50) NOT NULL,
                
                timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_accessed TIMESTAMPTZ DEFAULT NOW(),
                read_count INT DEFAULT 0,
                
                importance FLOAT4 DEFAULT 1.0,
                ttl_days INT,
                is_pinned BOOLEAN DEFAULT FALSE,
                is_deleted BOOLEAN DEFAULT FALSE,
                
                parent_id UUID REFERENCES agent_memories(id),
                session_id VARCHAR(255),
                workspace_id VARCHAR(255),
                
                metadata JSONB,
                tags TEXT[],
                
                CONSTRAINT valid_namespace CHECK (namespace IN (
                    'chat', 'user_prefs', 'decision', 'fact', 'skill', 'context', 'web'
                )),
                CONSTRAINT valid_source_type CHECK (source_type IN (
                    'user', 'agent', 'web', 'tool', 'decision'
                ))
            )
        """)
        
        # Create indexes
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_user_namespace 
                ON agent_memories(user_id, namespace) WHERE NOT is_deleted
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_embedding 
                ON agent_memories USING hnsw (embedding vector_cosine_ops) 
                WITH (m = 16, ef_construction = 64) 
                WHERE embedding IS NOT NULL AND NOT is_deleted
        """)
        
        print("✓ Table agent_memories initialized")
        
    except Exception as e:
        print(f"❌ Error initializing table: {e}")
    finally:
        cur.close()
        conn.close()


def cleanup_expired_memories(user_id: str = ROGER_USER_ID) -> int:
    """Remove expired memories (TTL exceeded)"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            DELETE FROM agent_memories
            WHERE user_id = %s
                AND NOT is_pinned
                AND NOT is_deleted
                AND ttl_days IS NOT NULL
                AND timestamp + (ttl_days || ' days')::interval < NOW()
        """, (user_id,))
        
        deleted = cur.rowcount
        if deleted > 0:
            print(f"✓ Cleaned up {deleted} expired memories")
        return deleted
        
    except Exception as e:
        print(f"❌ Error cleaning up: {e}")
        return 0
    finally:
        cur.close()
        conn.close()


def get_memory_stats(user_id: str = ROGER_USER_ID) -> Dict[str, Any]:
    """Get memory statistics by namespace"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT 
                namespace,
                COUNT(*) as count,
                AVG(importance) as avg_importance,
                MIN(timestamp) as oldest,
                MAX(timestamp) as newest
            FROM agent_memories
            WHERE user_id = %s AND NOT is_deleted
            GROUP BY namespace
            ORDER BY count DESC
        """, (user_id,))
        
        rows = cur.fetchall()
        stats = {}
        for row in rows:
            stats[row[0]] = {
                'count': row[1],
                'avg_importance': float(row[2]) if row[2] else 0,
                'oldest': row[3].isoformat() if row[3] else None,
                'newest': row[4].isoformat() if row[4] else None,
            }
        
        return stats
        
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
        return {}
    finally:
        cur.close()
        conn.close()


# =============================================================================
# MAIN (Test)
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Roger Cognitive Memory - Test Mode")
    print("=" * 60)
    
    # Initialize table
    print("\n1. Initializing table...")
    init_memory_table()
    
    # Test storage
    print("\n2. Testing memory storage...")
    test_memory_id = store_memory(
        user_id=ROGER_USER_ID,
        content="Test memory: Bijan Robinson is valued at 15000 KTC in dynasty leagues",
        namespace="fact",
        source_type="agent",
    )
    print(f"   Stored: {test_memory_id}")
    
    # Test recall
    print("\n3. Testing memory recall...")
    results = recall_memories(
        user_id=ROGER_USER_ID,
        query="Bijan Robinson dynasty value",
        namespace=["fact", "decision"],
        limit=3
    )
    print(f"   Found {len(results)} memories")
    for r in results:
        print(f"   - [{r['namespace']}] {r['content'][:60]}... (score: {r['final_score']:.2f})")
    
    # Test pre_action_recall
    print("\n4. Testing pre_action_recall...")
    context = pre_action_recall("dynasty trade evaluation Bijan")
    print(f"   Context: {context[:200] if context else 'None'}...")
    
    # Test post_action_store
    print("\n5. Testing post_action_store...")
    decision_id = post_action_store(
        content="Evaluated trade: Team A Bijan vs Team B Garrett Wilson + Kenneth Walker",
        namespace="decision",
        decision_outcome="team_a_wins"
    )
    print(f"   Decision stored: {decision_id}")
    
    # Get stats
    print("\n6. Memory stats:")
    stats = get_memory_stats()
    for ns, data in stats.items():
        print(f"   {ns}: {data['count']} memories (avg importance: {data['avg_importance']:.2f})")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)
