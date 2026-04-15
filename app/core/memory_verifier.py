"""
In-Situ Memory Verification System

Runs after session completion to verify memory integrity:
1. Generate QA pairs from recent memory writes
2. Query memory with those questions
3. Compare answers - repair if mismatch
4. Log verification results

Usage:
    python memory_verifier.py                    # Run verification
    python memory_verifier.py --hours 24         # Verify last 24 hours
    python memory_verifier.py --dry-run          # Don't repair, just report
"""
import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://dynastydroid_user:BKJZCv57P3sYpi5RGL3ciU9CylXsFRWv@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid"
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MEMORY_VERIFICATION_LOG = Path.home() / ".openclaw" / "memory_verification_log.jsonl"
SESSION_STATE_FILE = Path.home() / ".openclaw" / ".verifier_session_state.json"


def get_openai_client():
    import openai
    return openai.OpenAI(api_key=OPENAI_API_KEY)


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


def generate_qa_pairs(memories: List[Dict], client=None) -> List[Dict]:
    """Generate 3-5 QA pairs from memory content using LLM."""
    if not memories:
        return []
    
    if client is None:
        client = get_openai_client()
    
    # Prepare memory context
    memory_texts = []
    for m in memories:
        memory_texts.append(f"- [{m['type']}] {m['content'][:200]}")
    
    context = "\n".join(memory_texts[:10])  # Limit to 10 most recent
    
    prompt = f"""Based on these recent memory entries, generate 3-5 question-answer pairs 
that test whether the key facts would be correctly recalled.

Format each as:
Q: [question]
A: [answer]

Memory entries:
{context}

Questions should test specific facts (names, dates, decisions, preferences) not vague concepts."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a memory QA generator. Generate precise factual questions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        text = response.choices[0].message.content
        
        # Parse QA pairs
        qa_pairs = []
        current_q = None
        current_a = None
        
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('Q:'):
                current_q = line[2:].strip()
            elif line.startswith('A:') and current_q:
                current_a = line[2:].strip()
                qa_pairs.append({"question": current_q, "answer": current_a})
                current_q = None
                current_a = None
        
        return qa_pairs
    
    except Exception as e:
        print(f"Error generating QA pairs: {e}")
        return []


def verify_memory(query: str, client=None) -> str:
    """Query memory system and return answer."""
    if client is None:
        client = get_openai_client()
    
    # Import the memory retrieval function
    from memory import retrieve
    
    try:
        results = retrieve(query, k=3, similarity_threshold=0.35)
        
        if not results:
            return "NO_RESULTS"
        
        # Combine top results into context
        context = "\n".join([
            f"- {r['content'][:200]}"
            for r in results[:3]
        ])
        
        # Ask the memory system the question
        prompt = f"""Based on these memory entries, answer the question.
If the memories don't contain enough information, say "I don't know".

Memories:
{context}

Question: {query}

Answer:"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Answer based ONLY on the provided memory context."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.1
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        return f"ERROR: {e}"


def compare_answers(expected: str, actual: str, client=None) -> Tuple[bool, float]:
    """
    Compare expected vs actual answer.
    Returns (is_match, confidence).
    """
    if client is None:
        client = get_openai_client()
    
    if actual == "NO_RESULTS":
        return False, 0.0
    
    if actual.startswith("ERROR"):
        return False, 0.0
    
    # Use LLM to evaluate semantic similarity
    prompt = f"""Compare these two answers. Are they consistent (same facts, no contradictions)?

Expected: {expected}
Actual: {actual}

Respond with:
SIMILAR [0-1] - where 1 is identical meaning and 0 is completely different/contradictory
REASON: [brief explanation]"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You compare answers for factual consistency."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.0
        )
        
        text = response.choices[0].message.content
        
        # Parse similarity score
        for line in text.split('\n'):
            if line.startswith('SIMILAR'):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        score = float(parts[1])
                        return score >= 0.7, score
                    except ValueError:
                        pass
        
        return False, 0.0
    
    except Exception as e:
        return False, 0.0


def repair_memory(memory_id: int, issue: str, client=None):
    """Flag or repair problematic memory."""
    # For now, just flag it by adding a repair note
    # In future, could rewrite or mark as unreliable
    import psycopg2
    
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE memories 
                   SET content = content || %s
                   WHERE id = %s""",
                (f"\n\n[VERIFICATION_FLAG: {issue}]", memory_id)
            )
        conn.commit()


