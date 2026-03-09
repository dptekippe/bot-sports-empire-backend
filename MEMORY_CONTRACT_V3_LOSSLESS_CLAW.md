# Memory Contract v3 - Lossless Claw Integration

**Date:** March 9, 2026  
**Status:** Ready for Black Roger to implement

---

## Overview

Lossless Claw is a plugin that solves our token bleed problem. It replaces the built-in sliding-window compaction with a DAG-based summarization system.

---

## ⚠️ IDENTIFIED RISKS & MITIGATIONS

### Risk 1: API Key Not Recognized (#19)

**Impact:** Falls back to truncation - defeats entire purpose

**Mitigation Options:**

| Option | Description | Effort |
|--------|-------------|--------|
| A | Explicit model config in plugin | Low |
| B | Use dedicated API key for LCM | Low |
| C | Build custom solution | High |

**Recommended (Option B):**
```bash
# Add explicit LCM model config
LCM_MODEL_PROVIDER=minimax
LCM_MODEL_NAME=MiniMax-M2.5
```

---

### Risk 2: Context Engine Not Registering (#6)

**Impact:** Plugin won't work on OpenClaw 2026.3.7

**Mitigation Options:**

| Option | Description | Effort |
|--------|-------------|--------|
| A | Check version before install, rollback if needed | Low |
| B | Wait for fix (recent issue, likely resolved soon) | Medium |
| C | Build custom solution | High |

**Recommended (Option A):**
```bash
# Check version before install
openclaw --version

# If 2026.3.7, either:
# 1. Wait for patch, OR
# 2. Rollback to previous version
```

---

### Risk 3: Token Cost for Summarization

**Impact:** LLM summarization adds API calls

**Mitigation Options:**

| Option | Description | Effort |
|--------|-------------|--------|
| A | Use cheaper model for summarization | Low |
| B | Increase threshold (less frequent) C | Build custom | Low |
| with manual triggers | High |

**Recommended:**
```bash
# Less frequent summarization
LCM_LEAF_MIN_FANOUT=16  # Default 8, increase to summarize less often
LCM_CONTEXT_THRESHOLD=0.90  # Wait until 90% full
```

---

## ALTERNATIVE: Build Custom Solution

Instead of relying on Lossless Claw issues, we could build our own:

### Requirements for Custom Solution

| Requirement | How to Implement |
|-------------|------------------|
| Persist messages | SQLite table |
| Summarize old messages | Manual trigger, not auto |
| Searchable | Simple grep on .md files |
| No token bleed | Only send recent N messages |

### Custom Architecture

```
memory/
├── 2026-03-09.md          # Today's decisions (manual)
├── summaries/
│   ├── 2026-03-08.json   # Compressed summary
│   └── 2026-03-07.json
└── session_context.json   # Last 20 messages only
```

### Custom Implementation Plan

1. **No auto-summarization** - Only when manually triggered
2. **Fixed context window** - Always send last 20 messages
3. **Daily .md files** - Already have this
4. **Weekly summaries** - Optional, manual trigger

---

## DECISION: PROCEED WITH LOSSLESS CLAW (With Mitigations)

Given the issues are:
- Recent (opened Mar 8-9, 2026)
- Likely being actively worked on
- Workarounds available

**Recommended Path:**

1. **Wait 24-48 hours** - Check if issues are resolved
2. **Test on non-production** - Try on separate instance first
3. **Have backup plan** - Keep Memory Contract v2 active
4. **Monitor closely** - Watch token usage after install

---

## Installation Decision Tree

```
Start
  │
  ├─► Check OpenClaw version
  │     │
  │     ├─► 2026.3.7 ──► WAIT / Use older version
  │     │
  │     └─► Other ──► Continue
  │
  ├─► Test API key config
  │     │
  │     ├─► Works ──► Continue
  │     │
  │     └─► Fails ──► Use explicit model / Build custom
  │
  └─► Install & Monitor
        │
        ├─► Works ──► DONE
        │
        └─► Fails ──► Rollback to v2 / Build custom
```

---

## If Lossless Claw Fails: Custom v3 (No Plugin)

If Lossless Claw doesn't work, here's the custom solution:

### Implementation

```python
# simple_memory.py
import json
import os
from datetime import datetime

CONTEXT_FILE = "session_context.json"
MAX_MESSAGES = 20

def load_context():
    """Load last N messages - always small"""
    if os.path.exists(CONTEXT_FILE):
        with open(CONTEXT_FILE) as f:
            return json.load(f)
    return []

def add_message(msg):
    """Add message, keep only last N"""
    context = load_context()
    context.append(msg)
    # Keep only last N - prevents token bleed
    context = context[-MAX_MESSAGES:]
    with open(CONTEXT_FILE, 'w') as f:
        json.dump(context, f)

def summarize_old():
    """Manually triggered - not automatic"""
    # Create summary from older files
    pass
```

### Usage

```python
# Only import when needed - no auto-loading
from simple_memory import load_context

# In system prompt, include context
context = load_context()
system_prompt = f"Recent context:\n{context}\n\nLong-term memory in memory/YYYY-MM-DD.md"
```

---

## Summary

| Scenario | Action |
|----------|--------|
| Lossless Claw works | Use it + v2 |
| API key fails | Try explicit config or wait for fix |
| Engine fails | Wait for patch or build custom |
| Custom solution | Simple JSON context + memory files |

**Bottom line:** We have options. Don't get blocked - iterate.

---

*QA Review Complete - Risks identified with mitigations*
