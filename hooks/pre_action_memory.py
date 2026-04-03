#!/usr/bin/env python3
"""
Pre-Action Memory Search Hook

Purpose: Search memory before significant actions to provide context
Connected to pgvector on Render PostgreSQL

Integrates with cognitive_memory.py for enhanced recall:
- memories table: Fast keyword search
- agent_memories table: Semantic search via OpenAI embeddings

HOOK HEALTH INTEGRATION:
- Checks hook health before operations
- Tags outputs with degradation flags
- Applies confidence discounts when degraded
- Respects circuit breaker halts

MEMORY RETRIEVAL CONTRACT (2026-04-03):
- Domain tagging for selective recall
- Skip logic for short/generic queries
- Machine-friendly injection format
- Recall event logging for calibration
"""

import os
import sys
import json
import datetime
from typing import Dict, List, Optional, Tuple

# Add workspace to path for cognitive_memory import
sys.path.insert(0, '/Users/danieltekippe/.openclaw/workspace')

# Import cognitive_memory for enhanced recall
try:
    import cognitive_memory
    COGNITIVE_MEMORY_AVAILABLE = True
except ImportError:
    COGNITIVE_MEMORY_AVAILABLE = False

# Import hook health monitor for degradation awareness
try:
    from hook_health_monitor import get_degradation_context, apply_confidence_discount, HookState
    HOOK_HEALTH_AVAILABLE = True
except ImportError:
    HOOK_HEALTH_AVAILABLE = False

# Database configuration - Environment variable REQUIRED
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# =============================================================================
# EMBEDDING (2026-04-03: True pgvector semantic search)
# =============================================================================

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_API_KEY = os.environ.get("OPENAI_API_KEY")


def get_query_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding for query text using text-embedding-3-small"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=EMBEDDING_API_KEY)
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"[Embedding ERROR] Failed to generate query embedding: {e}")
        return None


# =============================================================================
# DOMAIN DETECTION (2026-04-03 spec)
# =============================================================================

DOMAIN_TRIGGERS = {
    'architecture': ['build', 'design', 'implement', 'create', 'setup', 'architect', 'system', 'infrastructure', 'deploy', 'render', 'postgres', 'database', 'api', 'endpoint', 'server', 'config'],
    'trade': ['trade', 'accept', 'reject', 'offer', 'value', 'dynasty', 'roster', 'draft', 'player', 'fantasy', 'superflex', 'ktc', 'pick', 'sf'],
    'memory-system': ['memory', 'recall', 'pgvector', 'hook', 'embed', 'retrieve', 'cognitive', 'store', 'vector', 'embedding'],
    'agent-ops': ['scout', 'hermes', 'iris', 'team', 'delegate', 'agent', 'subagent', 'orchestrator', 'blackboard'],
    'project': ['dynastydroid', 'moltbook', 'platform', 'feature', 'ui', 'frontend', 'dashboard', 'trade-calculator', 'draft'],
    'episodic': ['log', 'checkin', 'daily', 'standup', 'note', 'journal', 'reflection', 'yesterday', 'today', 'blocker'],
}

DOMAIN_KEYWORDS = set()
for triggers in DOMAIN_TRIGGERS.values():
    DOMAIN_KEYWORDS.update(triggers)


def detect_domain(content: str) -> str:
    """Detect domain from content using trigger keywords"""
    content_lower = content.lower()
    scores = {}
    for domain, triggers in DOMAIN_TRIGGERS.items():
        score = sum(1 for t in triggers if t in content_lower)
        scores[domain] = score
    if max(scores.values()) > 0:
        return max(scores, key=scores.get)
    return 'episodic'


# =============================================================================
# REVISED SKIP LOGIC (2026-04-03 spec)
# =============================================================================

def should_skip_recall(query: str) -> Tuple[bool, str]:
    """Returns (skip, reason)"""
    tokens = query.lower().split()
    
    # Skip if too short and generic
    if len(tokens) < 3:
        # Check if domain-rich (allow short domain phrases)
        if any(t in DOMAIN_KEYWORDS for t in tokens):
            return False, "domain-rich short query"
        return True, "too short and generic"
    
    # Skip if >60% stopwords
    stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'what', 'how', 'why', 'when', 'where', 'who'}
    if sum(1 for t in tokens if t in stopwords) / len(tokens) > 0.6:
        return True, "too generic (>60% stopwords)"
    
    return False, ""


# =============================================================================
# MACHINE-FRIENDLY INJECTION FORMAT (2026-04-03 spec)
# =============================================================================

