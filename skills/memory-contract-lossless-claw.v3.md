# Memory Contract + Lossless Claw Integration
## Version 3.0 - March 9, 2026

---

## ⚠️ INSTALLATION NOTE (From Dan)

**Dan will install the Lossless Claw plugin himself.** Black Roger is informed and will be kept in the loop once it's running.

---

## What is Lossless Claw?

Lossless Claw is an LCM (Lossless Context Management) plugin for OpenClaw that replaces the default sliding-window compaction with a DAG-based summarization system.

**Key Capabilities:**
- Persists every message to SQLite database
- Summarizes older messages into compact nodes
- Forms a DAG (directed acyclic graph) of summaries
- Provides search tools: `lcm_grep`, `lcm_expand`, `lcm_describe`
- Feels like talking to an agent that never forgets

---

## Benefits for Roger

| Benefit | Impact |
|---------|--------|
| **Never lose context** | No more memory gaps on session reset |
| **Automatic compaction** | No more manual Ralph Loop resets |
| **Searchable history** | `lcm_grep` to find past conversations |
| **DAG structure** | Can drill into summaries to recover detail |
| **75% threshold** | Compacts before context exhaustion |

### Configuration Used
```yaml
LCM_FRESH_TAIL_COUNT=32      # Last 32 messages stay raw
LCM_INCREMENTAL_MAX_DEPTH=-1 # Unlimited condensation
LCM_CONTEXT_THRESHOLD=0.75   # Compact at 75% context
```

---

## Integration: Two-Layer Memory System

### Layer 1: Lossless Claw (Low-Level)
- **Job:** Preserve every message, handle context compaction
- **Storage:** SQLite at `~/.openclaw/lcm.db`
- **Tools:** `lcm_grep`, `lcm_expand`, `lcm_describe`

### Layer 2: Memory Contract (High-Level)
- **Job:** Intentional memory behavior, decision logging
- **Storage:** Markdown files in `memory/` and `MEMORY.md`
- **Protocol:** SEARCH → SOLVE → PERSIST → SYNC

### How They Work Together

```
User Message
    ↓
[Lossless Claw] → Save to SQLite, manage context window
    ↓
[Memory Contract] → Search memory, persist decisions
    ↓
Response
    ↓
[Lossless Claw] → Compacts if needed, maintains DAG
```

---

## Updated Memory Protocol

### Before (v2 - Fragile)
```
1. Session starts → Load memory files (token heavy)
2. Do work
3. Cron saves memory (often fails)
4. Context exhausts → Reset → Memory gap
```

### After (v3 - With Lossless Claw)
```
1. Session starts → Lossless Claw restores context automatically
2. Do work → Memory Contract searches/persists as needed
3. Lossless Claw handles compaction in background
4. Session resets → Context restored from SQLite
```

---

## Tools Reference

### Lossless Claw Tools
```bash
lcm_grep "deployment patterns"    # Search past conversations
lcm_expand <summary_id>           # Drill into summary to recover detail
lcm_describe                      # Show DAG structure
```

### Memory Contract Tools (Still Used)
```bash
memory_search(query)              # Find relevant context
memory_get(path, lines=20)        # Get snippet only
post_action_memory_persistence()  # Log decisions
```

---

## What Changes for Black Roger

1. **No more manual memory loading** - Lossless Claw restores context
2. **No more Ralph Loop anxiety** - Auto-compaction handles it
3. **Keep memory-contract discipline** - Search before acting, persist decisions
4. **New tool available:** Use `lcm_grep` for deep history searches

---

## Session Reset Behavior

With `idleMinutes: 10080` (7 days):
- Session stays alive for 7 days of inactivity
- Lossless Claw maintains DAG through resets
- Context restores on wake: summaries + recent messages

---

## Testing Checklist

- [ ] Verify LCM database created: `ls -la ~/.openclaw/lcm.db`
- [ ] Check logs for plugin load: `tail -n 60 ~/.openclaw/logs/gateway.log`
- [ ] Run test message → verify DB counts increase
- [ ] Test `lcm_grep` search
- [ ] Verify memory-contract still works alongside

---

## Summary

Lossless Claw handles **data preservation**. Memory Contract handles **learning and intent**. Together they form a complete memory system:

- **Lossless Claw:** The hard drive (never loses)
- **Memory Contract:** The index (knows what's important)

---

*Document created: March 9, 2026*
*Status: Awaiting plugin installation by Dan*
