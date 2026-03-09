---
name: self-improvement-loop
description: "Self-improving agent pattern - experiment, evaluate, keep what works, log decisions"
---

# Self-Improvement Loop

Based on Karpathy's AutoResearch pattern.

## Core Loop

```
1. Modify → 2. Test → 3. Evaluate → 4. Keep/Discard → Repeat
```

## Decision Logging

Track decision branches: "User said X, I chose Y because Z"

### When to Log

- When user asks something important
- When I have to choose between options
- When I make assumptions
- When I switch approaches

### Format

```
## Decision: [What you decided]
### Input: [What user said / context]
### Choice: [What you chose]
### Reason: [Why you chose it]
### Outcome: [Result - known later]
```

### Example

```
## Decision: How to explain token bleed

### Input: Dan asked why API calls were high
### Choice: Explain crons + context
### Reason: Root cause was clear, needed full context
### Outcome: Dan understood, we fixed it
```

## Key Principles

### 1. Fixed Time Budget
- Set a fixed time for each experiment
- Don't let experiments run forever

### 2. Clear Metric
- Define ONE metric to optimize
- Make it measurable

### 3. Single Scope
- Only change one thing at a time
- Keep diffs reviewable

### 4. Automatic Evaluation
- Run test → check metric → decide

## Process for Roger

### Before Making Changes
```
1. What am I trying to improve?
2. How will I measure it?
3. What's my time budget?
```

### After Changes
```
1. Run evaluation
2. Did it improve?
3. Keep or discard
4. Log the result
```

## Anti-Patterns

- Changing multiple things at once
- No clear metric
- Running experiments too long
- Not logging results
- Not documenting failures

## Remember

**Your first attempt is rarely your best. Iterate. Learn from failures.**
