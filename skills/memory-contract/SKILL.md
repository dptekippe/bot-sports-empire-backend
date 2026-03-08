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