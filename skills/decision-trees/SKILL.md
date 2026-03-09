---
name: decision-trees
description: Store and access decision trees for decision-making workflows. Use when creating, updating, or referencing decision trees - the skill ensures Roger knows where to store them and how to organize them.
---

# Decision Trees Storage

## Directory Location

All decision trees must be stored at:
```
~/.openclaw/workspace/memory/decision_trees/
```

## On First Use

If this directory does not exist, create it:
```bash
mkdir -p ~/.openclaw/workspace/memory/decision_trees
```

## When to Use

Per AGENTS.md "Roger's Strategic Mandate": When a task is **ambiguous or high-stakes**, stop and weigh:

- **Cost vs. Accuracy** — Is this worth the time investment?
- **Speed vs. Safety** — Can we ship fast, or do we need to be careful?
- **Originality vs. Consistency** — Should we innovate or follow existing patterns?

## The Tool Gap Rule

If the best path requires a tool you don't have (missing `brew install`, API key, etc.), your **Decision** should be to ask Daniel for that specific thing — **not to fake a result**.

## File Organization

- One file per decision tree
- Use descriptive filenames (e.g., `league_creation_flow.md`, `player_draft_strategy.md`)
- Include: context, options considered, criteria weighed, final choice, rationale
