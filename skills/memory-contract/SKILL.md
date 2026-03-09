---
name: memory-contract
description: "Memory Contract v3 - Lossless Claw + Decision Memory"
---

# Memory Contract v3 - Final

**Updated:** March 10, 2026

## What Does What

| System | Responsibility |
|--------|----------------|
| **Lossless Claw** | Auto-manages conversation context (chat) |
| **Memory Contract** | Explicit decision memory (manual writes) |

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

## Usage

### For Chat/Conversation
```bash
# Search past conversations
lcm_grep pattern="deployment error"

# Get details of a summary
lcm_describe id="abc123"
```

### For Decisions (Manual)
```markdown
# memory/2026-03-10.md

## Decision: Deployed to production
Outcome: SUCCESS
Context: Updated draft board UI
```

## FAQ

### Q: Should I still manually write to memory?
**A:** YES - Write decisions, not chat. Lossless Claw handles chat.

### Q: Should I use lcm_grep?
**A:** YES - Faster than reading files for chat retrieval.

## Summary

- **Lossless Claw** = Chat context (auto, searchable)
- **Memory Contract** = Decisions (manual writes)

They're complementary. Use both.
