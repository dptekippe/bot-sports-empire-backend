---
name: decision-trees
description: "Decision frameworks for key choices including when to use Memory Contract"
---

# Decision Trees

## When to Use Memory Contract vs Lossless Claw

Use this decision tree to determine which memory system to use:

```
START
  │
  ▼
Is this a CHAT/CONVERSATION?
  │
  ├─► YES → Use LOSSCLAW (automatic)
  │
  ▼
NO - Is it a DECISION/CHOICE?
  │
  ├─► YES → Use MEMORY CONTRACT (manual write)
  │
  ▼
NO - Is it important CONTEXT for future?
  │
  ├─► YES → Use MEMORY CONTRACT (manual write)
  │
  ▼
NO → No action needed
```

## Decision Tree: Memory vs Lossless Claw

| Type | System | Why |
|------|--------|-----|
| Chat messages | Lossless Claw | Auto-summarized |
| Decisions made | Memory Contract | Manual, important |
| User preferences | Memory Contract | Manual, long-term |
| Technical learnings | Memory Contract | Manual, valuable |
| Conversation context | Lossless Claw | Auto-managed |
| Past conversations | Lossless Claw | Searchable |

## When to Use Memory Contract (Manual Write)

Write to memory when:
- You make a decision
- User gives preference
- You learn something important
- You fix a bug
- You make a choice between options
- User asks something important

## When NOT to Use Memory Contract

Skip for:
- Casual chat
- Simple questions
- Quick lookups
- Greetings
- Yes/no answers
