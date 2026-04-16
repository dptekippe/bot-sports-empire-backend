"""
Simplified In-Situ Memory Verification System

Verifies memory integrity by testing retrieval:
1. Get recent memories from database
2. Try to retrieve each memory using queries derived from its content
3. Check if similarity scores are above threshold
4. Log pass/fail - no LLM needed, completely free

Usage:
    python memory_verifier.py                    # Run verification
    python memory_verifier.py --hours 24         # Verify last 24 hours
"""
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from pathlib import Path

# Source .env file to get environment variables
_env_file = Path.home() / ".openclaw" / ".env"
if _env_file.exists():
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key] = val

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://dynastydroid_user:BKJZCv57P3sYpi5RGL3ciU9CylXsFRWv@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid"
)

MEMORY_VERIFICATION_LOG = Path.home() / ".openclaw" / "memory_verification_log.jsonl"


def get_recent_memories(hours: int = 24) -> List[Dict]:
    """Fetch recent memory writes from the database."""
    import psycopg2
    
    cutoff = datetime.now() - timedelta(hours=hours)
    
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, content, memory_type, importance, created_at
                   FROM memories 
                   WHERE created_at > %s
                   ORDER BY created_at DESC""",
                (cutoff.isoformat(),)
            )
            rows = cur.fetchall()
    
    return [
        {"id": r[0], "content": r[1], "type": r[2], "importance": r[3], "created_at": r[4]}
        for r in rows
    ]


def extract_query_from_content(content: str) -> str:
    """
    Extract a query from memory content.
    Takes first sentence or key phrase as the query.
    """
    # Take first sentence up to 100 chars
    sentences = content.replace('?', '.').replace('!', '.').split('.')
    if sentences:
        query = sentences[0].strip()
        if len(query) > 100:
            query = query[:100]
        return query if query else content[:100]
    return content[:100]


def test_retrieval(memory_id: int, content: str, threshold: float = 0.35) -> Tuple[bool, float, str]:
    """
    Test retrieval of a specific memory.
    Returns (success, best_score, retrieved_preview)
    
    Note: retrieve() doesn't return memory ID, so we check by content match.
    """
    from memory import retrieve
    
    # Extract query from content
    query = extract_query_from_content(content)
    
    try:
        results = retrieve(query, k=5, similarity_threshold=threshold)
        
        if not results:
            return False, 0.0, "NO_RESULTS"
        
        # Check if our memory content is in results
        # retrieve() doesn't return ID, so we match by content similarity
        for r in results:
            retrieved_content = r.get('content', '')
            score = r.get('score', r.get('similarity', 0))
            
            # Check if content matches (exact or very high similarity)
            if retrieved_content == content:
                return True, score, retrieved_content[:100]
            
            # Also check if first 100 chars match (partial match)
            if retrieved_content[:100] == content[:100]:
                return True, score, retrieved_content[:100]
        
        # Memory not found in results, return best score
        best = results[0]
        score = best.get('score', best.get('similarity', 0))
        preview = best.get('content', '')[:100]
        
        # Check if at least the content is similar (partial match)
        if best.get('similarity', 0) >= 0.95:
            return True, score, preview
        
        return False, score, f"MISMATCH: {preview}"
        
    except Exception as e:
        return False, 0.0, f"ERROR: {str(e)[:50]}"


def run_verification(hours: int = 24) -> Dict:
    """
    Run simplified verification.
    
    Returns summary dict with results.
    """
    print(f"\n{'='*60}")
    print(f" MEMORY VERIFICATION SYSTEM (Simplified)")
    print(f"{'='*60}")
    print(f" Checking memories from last {hours} hours")
    print(f" No LLM - completely free")
    print(f"{'='*60}\n")
    
    # Get recent memories
    memories = get_recent_memories(hours)
    print(f"Found {len(memories)} recent memories\n")
    
    if not memories:
        print("No recent memories to verify.")
        return {"status": "no_memories", "verified": 0, "passed": 0, "failed": 0}
    
    # Test retrieval for each memory
    results = []
    passed = 0
    failed = 0
    
    for m in memories:
        memory_id = m["id"]
        content = m["content"][:150]  # Preview
        mem_type = m["type"]
        
        success, score, preview = test_retrieval(memory_id, m["content"])
        
        if success:
            print(f"✅ [{mem_type}] ID {memory_id}")
            print(f"   Score: {score:.3f}")
            print(f"   Preview: {content[:80]}...")
            passed += 1
        else:
            print(f"❌ [{mem_type}] ID {memory_id}")
            print(f"   Best Score: {score:.3f}")
            print(f"   Stored: {content[:60]}...")
            print(f"   Retrieved: {preview[:60]}...")
            failed += 1
        
        results.append({
            "memory_id": memory_id,
            "type": mem_type,
            "passed": success,
            "score": score,
            "preview": content[:100],
            "retrieved_preview": preview[:100],
            "timestamp": datetime.now().isoformat()
        })
        print()
    
    # Log results
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "hours": hours,
        "memories_checked": len(memories),
        "passed": passed,
        "failed": failed,
        "pass_rate": passed/len(memories) if memories else 0,
        "results": results
    }
    
    with open(MEMORY_VERIFICATION_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    print(f"{'='*60}")
    print(f" VERIFICATION COMPLETE")
    print(f"{'='*60}")
    print(f" Memories Checked: {len(memories)}")
    print(f" Passed: {passed}")
    print(f" Failed: {failed}")
    print(f" Pass Rate: {passed/len(memories)*100:.1f}%")
    print(f" Log: {MEMORY_VERIFICATION_LOG}")
    print(f"{'='*60}\n")
    
    return {
        "status": "complete",
        "verified": len(memories),
        "passed": passed,
        "failed": failed,
        "pass_rate": passed/len(memories) if memories else 0
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Simplified In-Situ Memory Verification")
    parser.add_argument("--hours", type=int, default=24, help="Hours of memories to verify")
    
    args = parser.parse_args()
    
    result = run_verification(hours=args.hours)
    
    exit(0 if result.get("status") == "complete" else 1)
