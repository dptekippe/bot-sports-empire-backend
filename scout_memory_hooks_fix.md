# Fix Memory Hooks Critical Bugs

## CONTEXT
Scout conducted a deep code review of two OpenClaw memory hooks. You found 4 CRITICAL bugs and 4 HIGH bugs. Now fix them.

## FILES TO FIX
1. /Users/danieltekippe/.openclaw/hooks/pgvector-memory/handler.ts
2. /Users/danieltekippe/.openclaw/hooks/memory-pre-action/handler.ts

## CRITICAL BUGS TO FIX

### BUG 1: Hybrid Score Calculation Mismatch (CRITICAL)
**Problem:** The two handlers use INCOMPATIBLE hybrid score formulas.

**pgvector-memory** uses:
- Similarity: `1 - (embedding <=> $1::vector)` (inverted, higher = better)
- Recency window: 1 YEAR (`365*24*3600`)

**memory-pre-action** uses:
- Similarity: `embedding <=> $1::vector` (distance directly, lower = better) - INVERSE!
- Recency window: 2 DAYS (`48*60*60`) - orders of magnitude different!

**Fix required:** Unify both to use the SAME formula:
- Similarity: `1 - (embedding <=> $1::vector)` for both (consistent)
- Recency window: 30 DAYS for both
- Formula: `0.5 * similarity + 0.3 * importance_norm + 0.2 * recency_norm`

### BUG 2: hybridSearch Overwrites ALL Rows (CRITICAL)
**Problem:** The hybridSearch UPDATE uses the current query embedding to update ALL memories' hybrid_score. After a search, every memory is mutated with query-specific scores.

**Fix required:** Remove hybrid_score column entirely and compute scores inline in queries. This denormalized column makes no sense since it's query-dependent.

### BUG 3: Default Config Still Has Wrong Dimensions (CRITICAL)
**Problem in pgvector-memory lines ~29-38:**
```typescript
const DEFAULT_CONFIG: MemoryConfig = {
  embeddingModel: 'all-mpnet-base-v2',  // Wrong model
  dimensions: 768,  // Should be 1536
```
But comment says "OpenAI text-embedding-3-small (1536 dimensions)"

**Fix:** Change to:
```typescript
const DEFAULT_CONFIG: MemoryConfig = {
  embeddingModel: 'text-embedding-3-small',
  dimensions: 1536,
  hybridWeights: {
    similarity: 0.5,
    importance: 0.3,
    recency: 0.2
  }
};
```

### BUG 4: NULL .toFixed() Crash (CRITICAL)
**Problem:** If hybrid_score is NULL, `r.hybrid_score.toFixed(2)` throws TypeError.

**Fix:** Add null check:
```typescript
score: ${r.hybrid_score != null ? r.hybrid_score.toFixed(2) : '0.00'}
```

## HIGH PRIORITY BUGS TO FIX

### BUG 5: SQL Injection Risk (HIGH)
**Problem:** `r.content` and `r.project` are interpolated directly into output string in memory-pre-action.

**Fix:** Escape special characters or format as safe JSON structure.

### BUG 6: Redundant/Malformed Connection Handling (HIGH)
**Problem:** `client._connected` doesn't exist on pg Client.

**Fix:** Use proper connection handling - call connect() once at start, handle errors properly.

### BUG 7: Recency Calculation Error for NULL created_at_ts (HIGH)
**Problem:** If created_at_ts is NULL, recency becomes 0 (minimum).

**Fix:** Give recent score when unknown:
```typescript
LEAST(1.0, (($2 - COALESCE(created_at_ts, ($2 - $3)))::float / $3)) as recency_norm
```

## DATABASE SCHEMA CHANGES
If you remove hybrid_score column (Bug 2 fix):
1. Remove hybrid_score column from memories table
2. Remove idx_memories_hybrid index
3. Update hybridSearch() to compute inline without storing

## YOUR TASK
1. Read both files
2. Fix ALL critical bugs (1-4)
3. Fix ALL high priority bugs (5-7)
4. Update DB schema if needed (remove hybrid_score column)
5. Verify both handlers use IDENTICAL hybrid scoring formula
6. Report each change you made

Be thorough - these are production hooks.
