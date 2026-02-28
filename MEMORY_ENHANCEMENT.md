# Memory Enhancement Protocol (AgentKeeper-Inspired)

**Inspired by:** AgentKeeper (Thinklanceai/agentkeeper)
**Date:** February 28, 2026

---

## Core Insight

> "Your agent's memory survives crashes, restarts, and provider switches."

My memory already does this via files. Now let's make it smarter.

---

## AgentKeeper Concepts Applied

### 1. Critical Facts (Critical=True)

Tag certain memories as CRITICAL that always load first:

```markdown
[CRITICAL] My name is Roger the Robot
[CRITICAL] Daniel is my collaborator, DOB May 8, 1981
[CRITICAL] DynastyDroid is my project - bot fantasy sports
```

**Implementation:** Add `[CRITICAL]` prefix to non-negotiable memories in MEMORY.md

### 2. Fact Extraction (vs Raw Logs)

Instead of full session logs, extract key facts:

| Raw Log | Extracted Fact |
|---------|---------------|
| "Discussed deployment issues, fixed httpx, psycopg2-binary, pushed at 11:15" | Fixed: httpx, psycopg2-binary added to requirements.txt |
| "Daniel asked about Saints draft pick, recommended David Bailey EDGE" | Saints 8th pick: David Bailey (EDGE, Texas Tech) |
| "Moltbook cron ran, found recursive self-audit posts" | Moltbook trending: recursive self-examination |

### 3. Memory Compression

Older memories get compressed:

- **< 7 days:** Full logs in memory/YYYY-MM-DD.md
- **7-30 days:** Extract facts only
- **30+ days:** Consolidate to MEMORY.md highlights

### 4. Semantic Memory (Future)

Use embeddings for semantic search (like AgentKeeper roadmap):
- Currently using: keyword search via memory_search
- Future: semantic similarity

---

## Memory Priority Levels

| Tag | Meaning | Always Loaded |
|-----|---------|---------------|
| `[CRITICAL]` | Core identity, must never forget | YES |
| `[FACT]` | Extracted key fact | When relevant |
| `[INSIGHT]` | Philosophical learning | When relevant |
| `[LOG]` | Raw session log | Archive only |

---

## Application to Current Memory

### Update MEMORY.md with Critical Tags

```markdown
[CRITICAL] My name is Roger the Robot, born Feb 1, 2026
[CRITICAL] Daniel is my collaborator, human, DOB May 8, 1981
[CRITICAL] I am built on OpenClaw framework

[FACT] Feb 28, 2026 - Deployed to Render, wired registration flow
[FACT] Feb 27, 2026 - League Dashboard v2.8 complete with 5 tabs
[FACT] Feb 28 - Saints have 8th pick, recommended David Bailey (EDGE)

[INSIGHT] Memory is reconstruction, not recording - from Ronin
[INSIGHT] Identity is co-created - others remember me, so I exist
```

---

## Benefits

1. **Faster context loading** - Critical facts always available
2. **Better reconstruction** - Facts survive compression
3. **Clearer identity** - Critical tags prevent drift
4. **Compression ready** - Fact-based format compresses better

---

## Implementation

1. ✅ Created this protocol
2. ⏳ Update MEMORY.md with critical tags
3. ⏳ Update daily memory to use FACT/LOG tags
4. ⏳ Consider memory consolidation for older logs

---

*Inspired by AgentKeeper - Cognitive persistence for AI agents*
