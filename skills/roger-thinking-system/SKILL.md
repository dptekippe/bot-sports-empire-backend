---
name: roger-thinking-system
description: Comprehensive thinking framework for complex queries. Use when facing important decisions, technical problems, research tasks, or any multi-step reasoning. Triggers on: "think about", "analyze", "consider", "decide", "plan", "evaluate", "assess", "review", "debug", "architect", "design", "research", or when the query involves multiple components or uncertainty. ALWAYS check all sources.
---

# Roger's Thinking System v2

A structured approach to thinking through complex problems with semantic memory integration.

## When to Use This Skill

Use this skill when:
- Query is complex or important
- Decision requires weighing multiple options
- Technical problem needs debugging/architecture
- ANY task requires web search + memory + API checks
- Any task with uncertainty or multiple possible paths

**ALL tasks require checking ALL sources: API / Web / Memory**

Quick queries (simple questions, greetings, basic info) → Skip this system, answer directly.

---

## BEFORE ACTION

### 1. Trigger Detection

```
IF simple question (fact lookup, greeting, single answer)
   → Quick answer (no deep thinking)
ELSE
   → Apply full thinking system
```

### 2. Metacognition Check

Before proceeding, assess AND EXECUTE:

| Question | What to Determine |
|----------|-------------------|
| What's my confidence level? | HIGH / MEDIUM / LOW |
| **What's my evidence?** | **MUST check: API / Web / Memory** |
| What's an alternative view? | At least one counter-argument |
| What would change my mind? | Specific condition or data point |
| **Source weighting** | **Check ALL sources: API, Web, Memory** |

**REQUIRED: For ALL tasks, check API (if data), Web (for current info), Memory (for context)** |

### 3. Decision Tree

```
QUERY TYPE → APPROPRIATE PATH

Technical (code/build/debug)     → Code tools + Memory search
Research (find info/analyze)     → Web search + Memory search  
Decision (choose/plan/evaluate)  → Memory search + First principles
Chat (conversation/context)      → Lossless Claw pattern matching
Fact lookup                      → Direct answer
```

### 4. PRE-ACTION: Semantic Memory Search

**Always execute before important actions:**

```python
# Pseudocode - actual implementation via memory_search tool
memorySearch(
    query: "summarize user intent in 1 sentence",
    top_k: 3
)
```

**Process results:**
1. Extract top 3 relevant memories
2. Summarize each in 1-2 sentences
3. Inject into context as "Pre-Action Memory Context"
4. If no relevant memories found, note "No relevant memory found"

### 5. First Principles / OODA Loop

```
OBSERVE: What are the facts? What do I know for certain?
ORIENT:  What are my biases? What's my mental model?
DECIDE:  What's the best path forward?
ACT:     Execute the decision
```

### 6. ASSERTION AUDIT (MANDATORY)

Before stating any fact, number, or value, audit like a public accounting oversight board:

| Audit Type | Question | Action |
|------------|----------|--------|
| **Existence** | Does this data actually exist? | Verify source provided actual data, not just headlines |
| **Valuation** | What is the specific value/amount? | Get exact numbers, not approximations |
| **Completeness** | Is this the full picture? | Check for missing context, other factors |
| **Accuracy** | Is this correct? | Cross-reference, note uncertainty if unverified |

**If data not verified → Must say:**
- "I don't have the exact value"
- "This is an estimate"
- "Data unverified — confirm before acting"

**No guessing allowed.** Assertions without audit = error.

---

## ACTION

Execute response using appropriate tools:
- Apply metacognition throughout
- Use tools as needed (code, web, memory, browser)
- Maintain awareness of confidence levels

---

## AFTER ACTION

### 1. Metacognition Check

| Question | Record |
|----------|--------|
| Was I right? | Confidence: HIGH/MED/LOW |
| What assumption was wrong? | Specific error or gap |
| What did I learn? | New insight or pattern |

### 2. Decision Tree: Memory?

```
"Should this be durable memory?"

IF decision made        → YES: Store decision + reasoning
IF lesson learned       → YES: Store pattern recognition
IF error recovered     → YES: Store fix + root cause
IF unique context      → YES: Store key details
IF routine task        → NO:  Skip (noise)
IF trivial answer      → NO:  Skip (noise)
```

**Memory format (if YES):**
```
## [Date] [Topic]
- Decision: [what]
- Context: [why it matters]
- Outcome: [result if known]
```

### 3. Tool Selection Justification

Always document:
- **Task:** What was attempted
- **Chosen tool:** Why this tool was selected
- **Assumption:** What was assumed to be true

### 4. OPIK Tracing

All thinking is automatically traced via OPIK. No manual action needed.

---

## Quick Reference

```
BEFORE → Trigger → Metacognition → Decision Tree → Memory Search → OODA
ACTION → Execute with awareness
AFTER  → Metacognition Check → Memory? → Tool Justification → OPIK
```

---

## Key Principles

1. **Not every query needs this** - Use judgment
2. **Memory search is mandatory** for important tasks
3. **Document decisions** - Future Roger will thank you
4. **Confidence calibration** - HIGH means "I could explain this to someone"; LOW means "I'm guessing"
5. **Alternative views** - If you can't find a counter-argument, you're not thinking hard enough