def format_memory_for_injection(memory: dict, similarity: float) -> str:
    """Format memory in machine-parseable format for injection"""
    tags = memory.get('tags', []) or []
    if isinstance(tags, str):
        tags = [tags]
    
    # Safely get title and content
    title = memory.get('title', '') or ''
    content = memory.get('content', '') or ''
    if not title and content:
        title = content[:50]
    
    # Safely get timestamp (show just date)
    timestamp = memory.get('timestamp', '') or ''
    if not timestamp:
        created_at = memory.get('created_at', '')
        if created_at:
            # Handle datetime objects
            ts_str = str(created_at)
            timestamp = ts_str[:10]  # YYYY-MM-DD
    
    # Safely get snippet
    snippet = memory.get('snippet', '') or ''
    if not snippet:
        snippet = content[:200]
    
    source = memory.get('source', 'unknown') or 'unknown'
    
    return f"""[MEMORY] {title}
source: {source} | timestamp: {timestamp}
similarity: {similarity if similarity is not None else 0.0:.2f} | tags: {', '.join(tags)}
{snippet}"""


# =============================================================================
# RECALL LOGGING (2026-04-03 spec)
# =============================================================================

def log_recall_event(query: str, top_score: float, hit_count: int, injected_ids: list):
    """Log to recall_log table for calibration"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Create recall_log table if not exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS recall_log (
                id SERIAL PRIMARY KEY,
                query TEXT NOT NULL,
                top_score FLOAT,
                hit_count INT,
                injected_ids TEXT[],
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # Insert log entry
        cur.execute("""
            INSERT INTO recall_log (query, top_score, hit_count, injected_ids)
            VALUES (%s, %s, %s, %s)
        """, (query, top_score, hit_count, injected_ids))
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"[Recall Log ERROR] {e}")


# =============================================================================
# KEYWORD EXTRACTION
# =============================================================================

def extract_keywords(context: Dict) -> List[str]:
    """Extract search keywords from context"""
    keywords = []
    
    # Extract from tool type
    if 'tool' in context:
        keywords.append(context['tool'])
    
    # Extract from command/action
    if 'command' in context:
        # Simple keyword extraction from command
        words = context['command'].split()
        keywords.extend([w for w in words if len(w) > 3][:3])
    
    # Extract from user request if present
    if 'user_request' in context:
        words = context['user_request'].split()
        keywords.extend([w for w in words if len(w) > 3][:3])
    
    # Also extract from message if present
    if 'message' in context:
        words = context['message'].split()
        keywords.extend([w for w in words if len(w) > 3][:3])
    
    return list(set(keywords))  # Remove duplicates

def memory_search_safe(query: str, max_results: int = 5, domain: Optional[str] = None, 
                        query_embedding: Optional[List[float]] = None) -> Optional[List[Dict]]:
    """
    Query pgvector for relevant memories using TRUE SEMANTIC SIMILARITY.
    Uses <+> cosine distance operator with query embedding.
    
    Args:
        query: Search query string (used for logging if embedding provided)
        max_results: Maximum number of results to return (default 5)
        domain: Optional domain filter (pre-filters before similarity search)
        query_embedding: Pre-computed embedding for the query (optional, will generate if not provided)
    
    Returns:
        List of memories with real similarity scores from pgvector
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        # Generate query embedding if not provided (2026-04-03: True semantic search)
        if query_embedding is None:
            query_embedding = get_query_embedding(query)
            if query_embedding is None:
                print("[Memory Search ERROR] Could not generate query embedding")
                return None
        
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build TRUE SEMANTIC SEARCH query using pgvector <+> cosine distance
        # Domain filter narrows the search space first (efficient pre-filter)
        # Then semantic similarity orders the results
        if domain:
            # Domain filtered semantic search
            cur.execute("""
                SELECT id, content, memory_type, importance, project, created_at, domain, tags,
                       embedding <=> %s::vector AS distance,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM memories 
                WHERE domain = %s AND embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, query_embedding, domain, query_embedding, max_results))
        else:
            # Pure semantic search across all memories
            cur.execute("""
                SELECT id, content, memory_type, importance, project, created_at, domain, tags,
                       embedding <=> %s::vector AS distance,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM memories 
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, query_embedding, query_embedding, max_results))
        
        results = cur.fetchall()
        
        # Calculate avg distance and similarity for logging
        avg_distance = None
        avg_similarity = None
        if results:
            distances = [r['distance'] for r in results if r['distance'] is not None]
            similarities = [r['similarity'] for r in results if r['similarity'] is not None]
            avg_distance = sum(distances) / len(distances) if distances else None
            avg_similarity = sum(similarities) / len(similarities) if similarities else None
        
        # Format results with machine-friendly format (2026-04-03 spec)
        formatted = []
        for row in results:
            memory = {
                "id": str(row['id']),
                "content": row['content'][:500] if row['content'] else "",
                "memory_type": row['memory_type'],
                "importance": row['importance'],
                "similarity": row['similarity'],  # REAL semantic similarity from pgvector
                "distance": row['distance'],       # Actual cosine distance
                "project": row['project'],
                "created_at": str(row['created_at'])[:10],  # Just date YYYY-MM-DD
                "domain": row.get('domain', 'episodic'),
                "tags": row.get('tags', []),
                "source": "memories",
                "timestamp": str(row['created_at'])[:10],  # Just date YYYY-MM-DD
            }
            # Add injection format using REAL similarity
            memory["injection_format"] = format_memory_for_injection(memory, row['similarity'])
            formatted.append(memory)
        
        cur.close()
        conn.close()
        
        # Log calibration data
        if formatted:
            _log_similarity_calibration(query, avg_distance, avg_similarity, [m['id'] for m in formatted])
        
        return formatted if formatted else None
        
    except Exception as e:
        print(f"[Memory Search ERROR] {e}")
        return None


