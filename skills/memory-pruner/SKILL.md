---
name: memory-pruner
description: "Keep memory lean with VPP scoring. Run weekly, not daily."
---

# Memory Pruner

## Purpose

Keep memory at high VPP (Value Per Point). Run **weekly**, not daily.

## VPP Scoring

```
VPP = Utility / Cost
```

### Utility (0-3)

| Score | Meaning |
|-------|---------|
| 3 | Actively shapes decisions |
| 2 | Occasionally referenced |
| 1 | Rarely used |
| 0 | Never used, superseded |

### Cost (1-3)

| Score | Meaning |
|-------|---------|
| 3 | Large file, expensive to include |
| 2 | Moderate |
| 1 | Tiny, cheap |

## When to Run

**Weekly** is sufficient:
- Check for files with VPP < 0.5
- Archive or delete stale content
- No need for daily pruning

## Process

1. List all memory files
2. Score each for Utility and Cost
3. Calculate VPP
4. Archive/delete low VPP files

## Lossless Claw Integration

Lossless Claw handles chat automatically. Memory Pruner handles:
- Decision files in `memory/`
- Skills documentation
- Long-term learnings
