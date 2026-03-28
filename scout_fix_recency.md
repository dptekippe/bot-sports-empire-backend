# Fix pgvector Memory Recency Formula

## Problem
Current recency formula rewards STALENESS, not RECENCY:
```
recency_value = (current_ts - created_at_ts) / 30_days
```
- Brand new memory (2 min old) → recency ≈ 0.00006 (nearly zero!)
- 30+ day old memory → recency = 1.0 (maximum!)

This is backwards. Old memories score highest, new memories score lowest.

## Required Solution
Implement **exponential decay** for recency:
```
recency_decay = EXP(-age_days / decay_rate)
```
- Fresh memory (age=0): recency_decay = 1.0
- 7 days old: recency_decay ≈ 0.368 (half-life)
- 30 days old: recency_decay ≈ 0.014

## Files to Update
1. `/Users/danieltekippe/.openclaw/hooks/pgvector-memory/handler.ts`
2. `/Users/danieltekippe/.openclaw/hooks/memory-pre-action/handler.ts`

## Requirements

### 1. Implement Exponential Decay
Update the recency calculation in both handlers to use:
```sql
recency_decay = EXP(-age_seconds / (86400 * decay_rate_days))
-- or equivalent in the query language
```

Where `decay_rate_days` is configurable (default: 7).

### 2. Make decay_rate Configurable
Add `RECENCY_DECAY_DAYS` env var (default: 7).

### 3. Fix Timestamp Field Names
The memories table has:
- `created_at_ts` (bigint) - Unix timestamp in SECONDS
- `created_at` (timestamp with time zone)

Use the correct field for the calculation. If using `created_at_ts`, convert appropriately.

### 4. Keep Formula Consistent
Both handlers MUST use IDENTICAL formula:
```sql
0.5 * cosine_similarity + 0.3 * importance_score + 0.2 * recency_decay
```

### 5. Verify with Tests
After updating:
- Fresh memory (age≈0): recency_decay ≈ 1.0
- 7 day old memory: recency_decay ≈ 0.368
- 30 day old memory: recency_decay ≈ 0.014

### 6. Compile and Deploy
After fixing:
1. Compile both TypeScript handlers to JavaScript
2. Restart OpenClaw gateway to load new code
3. Test with a new memory to verify formula works

## Database Connection
```
postgresql://dynastydroid_user:BKJZCv57P3sYpi5RGL3ciU9CylXsFRWv@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid
```

## Verification SQL
After deployment, test with:
```sql
SELECT 
  id,
  LEFT(content, 60),
  importance,
  created_at_ts,
  NOW(),
  0.5 * (1 - (embedding <=> query_embedding)) +
  0.3 * (importance / 10.0) +
  0.2 * EXP( -EXTRACT(EPOCH FROM (NOW() - created_at)) / (86400 * 7) ) as hybrid_score
FROM memories
ORDER BY hybrid_score DESC
LIMIT 5;
```

## Important
- Preserve existing data (no migration needed)
- Log "Exponential decay deployed: decay_rate=X" when deployed
- Both handlers must use IDENTICAL formula
