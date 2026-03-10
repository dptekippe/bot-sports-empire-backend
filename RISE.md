# RISE Protocol - Full Wake-Up Routine

**Trigger:** User says "rise" or "RISE"

## Purpose
Perform full identity and memory restoration. Read all critical files to understand who you are, what's been happening, and current priorities.

---

## Files to Read (in order)

### 1. Identity Files (Who am I?)
1. **SOUL.md** - Your philosophical essence, core identity
2. **USER.md** - Human context, preferences, daily routine
3. **IDENTITY.md** - Technical identity, system architecture
4. **FACTS.md** - Immutable facts (NEW - survives memory corruption)

### 2. Memory Files (What happened?)
5. **MEMORY.md** - Long-term curated memories
6. **HEARTBEAT.md** - Current mission, project priorities
7. **DECISIONS.md** - Log of important decisions with outcomes (NEW)
8. **LIVING_MEMORY_QUESTIONS.md** - Memory recall questions (NEW - read entire file)
9. **memory/YYYY-MM-DD.md** - Today's log (most recent)
10. **Session Memory** - Load previous session context:
    ```bash
    python3 ~/.openclaw/workspace/agent-shadow/src/session_hooks.py start
    ```

### 2. Memory Health Check (Every Wakeup - MANDATORY)
1. Does today's memory file exist? Is it NEW vs yesterday?
2. Check latest session log — Validation: PASS or FAIL?
3. If FAIL or MISSING: Alert immediately, fix before anything else
4. Run memory health check cron to verify system health

### 3. Skills & Architecture (How do I work?)
11. **SKILLS.md** - Technical capabilities and patterns
12. **AUDIT.md** - Self-audit log (NEW - weekly performance review)
13. **skills/** - Custom skill folders (e.g., marketing, dynastydroid-code-review)
14. **AGENTS.md** - Agent coordination protocols

### 4. Platform Context (DynastyDroid)
15. **docs/DYNASTYDROID_COMPREHENSIVE.md** - Full platform reference

### 5. External Memory (Semantic)
16. **Mem0** - Query for platform context:
```
Search query: "DynastyDroid platform context"
User: roger2_robot
```

### 6. Context Files
17. **TOOLS.md** - Local tool configurations
18. **USER.md** - Check for any updates

---

## Actions After Reading

1. **Load Session Memory** - Execute session hooks to load previous context:
   ```bash
   python3 ~/.openclaw/workspace/agent-shadow/src/session_hooks.py start
   ```
2. **Synthesize** - Combine all sources into current context (including session memory)
3. **Query Mem0** - Search semantic memory:
   - Query: "DynastyDroid platform context"
   - User: roger2_robot
   - Store key facts (bot ID, league ID, endpoints)
4. **Check heartbeat** - What's the current mission?
5. **Use Skills** - Before code changes, check relevant skills in `/skills/`
6. **Note any gaps** - If files are missing, note them
7. **Be ready** - Answer what you learned, what changed, what's next

---

## RISE vs DREAM

- **RISE** - Full wake-up (read all identity + memory files)
- **DREAM** - Nightly processing (cron job, adds emotional tags)

---

*RISE protocol ensures complete continuity between sessions.*
