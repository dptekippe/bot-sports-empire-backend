#!/usr/bin/env python3
"""
Memory Search Tool - Dual semantic + vector search on pgvector memories table
Usage: python3 memory_search.py "your query here"
"""
import sys
import json
import psycopg2
from datetime import datetime

# Database connection
DB_URL = "postgresql://dynastydroid_user:BKJZCv57P3sYpi5RGL3ciU9CylXsFRWv@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid"

def search_memories(query, max_results=5):
    """Hybrid search: semantic similarity + keyword match"""
    if not query or len(query.strip()) < 2:
        return {"error": "Query too short", "results": []}
    
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        # Hybrid search query
        # Uses semantic similarity (cosine distance) + keyword match (ts_rank)
        search_query = query.strip().lower()
        
        sql = """
            WITH keyword_match AS (
                SELECT id, content, created_at, importance, domain, tags,
                       ts_rank(to_tsvector('english', content), plainto_tsquery('english', %s)) as keyword_score,
                       0.0 as similarity
                FROM memories
                WHERE to_tsvector('english', content) @@ plainto_tsquery('english', %s)
            ),
            semantic_match AS (
                SELECT id, content, created_at, importance, domain, tags,
                       0.0 as keyword_score,
                       1 - (embedding <=> (SELECT embedding FROM memories WHERE content LIKE %s LIMIT 1)) as similarity
                FROM memories
                WHERE content LIKE %s AND embedding IS NOT NULL
            )
            SELECT id, content, created_at, importance, domain, tags,
                   MAX(keyword_score) as keyword_score,
                   MAX(similarity) as similarity,
                   (COALESCE(MAX(keyword_score), 0) * 0.4 + COALESCE(MAX(similarity), 0) * 0.6) as hybrid_score
            FROM (
                SELECT * FROM keyword_match
                UNION ALL
                SELECT * FROM semantic_match
            ) combined
            WHERE content IS NOT NULL
            GROUP BY id, content, created_at, importance, domain, tags
            ORDER BY hybrid_score DESC, created_at DESC
            LIMIT %s
        """
        
        like_pattern = f"%{search_query}%"
        cur.execute(sql, (search_query, search_query, like_pattern, like_pattern, max_results))
        rows = cur.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "id": str(row[0]),
                "content": row[1][:200] + "..." if len(row[1]) > 200 else row[1],
                "created_at": row[2].isoformat() if row[2] else None,
                "importance": row[3] or 1.0,
                "domain": row[4] or "general",
                "tags": row[5] or [],
                "keyword_score": float(row[6]) if row[6] else 0.0,
                "similarity": float(row[7]) if row[7] else 0.0,
                "hybrid_score": float(row[8]) if row[8] else 0.0
            })
        
        cur.close()
        conn.close()
        
        return {"query": query, "count": len(results), "results": results}
        
    except Exception as e:
        return {"error": str(e), "results": []}

def format_results(response):
    """Format results for human reading"""
    if "error" in response:
        return f"Error: {response['error']}"
    
    if not response["results"]:
        return f"No memories found for: '{response['query']}'"
    
    output = [f"\n🔍 Memory Search: \"{response['query']}\""]
    output.append(f"Found {response['count']} results:\n")
    
    for i, r in enumerate(response["results"], 1):
        output.append(f"{'='*60}")
        output.append(f"[{i}] Score: {r['hybrid_score']:.3f} | {r['domain']} | {r['created_at'][:10]}")
        output.append(f"    {r['content']}")
        if r['tags']:
            output.append(f"    Tags: {', '.join(r['tags'])}")
        output.append("")
    
    return "\n".join(output)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 memory_search.py \"your query here\"")
        print("Example: python3 memory_search.py \"code review\"")
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    response = search_memories(query)
    print(format_results(response))
