"""
LLM Agent Memory Deduplication Module

Fuzzy deduplication for JSONL memory stores using difflib or embeddings.
"""
import difflib
import time
import random
import string
from typing import List, Dict, Any, Optional
from datetime import datetime


def deduplicate_memory(
    entries: List[Dict[str, Any]],
    threshold: float = 0.85,
    use_embeddings: bool = False
) -> tuple[List[Dict[str, Any]], Dict[str, Any], float]:
    """
    Deduplicate memory entries using fuzzy string matching or embeddings.
    
    Args:
        entries: List of memory entries with 'text', 'priority', 'ts' keys
        threshold: Similarity threshold (default 0.85)
        use_embeddings: If True, use torch embeddings instead of difflib
    
    Returns:
        (deduped_entries, stats, runtime)
        
    Stats returned:
        - pruned: count of duplicates removed
        - avg_sim: average similarity score of compared pairs
        - runtime: execution time in seconds
    """
    start_time = time.time()
    
    if not entries:
        return [], {"pruned": 0, "avg_sim": 0.0, "runtime": 0.0}, 0.0
    
    # Priority ordering (high > med > low)
    priority_rank = {"high": 3, "med": 2, "low": 1}
    
    # Parse timestamps for comparison
    def parse_ts(entry):
        ts = entry.get("ts", "")
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except:
            return datetime.min
    
    # Sort: priority DESC, then ts DESC (newest first)
    sorted_entries = sorted(
        entries,
        key=lambda x: (
            priority_rank.get(x.get("priority", "low"), 0),
            parse_ts(x)
        ),
        reverse=True
    )
    
    n = len(sorted_entries)
    to_remove = set()
    similarity_scores = []
    
    # O(n²) pairwise comparison with early termination
    for i in range(n):
        if i in to_remove:
            continue
            
        text_i = sorted_entries[i].get("text", "")
        
        for j in range(i + 1, n):
            if j in to_remove:
                continue
            
            text_j = sorted_entries[j].get("text", "")
            
            if use_embeddings:
                sim = _embedding_similarity(text_i, text_j)
            else:
                sim = difflib.SequenceMatcher(None, text_i, text_j).ratio()
            
            similarity_scores.append(sim)
            
            if sim >= threshold:
                # Mark j for removal (lower priority/older)
                to_remove.add(j)
    
    # Build dedpreserve original order within priority groupsuped list ()
    deduped = []
    seen_texts = set()  # For stable output order
    
    for i, entry in enumerate(sorted_entries):
        if i not in to_remove:
            deduped.append(entry)
    
    # Sort by timestamp for output (newest first)
    deduped = sorted(deduped, key=lambda x: parse_ts(x), reverse=True)
    
    # Calculate stats
    runtime = time.time() - start_time
    avg_sim = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.0
    
    stats = {
        "pruned": len(entries) - len(deduped),
        "avg_sim": round(avg_sim, 2),
        "runtime": round(runtime, 4)
    }
    
    return deduped, stats, runtime


def _embedding_similarity(text1: str, text2: str) -> float:
    """Compute cosine similarity using sentence-transformers."""
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        # Lazy load model
        if not hasattr(_embedding_similarity, "model"):
            _embedding_similarity.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        emb1 = _embedding_similarity.model.encode([text1])
        emb2 = _embedding_similarity.model.encode([text2])
        
        return cosine_similarity(emb1, emb2)[0][0]
    except ImportError:
        # Fallback to difflib if torch not available
        return difflib.SequenceMatcher(None, text1, text2).ratio()


def generate_dummy_entries(n: int = 5000, seed: int = 42) -> List[Dict[str, Any]]:
    """Generate dummy memory entries for benchmarking."""
    random.seed(seed)
    
    templates = [
        "Bijan Robinson superflex dynasty value {val}, elite RB1",
        "Superflex Bijan RB1 trade value ~{val}",
        "Bijan dynasty RB1 {val} value",
        "Josh Allen QB1 trade value {val}",
        "Jahmyr Gibbs rookie RB1 ADP {val}",
        "Marvin Harrison Jr rookie WR1 draft {val}",
        "Breece Hall Jets RB1 value {val}",
        "Puka Nacua rookie WR1 sleeper {val}",
        "Jalen Hurts rushing TDs fantasy {val}",
        "Christian McCaffrey injury update {val}",
    ]
    
    priorities = ["high", "med", "low"]
    entries = []
    
    for i in range(n):
        template = random.choice(templates)
        text = template.format(val=random.randint(80, 99))
        
        # Add slight variations for some entries
        if random.random() < 0.3:
            text += " " + random.choice(["update", "news", "note", "check"])
        
        entries.append({
            "text": text,
            "priority": random.choice(priorities),
            "ts": f"2026-03-{random.randint(1, 11):02d}"
        })
    
    return entries


def benchmark(n: int = 5000) -> Dict[str, Any]:
    """Run benchmark on dummy entries."""
    print(f"Generating {n} dummy entries...")
    entries = generate_dummy_entries(n)
    
    print(f"Running deduplication...")
    deduped, stats, runtime = deduplicate_memory(entries, threshold=0.85)
    
    print(f"\n=== BENCHMARK RESULTS ===")
    print(f"Input entries:  {n}")
    print(f"Output entries: {len(deduped)}")
    print(f"Pruned:        {stats['pruned']}")
    print(f"Avg similarity: {stats['avg_sim']}")
    print(f"Runtime:       {stats['runtime']:.4f}s")
    print(f"Target:        <3s | {'✅ PASS' if stats['runtime'] < 3 else '❌ FAIL'}")
    
    return {
        "input": n,
        "output": len(deduped),
        **stats,
        "pass": stats["runtime"] < 3
    }


if __name__ == "__main__":
    # Test with sample input
    sample = [
        {"text": "Bijan Robinson superflex dynasty value 98, elite RB1", "priority": "high", "ts": "2026-03-11"},
        {"text": "Superflex Bijan RB1 trade value ~96", "priority": "med", "ts": "2026-03-10"},
        {"text": "Bijan dynasty RB1 97 value", "priority": "high", "ts": "2026-03-11"},
    ]
    
    print("=== SAMPLE INPUT ===")
    print(f"Entries: {len(sample)}")
    for e in sample:
        print(f"  {e}")
    
    deduped, stats, runtime = deduplicate_memory(sample, threshold=0.85)
    
    print(f"\n=== SAMPLE OUTPUT ===")
    print(f"Entries: {len(deduped)}")
    for e in deduped:
        print(f"  {e}")
    print(f"\nStats: {stats}")
    print(f"Runtime: {runtime:.4f}s")
    
    # Edge case: All identical high-pri
    print("\n=== EDGE CASE: All identical high-pri ===")
    identical = [
        {"text": "Same memory entry", "priority": "high", "ts": "2026-03-11"},
        {"text": "Same memory entry", "priority": "high", "ts": "2026-03-10"},
        {"text": "Same memory entry", "priority": "high", "ts": "2026-03-09"},
    ]
    deduped, stats, runtime = deduplicate_memory(identical, threshold=0.85)
    print(f"Input: 3 identical high-pri | Output: {len(deduped)} (should be 1)")
    print(f"Kept: {deduped[0] if deduped else 'NONE'}")
    
    # Benchmark
    print("\n=== 5K BENCHMARK ===")
    benchmark(5000)