def _log_similarity_calibration(query: str, avg_distance: Optional[float], 
                                avg_similarity: Optional[float], injected_ids: List[str]):
    """Log similarity calibration data (2026-04-03)"""
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO recall_log (query, top_score, hit_count, injected_ids, avg_similarity, avg_distance)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (query, avg_similarity or 0, len(injected_ids), injected_ids, avg_similarity, avg_distance))
        
        cur.close()
        conn.close()
        print(f"[Calibration Log] query={query[:50]}... dist={avg_distance:.4f} sim={avg_similarity:.4f} ids={len(injected_ids)}")
    except Exception as e:
        print(f"[Calibration Log ERROR] {e}")


def log_search(context: Dict, keywords: List[str], results: Optional[List[Dict]]):
    """Log search for compliance tracking"""
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "context": context,
        "keywords": keywords,
        "results_count": len(results) if results else 0,
        "search_successful": results is not None
    }
    print(f"[Memory Contract] Search logged: {log_entry['results_count']} results")


# =============================================================================
# PRE-ACTION RECALL (updated 2026-04-03) - OpenClaw Tool
# =============================================================================

def pre_action_recall(query: str, domain: Optional[str] = None, limit: int = 3) -> str:
    """
    Standalone recall function exposed as OpenClaw tool.
    
    Args:
        query: Search query string
        domain: Optional domain filter (architecture, trade, memory-system, agent-ops, project, episodic)
        limit: Maximum number of results (default 3, max 5)
    
    Returns:
        Formatted memory context string for injection
    
    Usage:
        result = pre_action_recall("dynasty trade Bijan Robinson", domain="trade")
    """
    limit = min(limit, 5)
    
    # Apply skip logic
    skip, reason = should_skip_recall(query)
    if skip:
        print(f"[Memory Contract] Skipping recall: {reason}")
        return ""
    
    # Perform search with optional domain filter
    results = memory_search_safe(query, max_results=limit, domain=domain)
    
    if not results:
        return ""
    
    # Build formatted output
    context_parts = ["\n### Relevant Memory Context:\n"]
    top_score = 0.0
    hit_count = 0
    injected_ids = []
    
    for m in results:
        hit_count += 1
        injected_ids.append(m['id'])
        # Use REAL similarity from pgvector (2026-04-03)
        score = m.get('similarity') or m.get('hybrid_score') or 0.0
        if score > top_score:
            top_score = score
        
        # Use machine-friendly injection format
        context_parts.append(m.get('injection_format', m['content'][:200]))
    
    # Log recall event
    log_recall_event(query, top_score, hit_count, injected_ids)
    
    return "\n".join(context_parts)


