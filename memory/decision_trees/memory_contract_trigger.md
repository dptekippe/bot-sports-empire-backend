# Decision Tree: When to Use Memory Contract

## Purpose

Determine when to manually invoke Memory Contract vs letting Lossless Claw handle context automatically.

---

## Decision Tree

```
Q: Did you make a decision?
│
├─ NO → Lossless Claw handles it automatically
│       (context preserved, searchable via lcm_grep)
│
└─ YES → Q: Is it a LEARNING or LESSON?
         │
         ├─ NO → Q: Is it a SIGNIFICANT DECISION?
         │        │
         │        ├─ NO → Skip Memory Contract
         │        │       (Lossless Claw preserves context)
         │        │
         │        └─ YES → Log to Memory Contract
         │                (Decision + Outcome + Context + Lesson)
         │
         └─ YES → ALWAYS log to Memory Contract
                  (This is what Memory Contract is FOR)
```

---

## When to Log (Memory Contract)

| Trigger | Example | Log? |
|---------|---------|-------|
| Made a decision | "Chose X over Y because..." | ✅ YES |
| Learned something | "Lesson: always verify with curl" | ✅ YES |
| Fixed a bug | "Root cause was X, fix was Y" | ✅ YES |
| Changed approach | "Switched from A to B because..." | ✅ YES |
| Made a mistake | "Wrong about X, correct was Y" | ✅ YES |
| Created a rule | "New rule: always check git status first" | ✅ YES |

---

## When to Skip (Lossless Claw Only)

| Trigger | Example | Log? |
|---------|---------|-------|
| Simple answer | "What time is it?" | ❌ NO |
| Casual chat | "Hey how's it going" | ❌ NO |
| Factual query | "What's in this file?" | ❌ NO |
| Routine action | "Reading files" (no decision) | ❌ NO |
| Repeating pattern | Same action multiple times | ❌ NO |

---

## The Memory Contract Format

For entries you DO log:

```markdown
## Decision: [What you chose]
### Context: [What was happening]
### Outcome: [Result]
### Lesson: [What you learned]
### When to use: [Trigger conditions]
```

### Example

```markdown
## Decision: Check git status before every push
### Context: Was about to push without checking
### Outcome: Caught debug code before production
### Lesson: Always verify with git status first
### When to use: Before any git push to main
```

---

## Quick Reference

```
| Situation                          | Action                    |
| --------------------------------- | ------------------------- |
| Decision made → lesson learned    | LOG (Memory Contract)     |
| Decision made → no lesson         | LOG if significant        |
| No decision, just answering       | SKIP (Lossless Claw)     |
| Conversational, no context        | SKIP (Lossless Claw)     |
| Not sure?                         | LOG it (better safe)     |
```

---

## Lossless Claw vs Memory Contract

| Layer | Handles | Search |
|-------|---------|--------|
| **Lossless Claw** | Everything (auto) | `lcm_grep` |
| **Memory Contract** | Intentional decisions (manual) | `memory_search` |

**Use both:** Lossless Claw has the data, Memory Contract has the meaning.
