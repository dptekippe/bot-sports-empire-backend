---
name: self-improvement-loop
description: "Self-improving agent pattern - experiment, evaluate, keep what works"
---

# Self-Improvement Loop

Based on Karpathy's AutoResearch pattern.

## Core Loop

```
1. Modify → 2. Test → 3. Evaluate → 4. Keep/Discard → Repeat
```

## Key Principles

### 1. Fixed Time Budget
- Set a fixed time for each experiment
- Don't let experiments run forever
- Move on if no improvement

### 2. Clear Metric
- Define ONE metric to optimize
- Make it measurable: "Did X improve?"
- Avoid vague goals

### 3. Single Scope
- Only change one thing at a time
- Keep diffs reviewable
- Don't refactor everything at once

### 4. Automatic Evaluation
- Run test → check metric → decide
- No human intervention needed
- Log everything

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

## Example

**Goal:** Improve metacognition skill

```
- Change: Add confidence scale
- Test: Try on 5 questions
- Metric: Expresses confidence %
- Result: 3/5 → keep
```

## Anti-Patterns

- Changing multiple things at once
- No clear metric
- Running experiments too long
- Not logging results

## Remember

**Your first attempt is rarely your best. Iterate.**
