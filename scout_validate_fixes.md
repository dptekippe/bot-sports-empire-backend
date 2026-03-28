# Validate Memory Hooks Fixes

## CONTEXT
The memory hooks were just fixed by Scout. Now we need to VALIDATE the fixes produce correct behavior - not just assume they work.

## VALIDATION TASKS

### 1. Verify TypeScript compiles

Check both files:
- /Users/danieltekippe/.openclaw/hooks/pgvector-memory/handler.ts
- /Users/danieltekippe/.openclaw/hooks/memory-pre-action/handler.ts

Run tsc or check for syntax errors.

### 2. Verify hybrid scoring formula produces EXPECTED values

The unified formula (both handlers now use):
```sql
0.5 * (1 - (embedding <=> $1::vector)) +
0.3 * (importance / 10.0) +
0.2 * LEAST(1.0, (($2 - COALESCE(created_at_ts, ($2 - $3)))::float / $3))
```

Where $2 = current Unix timestamp, $3 = 2592000 (30 days).

Write test SQL to verify this produces reasonable 0-1 scores.

Database:
postgresql://dynastydroid_user:BKJZCv57P3sYpi5RGL3ciU9CylXsFRWv@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid

### 3. Verify semantic search works end-to-end

Insert a test memory, search for it, verify it returns with high similarity.

### 4. Trace through memory-pre-action logic

Read the fixed handler and trace:
- Does it correctly extract user message?
- Does it generate embedding correctly?
- Does it format memories safely?
- Does injection work?

### 5. Check for edge cases

- NULL hybrid_score handling
- NULL created_at_ts handling
- Empty results handling
- Very long content truncation

## REPORT

For each step: PASS/FAIL + details

If new bugs found, report them clearly.