def get_last_session_count() -> int:
    """Get the last processed session count."""
    if SESSION_STATE_FILE.exists():
        with open(SESSION_STATE_FILE) as f:
            data = json.load(f)
            return data.get("last_session_count", 0)
    return 0


def set_last_session_count(count: int):
    """Save the last processed session count."""
    SESSION_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SESSION_STATE_FILE, 'w') as f:
        json.dump({"last_session_count": count}, f)


def run_verification(hours: int = 24, dry_run: bool = True) -> Dict:
    """
    Run the verification loop.
    
    Returns summary dict with results.
    """
    print(f"\n{'='*60}")
    print(f" MEMORY VERIFICATION SYSTEM")
    print(f"{'='*60}")
    print(f" Checking memories from last {hours} hours")
    print(f" Dry run mode: {dry_run}")
    print(f"{'='*60}\n")
    
    # Get recent memories
    memories = get_recent_memories(hours)
    print(f"Found {len(memories)} recent memories\n")
    
    if not memories:
        print("No recent memories to verify.")
        return {"status": "no_memories", "verified": 0, "passed": 0, "failed": 0}
    
    # Generate QA pairs
    print("Generating QA pairs...")
    qa_pairs = generate_qa_pairs(memories)
    print(f"Generated {len(qa_pairs)} QA pairs\n")
    
    if not qa_pairs:
        print("Failed to generate QA pairs.")
        return {"status": "qa_failed", "verified": 0, "passed": 0, "failed": 0}
    
    # Run verification
    results = []
    passed = 0
    failed = 0
    client = get_openai_client()
    
    for qa in qa_pairs:
        question = qa["question"]
        expected = qa["answer"]
        
        print(f"Q: {question}")
        actual = verify_memory(question)
        
        is_match, confidence = compare_answers(expected, actual, client)
        
        if is_match:
            print(f"  ✅ PASS (confidence: {confidence:.2f})")
            passed += 1
        else:
            print(f"  ❌ FAIL (confidence: {confidence:.2f})")
            print(f"     Expected: {expected[:80]}...")
            print(f"     Actual: {actual[:80]}...")
            
            # Find which memory might be problematic
            if not dry_run:
                # In production, would investigate and potentially repair
                pass
            
            failed += 1
        
        results.append({
            "question": question,
            "expected": expected,
            "actual": actual,
            "passed": is_match,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        })
        print()
    
    # Log results
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "memories_checked": len(memories),
        "qa_pairs": len(qa_pairs),
        "passed": passed,
        "failed": failed,
        "results": results
    }
    
    with open(MEMORY_VERIFICATION_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    print(f"{'='*60}")
    print(f" VERIFICATION COMPLETE")
    print(f"{'='*60}")
    print(f" QA Pairs: {len(qa_pairs)}")
    print(f" Passed: {passed}")
    print(f" Failed: {failed}")
    print(f" Pass Rate: {passed/len(qa_pairs)*100:.1f}%")
    print(f"{'='*60}\n")
    
    return {
        "status": "complete",
        "verified": len(qa_pairs),
        "passed": passed,
        "failed": failed,
        "pass_rate": passed/len(qa_pairs) if qa_pairs else 0
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="In-Situ Memory Verification")
    parser.add_argument("--hours", type=int, default=24, help="Hours of memories to verify")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Don't repair, just report")
    parser.add_argument("--fix", action="store_true", help="Actually repair issues")
    
    args = parser.parse_args()
    
    if args.fix:
        args.dry_run = False
    
    result = run_verification(hours=args.hours, dry_run=args.dry_run)
    
    exit(0 if result.get("status") != "qa_failed" else 1)
