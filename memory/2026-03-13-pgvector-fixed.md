# pgvector Fix Report - March 13, 2026

## Database: dynastydroid (Render PostgreSQL)

### Fixes Applied

| Step | Action | Status |
|------|--------|--------|
| 1 | Add hybrid_score column | ✓ Done |
| 2 | Update Roger-core importance to 8 | ✓ Done (2 rows) |
| 3 | Switch to all-mpnet-base-v2 (768dim) | ✓ Done |
| 4 | Calculate hybrid scores | ✓ Done |

### Changes Made

1. **Column Added:**
   - `ALTER TABLE memories ADD COLUMN hybrid_score real`

2. **Importance Updated:**
   - `UPDATE memories SET importance = 8 WHERE project = 'Roger-core'`

3. **Embedding Model Upgraded:**
   - Old: all-MiniLM-L6-v2 (384dim)
   - New: all-mpnet-base-v2 (768dim)
   - All 8 memories re-embedded

4. **Hybrid Scores Calculated:**
   - Formula: 0.5×similarity + 0.3×importance + 0.2×recency

---

## Final Audit

### Schema
| Column | Type |
|--------|------|
| id | uuid |
| content | text |
| embedding | vector(768) |
| memory_type | text |
| tags | array |
| importance | double precision |
| project | text |
| sensitivity | text |
| created_at | timestamp |
| created_at_ts | bigint |
| hybrid_score | real |

### Memory Distribution

| Importance | Count |
|------------|-------|
| 8.0 (Roger-core, personal) | 3 |
| 5.0 (general) | 5 |

### Top by Hybrid Score

| memory_type | importance | hybrid_score | project |
|-------------|------------|--------------|---------|
| procedure | 8.0 | 0.690 | Roger-core |
| fact | 8.0 | 0.690 | personal |
| instruction | 8.0 | 0.690 | Roger-core |
| general | 5.0 | 0.600 | general |
| general | 5.0 | 0.599 | general |
| general | 5.0 | 0.599 | general |
| general | 5.0 | 0.599 | general |
| general | 5.0 | 0.599 | general |

---

## VERDICT: ✓ HEALTHY

| Check | Status |
|-------|--------|
| Total memories | 8 |
| Embedding dimensions | 768 |
| Importance distribution | ✓ (3×8, 5×5) |
| Hybrid scores | ✓ Calculated |
| Vector search | ✓ Working |

**Fixed Issues:**
- ✓ Embedding model upgraded to 768dim
- ✓ Hybrid_score column added
- ✓ Importance values corrected
- ✓ Hybrid scoring implemented
