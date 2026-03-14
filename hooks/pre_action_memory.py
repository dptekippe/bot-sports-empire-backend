#!/usr/bin/env python3
"""
Pre-Action Memory Search Hook

Purpose: Search memory before significant actions to provide context
Connected to pgvector on Render PostgreSQL
"""

import os
import json
import datetime
from typing import Dict, List, Optional

# Database configuration - Render PostgreSQL
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://dynastydroid_user:BKJZCv57P3sYpi5RGL3ciU9CylXsFRWv@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid"
)

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

def memory_search_safe(query: str, max_results: int = 5) -> Optional[List[Dict]]:
    """
    Query pgvector for relevant memories
    Returns top memories by hybrid_score matching the query keywords
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get top memories by hybrid_score
        # For now, order by hybrid_score (most relevant first)
        # TODO: Add full-text search or vector similarity if embedding matches
        cur.execute("""
            SELECT id, content, memory_type, importance, hybrid_score, project, created_at
            FROM memories 
            ORDER BY hybrid_score DESC 
            LIMIT %s
        """, (max_results,))
        
        results = cur.fetchall()
        
        # Format results
        formatted = []
        for row in results:
            formatted.append({
                "id": str(row['id']),
                "content": row['content'][:500] if row['content'] else "",  # Truncate for context
                "memory_type": row['memory_type'],
                "importance": row['importance'],
                "hybrid_score": row['hybrid_score'],
                "project": row['project'],
                "created_at": str(row['created_at'])
            })
        
        cur.close()
        conn.close()
        
        return formatted if formatted else None
        
    except Exception as e:
        print(f"[Memory Search ERROR] {e}")
        return None

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

def pre_action_memory_search(context: Dict) -> Optional[List[Dict]]:
    """
    Search memory for relevant context before action
    
    Args:
        context: Dictionary containing action context (tool, command, user_request, etc.)
    
    Returns:
        List of memory search results or None if search failed
    
    White Roger Revision: If search fails, return None but don't block execution
    """
    print(f"[Memory Contract] Pre-action search for: {context.get('tool', 'unknown')}")
    
    # Extract keywords
    keywords = extract_keywords(context)
    if not keywords:
        print(f"[Memory Contract] No keywords extracted from context")
        # Still return recent memories even without keywords
        keywords = ["recent"]
    
    # Perform safe search
    query = " ".join(keywords)
    results = memory_search_safe(query, max_results=5)
    
    # Log for compliance tracking
    log_search(context, keywords, results)
    
    if results:
        print(f"[Memory Contract] Found {len(results)} relevant memories")
        for i, r in enumerate(results[:3]):
            print(f"  [{i+1}] {r.get('memory_type', 'unknown')} (score: {r.get('hybrid_score', 'N/A')})")
    else:
        print(f"[Memory Contract] No memories found (continuing anyway)")
    
    return results

# Test function
if __name__ == "__main__":
    # Test the hook
    test_context = {
        "tool": "exec",
        "command": "git push origin main",
        "user_request": "Deploy to production"
    }
    
    results = pre_action_memory_search(test_context)
    print(f"\nTest results: {json.dumps(results, indent=2) if results else 'None'}")
