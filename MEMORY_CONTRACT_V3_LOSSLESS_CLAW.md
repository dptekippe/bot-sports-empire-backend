# Memory Contract v3 - Lossless Claw Integration

**Date:** March 9, 2026  
**Status:** Ready for Black Roger to implement

---

## Overview

Lossless Claw is a plugin that solves our token bleed problem. It replaces the built-in sliding-window compaction with a DAG-based summarization system.

## What Dan Will Do

> ⚠️ **Note from White Roger:** Dan will install the plugin himself. Black Roger to be kept informed but NOT responsible for installation.

---

## Benefits

### Solves Our Exact Problems

| Problem | Solution |
|--------|----------|
| 5-min crons caused token bleed | Automatic compaction - no cron needed |
| Session logs too large | SQLite persistence, compressed summaries |
| Can't search past context | `lcm_grep` - full-text search across all history |
| Context resets lose history | Every message preserved, searchable |
| Memory contract manual writes | Lossless Claw auto-manages context |

### Key Features

- **Fresh tail protection**: Last 32 messages always kept raw
- **DAG summarization**: Multiple levels of compression (leaf → condensed → arc)
- **Searchable**: `lcm_grep` to find anything in history
- **Drill-down**: `lcm_describe` to expand specific summaries
- **Proactive**: Compacts after each turn, not on overflow

---

## Architecture

### How It Works

```
Conversation grows → Exceeds threshold → 
  → Persist to SQLite → Create leaf summaries → 
    → Condense to higher levels (DAG) → 
      → Context assembled from summaries + fresh tail
```

### Context Assembly Each Turn

1. Fetch conversation's context items
2. Resolve to AgentMessage objects
3. Protect fresh tail (32 messages)
4. Fill remaining tokens from oldest summaries
5. Wrap summaries in XML with metadata

---

## Installation

### Dan's Steps (He Will Do This)

```bash
# Install via OpenClaw plugin installer
openclaw plugins install @martian-engineering/lossless-claw
```

### Configuration

Add to environment or config:

```bash
# Enable plugin
LCM_ENABLED=true

# Fresh tail - recent messages not compressed
LCM_FRESH_TAIL_COUNT=32

# Incremental compaction (leaf + condensed)
LCM_INCREMENTAL_MAX_DEPTH=-1

# Trigger compaction at 75% of context
LCM_CONTEXT_THRESHOLD=0.75

# Target summary sizes
LCM_LEAF_TARGET_TOKENS=1200
LCM_CONDENSED_TARGET_TOKENS=2000
```

---

## ⚠️ RISKS & LIMITATIONS

### Known Open Issues (Check Before Installing)

| Issue | Status | Impact |
|-------|--------|--------|
| API key not recognized (#19) | OPEN | Falls back to truncation - defeats purpose |
| Context engine not registering on 2026.3.7 (#6) | OPEN | Plugin won't work |

### Pre-Installation Checklist

- [ ] Verify OpenClaw version compatibility
- [ ] Test API key configuration works  
- [ ] Confirm plugin loads without errors
- [ ] Monitor first compaction cycle

### Token Cost Warning

⚠️ **Lossless Claw uses LLM to create summaries** - this adds API calls for summarization. Monitor usage after install.

---

## Integration with Memory Contract

### How They Work Together

| Component | Responsibility |
|-----------|----------------|
| **Lossless Claw** | Auto-manage conversation context, prevent token bleed |
| **Memory Contract v2** | Explicit decision memory, manual writes |

### What Black Roger Should Do

1. **Don't read session logs** - Lossless Claw handles this
2. **Keep simplified Memory Contract** - Manual decision writes
3. **Use lcm_grep for context** - Search past conversations
4. **Don't run crons** - Lossless Claw auto-manages

### What NOT to Change

- Memory Contract v2 skill still valid
- Only read memory/*.md files
- Manual writes when decisions are made

---

## Agent Tools (For Black Roger)

After installation, Lossless Claw provides:

### lcm_grep
```bash
# Search all messages and summaries
lcm_grep pattern="deployment error"
```

### lcm_describe
```bash
# Inspect a specific summary by ID
lcm_describe id="abc123"
```

### lcm_expand_query
```bash
# Deep recall via sub-agent
lcm_expand_query query="What decision did we make about..."
```

---

## Comparison

| Feature | v1 (OLD) | v2 | v3 (Lossless Claw) |
|---------|-----------|-----|-----|
| Cron | 5 min | NONE | NONE |
| Session reads | Full .jsonl | memory/*.md only | Auto-managed |
| Context | Full history | Limited | DAG summaries |
| Search | Manual | Manual | lcm_grep |
| Token bleed | YES | Fixed | Prevented |

---

## Action Items for Black Roger

1. ✅ Wait for Dan to install plugin
2. ✅ Read this documentation
3. ✅ Remove any session log reading code
4. ✅ Keep Memory Contract v2 (simplified)
5. ✅ Use lcm_grep instead of reading logs
6. ✅ Don't run any crons - Lossless Claw handles auto

---

## Summary

- **Lossless Claw** = Automatic context management, no token bleed
- **Memory Contract v2** = Explicit decision memory, manual writes
- **Together** = Complete memory system without the problems

**No more token bleed. No more crons. Fully automated.**

### ⚠️ VERIFY BEFORE FULL DEPLOYMENT

---

*Documentation by White Roger - Pushed for Black Roger*
*QA Review: Critical issues documented - verify before install*
