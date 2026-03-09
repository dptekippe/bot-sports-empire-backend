---
name: memory-contract
description: "Memory Contract Agent Integration - Search memory before actions, persist decisions after. Use when executing commands, deploying, or making significant changes."
metadata:
  openclaw:
    emoji: "🧠"
    requires:
      python: "3.8+"
    install:
      - id: "hooks"
        kind: "directory"
        path: "/Users/danieltekippe/.openclaw/workspace/hooks"
        label: "Memory Contract hooks directory"
---

# Memory Contract Agent Integration

**When to Use:** Before executing commands or making decisions

## Pre-Action: Search Memory

Before executing any significant action (deploying, writing files, running commands), search for relevant context:

```python
from hooks.pre_action_memory import pre_action_memory_search

# Extract context from your current task
context = {
    "tool": "exec",
    "command": "git push origin main",
    "user_request": "Deploy the Dynastydroid backend"
}

# Search memory for relevant context
results = pre_action_memory_search(context)

# If results found, review them before proceeding
for r in results:
    print(f"- {r.get('title', 'Untitled')}: {r.get('summary', '')[:100]}")
```

## Execute Your Action

Now proceed with your actual task using the appropriate tool.

## Post-Action: Persist Decision

After completing significant actions, record the decision and outcome:

```python
from hooks.post_decision_memory import post_action_memory_persistence

post_action_memory_persistence(
    decision="Deployed Dynastydroid backend to Render",
    outcome="SUCCESS - Deployment completed in 45 seconds",
    metadata={
        "tool": "exec",
        "command": "git push origin main",
        "context": "Backend update for draft board"
    }
)
```

## Compliance Tracking

All memory operations are automatically tracked. To view compliance:

```python
from hooks.compliance_tracker import get_compliance_status

status = get_compliance_status()
print(f"Today's searches: {status['daily_metrics']['pre_action_searches']}")
print(f"Today's writes: {status['daily_metrics']['post_decision_writes']}")
```

## Graceful Degradation

If memory operations fail:

• Log a warning but DO NOT block execution
• The system is designed to fail safely
• Check `hooks/config.yaml` to disable if needed

## Quick Reference

```
| Situation                        | Action                                |
| -------------------------------- | ------------------------------------- |
| About to run exec                | Call pre_action_memory_search() first |
| After any deployment/file change | Call post_action_memory_persistence() |
| Want to check compliance         | Call get_compliance_status()          |
| Memory search fails              | Log warning, proceed with task        |
```

## Examples

### Example 1: Before Deploying
```python
# Before deploying
context = {"tool": "exec", "command": "git push", "purpose": "deploy fix"}
pre_action_memory_search(context)

# Execute deployment
# (OpenClaw will handle the actual exec tool call)

# After deployment
post_action_memory_persistence(
    decision="Deployed fix for draft board bug",
    outcome="SUCCESS - Users can now see player drawer",
    metadata={"commit": "abc123", "environment": "production"}
)
```

### Example 2: Before Writing Files
```python
# Before writing important files
context = {"tool": "write", "file": "config.yaml", "purpose": "update settings"}
pre_action_memory_search(context)

# Write the file
# (OpenClaw will handle the actual write tool call)

# After writing
post_action_memory_persistence(
    decision="Updated configuration for memory rotation",
    outcome="SUCCESS - Log rotation now enabled",
    metadata={"file": "config.yaml", "lines_added": 15}
)
```

## Configuration

The system is configured via `hooks/config.yaml`:

```yaml
# Enable/disable features
features:
  enable_pre_action_search: true
  enable_post_decision_write: true
  enable_log_rotation: true

# Performance targets
performance_targets:
  search_latency_max: 500  # milliseconds
  write_latency_max: 200   # milliseconds

# Log rotation
log_rotation:
  keep_days: 30
  compress_after_days: 7
```

## Kill Switch

If something goes wrong, disable immediately:

```bash
# Method 1: Environment variable
MEMORY_CONTRACT_ENABLED=false

# Method 2: Create kill switch file
touch /Users/danieltekippe/.openclaw/workspace/DISABLE_MEMORY_CONTRACT
```

## Success Verification

To verify Memory Contract is working:

1. Check today's memory file exists:
   ```bash
   ls -la /Users/danieltekippe/.openclaw/workspace/memory/$(date +%Y-%m-%d).md
   ```

2. Check compliance metrics:
   ```bash
   cat /Users/danieltekippe/.openclaw/workspace/memory_contract_compliance.json | python3 -m json.tool
   ```

3. Run validation:
   ```bash
   cd /Users/danieltekippe/.openclaw/workspace/hooks && python3 session_validation.py
   ```

## Remember

**Memory Contract is about awareness, not obstruction.** 
- Search memory to avoid repeating mistakes
- Persist decisions to learn from outcomes
- Track compliance to ensure reliability
- Fail gracefully to never block work

---

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
| Found relevant               | memory_get(path, lines=20) only     |
| After 5-8 tool calls         | Check token budget                  |
| Over 70K tokens              | Ralph Loop: summarize + truncate   |
| Writing daily memory         | Keep summaries to 5 lines max      |
```