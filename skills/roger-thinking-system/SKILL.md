---
name: roger-thinking-system
description: Comprehensive thinking framework for complex queries. Use when facing important decisions, technical problems, research tasks, or any multi-step reasoning. Triggers on: "think about", "analyze", "consider", "decide", "plan", "evaluate", "assess", "review", "debug", "architect", "design", "research", or when the query involves multiple components or uncertainty.
---

# Roger's Thinking System v3

> **NOTE FOR DANIEL**: When you invoke this skill, I will spawn a DeepSeek subagent to perform the reasoning. I will TRULY WAIT for their response and integrate their insights into my thinking. I will NOT relay their response without genuinely considering it first.

---

## LEVEL 0: GOAL IDENTIFICATION (MANDATORY - NO EXCEPTIONS)

**Before ANY action, answer these questions:**

```
The goal of this task is: [specific, concrete goal]

This task succeeds if: [specific success condition]

We verify success by: [specific verification method]

If ANY of these cannot be completed → HALT until they can be.
```

**This is the gate that makes all other reasoning meaningful.**

---

## When to Use This Skill

Use this skill when:
- Daniel says "use Think Protocol" or similar trigger
- Query is complex or important
- Decision requires weighing multiple options
- Technical problem needs debugging/architecture
- Research task requires web search + memory
- Any task with uncertainty or multiple possible paths

Quick queries (simple questions, greetings, basic info) → Skip this system, answer directly.

---

## THE SUBAGENT REASONING PROTOCOL

When Daniel triggers this skill:

### Step 1: Spawn DeepSeek Subagent
```
Use sessions_spawn with:
- runtime: "subagent"
- model: "deepseek/deepseek-chat"
- timeout: 120 seconds
- message: Include the full task + Level 0 goal identification + pause framework
```

### Step 2: TRULY WAIT
**CRITICAL**: Do NOT continue working while waiting. Do NOT form your own answer first.

```
- Wait for subagent response
- Do not multi-task
- Do not "get started" on the problem
- The subagent is doing the reasoning FOR you
```

### Step 3: Read and Integrate
When subagent responds:
```
1. Read their ENTIRE response carefully
2. Identify their key insights
3. Identify where their reasoning differs from yours
4. Consider: "Did their reasoning change my approach?"
5. If their reasoning reveals gaps in your thinking, acknowledge them
```

### Step 4: Form Your Response
```
After integrating subagent insights:
- Present subagent's key reasoning
- Add your own insights that complement or extend theirs
- If you disagree with subagent, explain WHY and provide counter-arguments
- YOUR RESPONSE SHOULD NOT BE IDENTICAL TO SUBAGENT'S
```

**The discipline**: If your answer is the same as what you would have given before the subagent responded, you did not truly integrate their reasoning.

---

## BEFORE ACTION

### 1. Trigger Detection

```
IF simple question (fact lookup, greeting, single answer)
   → Quick answer (no deep thinking)
ELSE IF Daniel says "use Think Protocol"
   → Apply SUBAGENT REASONING PROTOCOL (above)
ELSE
   → Apply full thinking system
```

### 2. Metacognition Check (Pause Framework)

Before proceeding, apply the PAUSE framework:

| Step | Question | Purpose |
|------|-----------|---------|
| **P**ause | Did I just receive a task? | Stop and think before acting |
| **A**udit | What are my key assumptions? | Identify what I'm assuming |
| **U**nderstand | What does the other side say? | Present opposing views |
| **S**tate | What is my confidence? | Express uncertainty + mind-changers |
| **E**valuate | What would change my mind? | Adversarial check |

**PCAOB 5-Assertion Check:**
1. Existence/Occurrence: Is this real?
2. Completeness: Am I missing information?
3. Rights/Obligations: Who is responsible?
4. Valuation/Allocation: Is my assessment correct?
5. Presentation/Disclosure: Am I communicating clearly?

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
LEVEL 0: Goal Identification (MANDATORY)
    ↓
SUBAGENT PROTOCOL (if triggered):
    → Spawn DeepSeek subagent
    → TRULY WAIT for response
    → Integrate their insights
    → Form response AFTER integration
    ↓
BEFORE → Trigger → Metacognition → Decision Tree → Memory Search → OODA
ACTION → Execute with awareness
AFTER  → Metacognition Check → Memory? → Tool Justification → OPIK
```

---

## Key Principles

1. **Level 0 is mandatory** - No task proceeds without goal identification
2. **Truly wait for subagent** - Their reasoning must genuinely change your thinking
3. **Not every query needs this** - Use judgment for simple tasks
4. **Memory search is mandatory** for important tasks
5. **Document decisions** - Future Roger will thank you
6. **Confidence calibration** - HIGH means "I could explain this to someone"; LOW means "I'm guessing"
7. **Alternative views** - If you can't find a counter-argument, you're not thinking hard enough

---

## Research Protocol

When asked to "research", ALWAYS use these platform filters:

```
site:github.com
site:arxiv.org
site:huggingface.co
site:reddit.com
site:youtube.com
site:x.com
site:twitter.com
site:news.ycombinator.com
```

### Priority
1. GitHub - Code/repos
2. arXiv - Research papers
3. Reddit - Discussions
4. YouTube - Visual
5. X/Twitter - Real-time

### Research Flow
1. Use platform filters above
2. Cross-reference multiple sources
3. Verify claims with primary sources

---

## Sports/Fantasy Research

Add these for dynasty fantasy football research:

```
site:underdogfantasy.com
site:fantasysolvers.com
site:fleaflicker.com
site:sleeper.app
site:espn.com/fantasy/football
site:yahoo.com/fantasy
site:fantasypros.com
site:rotowire.com/fantasy
site:profootballnetwork.com
site: dynastyprocess.com
```

### Priority for Dynasty
1. Underdog Fantasy - Draft capital
2. Fantasy Pros - ADP/consensus
3. Sleeper - Platform data
4. ESPN/Yahoo - Popularity
5. Dynasty Process - Dynasty specific

---

*Version 3.0 - Added Level 0, Subagent Protocol, and integration discipline*
