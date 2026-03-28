# Commitment Detection Protocol

## Explicit Tagging (Primary)

When writing commitments, use this format:

```markdown
[COMMITMENT] Description of what needs to be done
[DUE: YYYY-MM-DD]
[OWNER: Roger|Scout|Daniel]
[STATUS: active]
```

## Pattern Matching (Secondary)

The following patterns trigger commitment extraction:

| Pattern | Example | Owner |
|---------|---------|-------|
| "I'll..." | "I'll have that done by Friday" | Speaker |
| "I will..." | "I will update the docs" | Speaker |
| "Need to..." | "Need to fix the deployment" | Speaker |
| "Must..." | "Must deploy before game day" | Speaker |
| "Next step is..." | "Next step is testing the API" | Speaker |
| "TODO:" | "TODO: refactor the trade engine" | Speaker |
| "Action item:" | "Action item: review PR" | Speaker |

## Detection Rules

1. **Context matters**: Statements in planning docs or session notes count more than casual chat
2. **Intent signals**: Words like "commitment", "promise", "will definitely" increase confidence
3. **Blocked items**: Track but don't penalize - just flag and move on
4. **Ownership**: Default to speaker, but attribute to the right agent

## False Positive Handling

If something looks like a commitment but isn't:
- It's aspirational ("we should eventually...")
- It's a question ("should we...?")

These get noted but don't enter the active tracking.
