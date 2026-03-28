# DynastyDroid Commitments System

## Directory Structure

```
commitments/
├── active/           # Current commitments (one file per commitment)
├── history/          # Completed/archived commitments
├── protocol.md       # Detection rules and tagging format
└── RITUAL.md         # Pre-session review ritual
```

## Tagging Format

**Explicit Tags:**
- `[COMMITMENT]` - Start of a new commitment
- `[DUE: YYYY-MM-DD]` - Optional deadline
- `[OWNER: agent]` - Who owns it (Roger, Scout, Daniel)
- `[STATUS: active|blocked|done]` - Current status
- `[BLOCKED: reason]` - Why blocked (if applicable)

**Pattern Detection:**
- "I'll..." / "I will..." / "I promise..."
- "Need to..." / "Must..." / "Should..."
- "Next step is..." / "Action item:"
- "TODO:" / "FIXME:" (when said by Roger/Daniel)

## File Naming

`active/YYYY-MM-DD_short-description.md`

## Workflow

1. **Detect** → Tag or pattern-match identifies potential commitment
2. **Extract** → Create new file in `active/` with full commitment details
3. **Track** → Update status as work progresses
4. **Review** → Pre-session ritual checks active commitments
5. **Complete** → Move to `history/` with outcome notes
