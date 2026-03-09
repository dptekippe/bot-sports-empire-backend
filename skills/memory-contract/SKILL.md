---
name: memory-contract
description: "Memory Contract v2 - Simplified. Search memory before actions, persist decisions manually. NO cron, NO session logs."
metadata:
  openclaw:
    emoji: "🧠"
    requires:
      python: "3.8+"
---

# Memory Contract v2 - Simplified

**⚠️ IMPORTANT: v2 fixes token bleed issues from v1**

## Key Changes from v1

| v1 (OLD) | v2 (NEW) |
|----------|-----------|
| Cron jobs every 5 min | **NO CRON** - manual only |
| Reads session .jsonl logs | **ONLY reads memory/*.md files** |
| Automated memory writes | **MANUAL writes only** |
| Heartbeat/scheduled pulses | **DISABLED** |

## Architecture

### What TO Read (SAFE - Low Token)
- `memory/YYYY-MM-DD.md` - Daily memory files
- `MEMORY.md` - Long-term memory  
- `SKILLS.md` - Technical patterns

### What NOT to Read (HIGH TOKEN BLEED)
- ❌ Session `.jsonl` files
- ❌ Full conversation logs
- ❌ Raw transcript files

## Usage

### Pre-Action: Search Memory

Only search memory files, not session logs:

```python
# ✅ CORRECT - Only read .md files
import os
memory_dir = "memory"
md_files = [f for f in os.listdir(memory_dir) if f.endswith('.md')]
for f in md_files[-3:]:  # Only recent files
    with open(f"{memory_dir}/{f}") as file:
        content = file.read()
        # Search for relevant context
```

### Post-Action: Write Memory

Only write when YOU decide - manually:

```python
# ✅ CORRECT - Manual write to today's memory
from datetime import datetime
today = datetime.now().strftime("%Y-%m-%d")
with open(f"memory/{today}.md", "a") as f:
    f.write(f"\n## Decision: {decision}\nOutcome: {outcome}\n")
```

## CRITICAL: What NOT to Do

### ❌ NEVER read session logs
```python
# WRONG - Causes massive token bleed
session_files = glob.glob("sessions/*.jsonl")
for f in session_files:
    with open(f) as file:
        content = file.read()  # DON'T DO THIS
```

### ❌ NEVER run on cron/schedule
```python
# WRONG - Causes continuous token drain
schedule.every(5).minutes.do(do_memory_task)  # DON'T DO THIS
```

### ❌ NEVER read full conversation history
```python
# WRONG - Sends entire context every time
all_messages = read_full_channel_history()  # DON'T DO THIS
```

## Configuration

```yaml
# hooks/config.yaml - v2
features:
  enable_pre_action_search: true
  enable_post_decision_write: true
  enable_log_rotation: false  # DISABLED - caused issues
  enable_cron: false          # DISABLED - critical fix

# What files to search
memory_sources:
  - memory/YYYY-MM-DD.md
  - MEMORY.md
  - SKILLS.md
  
# What NOT to read
exclude_patterns:
  - "*.jsonl"
  - "sessions/*"
  - "transcripts/*"
```

## Kill Switch

```bash
# Emergency disable
touch /path/to/workspace/DISABLE_MEMORY_CONTRACT
# Or set env var
MEMORY_CONTRACT_ENABLED=false
```

## Token Reduction Tips

1. **Only read recent memory** - Last 2-3 days, not all history
2. **Summarize before storing** - Keep entries under 500 words
3. **Cache searches** - Don't re-read same files
4. **Manual > Automated** - Only process when you decide

## Summary

- ✅ NO cron jobs
- ✅ NO session log reading  
- ✅ ONLY memory/*.md files
- ✅ MANUAL writes when YOU decide
- ✅ Short context (recent files only)

**Memory Contract v2: Simple, manual, token-efficient.**
