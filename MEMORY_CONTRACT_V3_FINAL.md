# Memory Contract v3 - Final

**Date:** March 10, 2026  
**Status:** Current - Final Version

---

## Overview

Memory Contract v3 combines Lossless Claw + simplified Memory Contract v2.

---

## What Does What

| System | Responsibility |
|--------|----------------|
| **Lossless Claw** | Auto-manages conversation context (chat) |
| **Memory Contract v3** | Explicit decision memory (manual writes) |

---

## How They Work Together

### Lossless Claw (Handles Chat)

- Automatically summarizes old messages into DAG
- Keeps last 32 messages fresh
- Searchable via `lcm_grep`
- Prevents token bleed

### Memory Contract (Handles Decisions)

- Manual writes when YOU make decisions
- NOT chat - just decisions and outcomes
- Stored in `memory/YYYY-MM-DD.md`

---

## Usage

### For Chat/Conversation
```bash
# Search past conversations
lcm_grep pattern="deployment error"

# Get details of a summary
lcm_describe id="abc123"
```

### For Decisions (Manual)
```python
# When you make a decision, write to memory
# File: memory/2026-03-10.md

## Decision: Deployed to production
Outcome: SUCCESS
Context: Updated draft board UI
```

---

## FAQ

### Q: Should I still manually write to memory?
**A:** YES - Write decisions, not chat. Lossless Claw handles chat.

### Q: Should I use lcm_grep?
**A:** YES - Faster than reading files for chat retrieval.

### Q: What's the difference between v1, v2, v3?
| v1 | v2 | v3 |
|----|----|----|
| Crons (5 min) | No crons | No crons |
| Session logs | memory/*.md only | Lossless Claw |
| Token bleed | Fixed | Fixed |
| Manual writes | Manual | Manual |

### Q: Do I need pre/post hooks?
**A:** Optional - Memory Contract is awareness, not enforcement. Write decisions manually when you make them.

---

## Summary

- **Lossless Claw** = Chat context (auto, searchable)
- **Memory Contract v3** = Decisions (manual writes)

They're complementary. Use both.

---

*Updated March 10, 2026 - Final version with Lossless Claw integration*