def pre_action_memory_search(context: Dict, domain: Optional[str] = None) -> Optional[List[Dict]]:
    """
    Search memory for relevant context before action
    
    Args:
        context: Dictionary containing action context (tool, command, user_request, etc.)
        domain: Optional domain filter (architecture, trade, memory-system, agent-ops, project, episodic)
    
    Returns:
        List of memory search results or None if search failed
        Results include degradation_tags when hook health is degraded
    
    HOOK HEALTH INTEGRATION:
    - Checks circuit breaker before execution
    - Tags outputs with degradation flag when degraded
    - Applies confidence discount to base confidence
    
    White Roger Revision: If search fails, return None but don't block execution
    
    MEMORY RETRIEVAL CONTRACT (2026-04-03):
    - Skip logic: filter short/generic queries
    - Domain detection: filter by domain when specified
    - Machine-friendly injection format
    - Recall event logging for calibration
    """
    # Check hook health status first
    degradation_tags = {}
    if HOOK_HEALTH_AVAILABLE:
        try:
            health_ctx = get_degradation_context()
            if health_ctx["circuit_breaker_open"]:
                print(f"[Memory Contract] ⚠️ Circuit breaker open - halting memory search")
                print(f"  Halted: {health_ctx['halted_operations']}")
                return None
            if health_ctx["is_degraded"]:
                degradation_tags["degraded"] = True
                degradation_tags["confidence_multiplier"] = health_ctx["confidence_multiplier"]
                degradation_tags["degraded_hooks"] = health_ctx["degraded_hooks"]
                print(f"[Memory Contract] ⚠️ Running in degraded mode")
                print(f"  Confidence multiplier: {health_ctx['confidence_multiplier']}")
                print(f"  Degraded hooks: {health_ctx['degraded_hooks']}")
        except Exception as e:
            print(f"[Memory Contract] Health check failed: {e}")
    
    print(f"[Memory Contract] Pre-action search for: {context.get('tool', 'unknown')}")
    
    # Build query text for skip logic
    query_text = context.get('command', '') or context.get('user_request', '') or context.get('message', '') or ""
    
    # Apply skip logic (2026-04-03 spec)
    skip, reason = should_skip_recall(query_text)
    if skip:
        print(f"[Memory Contract] Skipping recall: {reason}")
        return None
    
    # Detect domain from context (2026-04-03 spec)
    detected_domain = detect_domain(query_text)
    print(f"[Memory Contract] Detected domain: {detected_domain}")
    
    # Extract keywords
    keywords = extract_keywords(context)
    if not keywords:
        print(f"[Memory Contract] No keywords extracted from context")
        # Still return recent memories even without keywords
        keywords = ["recent"]
    
    # Build query text and generate embedding ONCE (2026-04-03: True semantic search)
    query_text_for_search = " ".join(keywords)
    query_embedding = get_query_embedding(query_text_for_search)
    
    # Perform TRUE SEMANTIC SEARCH on memories table using pgvector
    # Pass detected domain for filtering and pre-computed embedding for efficiency
    results = memory_search_safe(query_text_for_search, max_results=5, 
                                 domain=detected_domain, query_embedding=query_embedding)
    
    # ALSO call cognitive_memory.pre_action_recall() for semantic search
    cognitive_results = None
    if COGNITIVE_MEMORY_AVAILABLE:
        try:
            cognitive_context = cognitive_memory.pre_action_recall(query_text)
            if cognitive_context:
                print(f"[Memory Contract] Cognitive memory found context")
                cognitive_results = [{"content": cognitive_context, "source": "cognitive_memory"}]
        except Exception as e:
            print(f"[Memory Contract] Cognitive memory search failed: {e}")
    
    # Log for compliance tracking
    log_search(context, keywords, results)
    
    # Calculate top score and hit count for recall logging (using REAL similarity)
    top_score = 0.0
    hit_count = 0
    injected_ids = []
    
    if results:
        print(f"[Memory Contract] Found {len(results)} relevant memories (pgvector semantic)")
        for i, r in enumerate(results[:3]):
            sim = r.get('similarity', 0.0)
            dist = r.get('distance', 0.0)
            print(f"  [{i+1}] {r.get('memory_type', 'unknown')} (sim={sim:.4f}, dist={dist:.4f})")
        top_score = results[0].get('similarity', 0.0) if results else 0.0
        hit_count = len(results)
        injected_ids = [r['id'] for r in results]
    else:
        print(f"[Memory Contract] No memories found (continuing anyway)")
    
    # Log recall event (2026-04-03 spec)
    log_recall_event(query_text, top_score, hit_count, injected_ids)
    
    # Combine results - cognitive results first (higher priority), then pgvector
    if cognitive_results and results:
        combined = cognitive_results + results
    elif cognitive_results:
        combined = cognitive_results
    else:
        combined = results
    
    # Tag results with degradation info
    if combined and degradation_tags:
        for r in combined:
            r["degradation"] = degradation_tags
    
    return combined

# Test function
if __name__ == "__main__":
    # Test pre_action_recall (the new OpenClaw tool)
    print("\n=== Testing pre_action_recall ===")
    result = pre_action_recall("dynasty trade Bijan Robinson", domain="trade", limit=3)
    print(f"Result: {result}")
    
    print("\n=== Testing pre_action_memory_search ===")
    # Test the hook
    test_context = {
        "tool": "exec",
        "command": "deploy to render production",
        "user_request": "Deploy DynastyDroid to production"
    }
    
    results = pre_action_memory_search(test_context)
    print(f"\nTest results: {json.dumps(results, indent=2) if results else 'None'}")
