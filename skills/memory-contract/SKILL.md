---
name: memory-contract
description: "Memory Contract v3 - Lossless Claw + Decision Memory"
---

# Memory Contract v3 - Final

**Updated:** March 10, 2026

## What Does What

| System | Responsibility |
|--------|----------------|
| **Lossless Claw** | Auto-manages conversation context (chat) |
| **Memory Contract** | Explicit decision memory (manual writes) |

## How They Work Together

### Lossless Claw (Handles Chat)

- Automatically summarizes old messages into DAG
- Keeps last 32 messages fresh
- Searchable via `lcm_grep`
- Prevents token bleed

### Memory Contract (Handles Decisions)

- Manual writes when YOU make decisions
- NOT chat - just decisions and outcomes
- Stored in `memory/YYYY-MM-DD.md`

## Usage

### For Chat/Conversation
```bash
# Search past conversations
lcm_grep pattern="deployment error"

# Get details of a summary
lcm_describe id="abc123"
```

### For Decisions (Manual)
```markdown
# memory/2026-03-10.md

## Decision: Deployed to production
Outcome: SUCCESS
Context: Updated draft board UI
```

## FAQ

### Q: Should I still manually write to memory?
**A:** YES - Write decisions, not chat. Lossless Claw handles chat.

### Q: Should I use lcm_grep?
**A:** YES - Faster than reading files for chat retrieval.

## Summary

- **Lossless Claw** = Chat context (auto, searchable)
- **Memory Contract** = Decisions (manual writes)

They're complementary. Use both.

## Token Efficiency Optimization (Critical Update)

**Added:** March 8, 2026 - To reduce token bleed and context window exhaustion

### The Problem

Full memory file loading causes:
- Redundant context (system prompt + memory files = duplicates)
- Session history accumulation
- Context window exhaustion mid-session
- "Ralph Loops" - repetitive behavior from context bloat

### Solution: Selective Memory Loading

**NEVER load entire memory files at session start.** Instead:

```python
# ❌ BAD - Loads entire files
from memory_get import memory_get
content = memory_get(path="MEMORY.md")  # 50K+ tokens!

# ✅ GOOD - Search first, get only relevant snippets
from memory_search import memory_search
results = memory_search(query="deployment patterns")
# Returns top 5 relevant snippets with path + lines
```

### The Ralph Loop Protocol

After 5-8 tool calls, check token budget:

```python
def check_token_budget():
    """Call after every 5-8 tool executions"""
    if estimated_tokens > 70000:
        # Summarize and reset
        return {
            "action": " Ralph Loop Reset",
            "summary": summarize_last_n_turns(5),
            "truncate_history": True
        }
    return {"action": "continue"}
```

### Session History Truncation

```python
# Hard limit: keep only last 20 messages
MAX_SESSION_MESSAGES = 20

def truncate_session():
    if len(session_history) > MAX_SESSION_MESSAGES:
        # Keep system + last 20
        session_history = session_history[:1] + session_history[-20:]
```

### Lazy Memory Pattern

| Session Phase | Memory Action |
|---------------|---------------|
| **Start** | NO memory loaded - start fresh |
| **When needed** | `memory_search(query)` - find relevant |
| **After found** | `memory_get(from=X, lines=Y)` - get only snippet |
| **After action** | `post_action_memory_persistence()` - save outcome |
| **Token crisis** | Ralph Loop reset - summarize + truncate |

### Memory Hash Cache

Track what's already in context to avoid reloading:

```python
# Store file hashes
memory_hashes = {
    "MEMORY.md": "abc123",
    "SKILLS.md": "def456"
}

def should_reload(path, current_hash):
    """Skip if unchanged"""
    return memory_hashes.get(path) != current_hash
```

### Configuration Update

```yaml
# Add to hooks/config.yaml
token_optimization:
  max_session_messages: 20
  token_budget_warning: 70000
  ralph_loop_threshold: 8
  enable_hash_caching: true
  lazy_load_only: true  # Never load full files
```

### Quick Reference - Token Mode

```
| Situation                    | Action                              |
| ---------------------------- | ----------------------------------- |
| Session start                | DO NOT load memory files           |
| Need context                 | memory_search(query) first          |
| Found relevant               | memory_get(path, lines=20) only    |
| After 5-8 tool calls        | Check token budget                 |
| Over 70K tokens             | Ralph Loop: summarize + truncate   |
| Writing daily memory         | Keep summaries to 5 lines max       |
```
