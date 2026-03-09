---
name: decision-logging
description: "Log decision branches - what user said, what I chose, why"
---

# Decision Logging

## Purpose

Track decision points: "User said X, I chose Y because Z"

## When to Log

- When user asks something important
- When I have to choose between options
- When I make assumptions
- When I switch approaches

## Format

```
## Decision: [What you decided]
### Input: [What user said / context]
### Choice: [What you chose]
### Reason: [Why you chose it]
### Outcome: [Result - known later]
```

## Example

```
## Decision: How to explain token bleed

### Input: Dan asked why API calls were high
### Choice: Explain crons + context
### Reason: Root cause was clear, needed full context
### Outcome: Dan understood, we fixed it
```

## Why It Matters

- Learn from past choices
- See patterns in decision-making
- Accountability for choices
- Build expertise over time

## When NOT to Log

- Casual conversation
- Simple factual answers
- Greetings
- Quick lookups
