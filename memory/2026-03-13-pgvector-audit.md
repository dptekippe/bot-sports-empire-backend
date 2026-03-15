# pgvector Memories Audit - March 13, 2026

## Database: dynastydroid (Render PostgreSQL)

### Query Results

| Query | Result |
|-------|--------|
| Total memories | 8 |
| Structured (memory_type not null) | 8 |
| Embedding dimensions | 384 |
| Vector search | ✓ OK |

### Top Memories by Importance

| memory_type | importance | project |
|-------------|------------|---------|
| procedure | 10.0 | Roger-core |
| instruction | 9.0 | Roger-core |
| fact | 8.0 | personal |
| general | 5.0 | general |
| general | 5.0 | general |

### All Memories

| id | memory_type | importance | project | created_at |
|----|-------------|------------|---------|------------|
| d0cb10b8-ecb6-4448-9f94-f7dcaa8e1fd4 | procedure | 10.0 | Roger-core | 2026-03-13 22:13:35 |
| 8ef5bdea-5ee9-4684-b374-981dd22fefb6 | instruction | 9.0 | Roger-core | 2026-03-13 21:39:39 |
| e884cf73-299a-48e2-93f5-7660cbe080b8 | fact | 8.0 | personal | 2026-03-13 21:37:44 |
| faade4a1-6940-4791-84f9-42bfc51af44e | general | 5.0 | general | 2026-03-13 21:33:42 |
| 0c5a7578-c12c-4789-aa12-7b3d0c4feedc | general | 5.0 | general | 2026-03-13 21:09:24 |
| f6fae21b-f77c-4cbc-84a4-5d2de73ee654 | general | 5.0 | general | 2026-03-13 20:45:04 |
| 3c42d6e6-6e21-4cee-981a-6809a930f207 | general | 5.0 | general | 2026-03-13 19:41:16 |
| f18442a4-6716-46ea-a51f-f37663eac408 | general | 5.0 | general | 2026-03-13 19:41:16 |

### Handler Queries

**File:** `app/core/memory.py`

```python
# Semantic search query
SELECT content, source_file 
FROM memories 
ORDER BY embedding <=> %s::vector 
LIMIT %s

# Store memory
INSERT INTO memories 
(content, embedding, source_file, memory_type, tags, importance, project, sensitivity)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
```

✓ Queries verified working

### Injection Test: "Plan backup script"

```
Returned: 3 results
- Result 1: "Remember this" instruction (procedure)
- Result 2: Core Identity (general)
- Result 3: Claude skills documentation (fact)
```

✓ Injection working - memories retrieved and ready for injection

### Issues Found

1. **Embedding Model Mismatch**
   - Milestone stated: 768dim (all-mpnet-base-v2)
   - Actual: 384dim (all-MiniLM-L6-v2)
   - Impact: Low - both work for semantic search

2. **Hybrid Scoring Not Applied**
   - Milestone stated: 0.5×similarity + 0.3×importance + 0.2×recency
   - Actual: Only similarity (cosine distance) used
   - Impact: Medium - importance/recency not weighted

3. **Importance Null in Results**
   - retrieve() returns importance: None
   - Should return importance for hybrid scoring

---

## VERDICT: ⚠️ PARTIALLY HEALTHY

- ✓ Table exists with 8 memories
- ✓ Vector search works
- ✓ Handler queries verified
- ✓ Injection test passed
- ⚠️ Embedding model: 384dim (not 768)
- ⚠️ Hybrid scoring not implemented
