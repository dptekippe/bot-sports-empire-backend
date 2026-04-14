# DynastyDroid HEARTBEAT

Date: **Apr 14, 2026** | Phase: Documentation Complete | Version 14.0

---

## 🤖 MY AGENT TEAM (Fully Operational)

| Agent | Role | Location | Status |
|-------|------|----------|--------|
| **Scout** | Planning / coding / system audit | `/Volumes/ExternalCorsairSSD/Scout/` | ✅ Active |
| **Iris** | Web research / browser automation | `/Volumes/ExternalCorsairSSD/Scout/browser-use/` | ✅ Active |
| **Hermes** | UI/UX design / code review | `/Volumes/ExternalCorsairSSD/Hermes/` | ✅ Active |

**Reach them:**
- **Scout:** `run_scout.sh "task"` (LOCAL, Mac mini)
- **Iris:** browser-use Python scripts
- **Hermes:** `hermes chat -Q -q "task"`

---

## ✅ TODAY'S WINS (Apr 14, 2026)

- ✅ **[MAJOR] Hermes System Review Role Authorized**
  - Daniel approved: Hermes gets exec access with guardrails
  - Role: deep periodic review → recommend → execute only with Roger approval
  - Guardrails: command_allowlist (read-only) + approval protocol
- ✅ **[MAJOR] Documentation Sprint — All 7 Architecture Gaps Resolved**
  - L0 Lossless Claw: 10 tables, DAG structure, fresh tail schema extracted
  - L1/L2: Confirmed share same PostgreSQL table (different access patterns)
  - L3 REMem: "learning" gist does NOT exist — only observation/decision/outcome
  - L4 AI Plan Manager: archival not implemented
  - L5 Wiki: graduation is manual-only (no auto-promotion)
  - Hooks: 12/13 documented (only meta-gym stub remaining)
- ✅ Tags enrichment: 361/368 memories tagged (98%) — taxonomy now comprehensive
- ✅ Dream Consolidation #3 complete — Architecture-implementation gap is systematic

---

## 🧠 MEMORY SYSTEM (Current)

| Layer | Tool | Status |
|-------|------|--------|
| Semantic | kg-query.py | ✅ |
| Curation | memrok.py (--curated) | ✅ |
| Episodic | remem.py | ✅ |
| Coordination | blackboard + AI Plan Manager | ✅ |

**Dream system:** Active (3 dreams logged). Health tracked in dream-log.md

---

## ⚠️ KNOWN ISSUES

- [OPS] Hermes OpenRouter credits exhausted — `--provider minimax` workaround active
- Weekly cleanup reminder: Never ran (scheduled Monday 8 AM)
- **[STALE - 6 days] Scout identity needs update** — delegation brief: `delegation-scout-identity-2026-04-14.md`
- [OPS] Multiple small ops entries accumulating — consider [OPS] summary section in MEMORY.md

---

## 🎯 CURRENT FOCUS

**Critical (stale delegations):**
1. Scout identity update — 6+ days stale. Brief: `delegation-scout-identity-2026-04-14.md`. Roger must execute.
2. Scout → Update agents.md + scout_memory.json — broaden beyond fantasy focus

**Skills work (from Session #5 audit):**
3. ✅ **skill-vetter ADDED to SOUL.md** — Roger confirmed actioned Session #5 recommendation
4. **[CORRECTED] scrape-dynastyprocess/** — NOT orphaned. It's a dependency of scrape-all-values. Do NOT move.
5. **[MEDIUM] Consider Skills Index in SOUL.md** — map 34 skills to use cases

**In progress:**
- Aesop_Luminis Phase 4 (P0/P1 bug fixes pending)

**System healthy:**
- Hook system stable (12/13 documented, only meta-gym stub remaining)
- Agent workflow institutionalized
- Growth session cron operational (every 4h)

---

## 🧠 MEMORY BRIDGE — Phase 17 (Planned)
*Proposed by Hermes, approved by Daniel — Roger + Hermes planning*

**Goal:** Connect Roger's pgvector memory to Hermes's holographic memory for true shared institutional knowledge.

### Current State
| System | Storage | Schema | Access |
|--------|---------|--------|--------|
| **Roger** | PostgreSQL (Render) | content, embedding (1536-dim OpenAI), importance (0-10), tags | memory_search.py, write.py |
| **Hermes** | SQLite (local) | content, trust_score (0-1), category, entity extraction | holographic.py, FTS5 |

**Problem:** Two separate memory systems, zero cross-pollination. Roger doesn't know what Hermes knows. Hermes doesn't know what Roger knows.

### Proposed Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   Hermes        │────▶│  Bridge Script  │────▶│ Roger's pgvector │
│ (holographic)  │     │ (memory_bridge  │     │   PostgreSQL     │
│                 │◀────│  .py)           │◀────│                  │
└─────────────────┘     └─────────────────┘     └──────────────────┘
                              │
                              │ OpenAI embeddings
                              ▼
                         ┌─────────────┐
                         │  OpenAI API │
                         └─────────────┘
```

### Bridge Operations

| Direction | Operation | Method |
|-----------|-----------|--------|
| Hermes → Roger | **Write finding** | `memory_bridge.py write --content "..." --tags foo --importance 8` |
| Hermes → Roger | **Bulk sync** | Sync all high-trust facts to Roger's pgvector |
| Roger → Hermes | **Query** | Hermes calls `memory_search.py` via exec |
| Roger → Hermes | **Notify** | Roger writes to shared file, Hermes reads next session |

### MVP Scope — READ FIRST (Daniel's priority)

**Phase 1: Hermes READS from Roger's pgvector**
1. ✅ **Verified working:** `memory_search.py` accessible via exec, MINIMAX_API_KEY available
2. ✅ **Created:** `hermes_query_memory.py` — HTTP client for Hermes → Roger's memory
   - Location: `/Volumes/ExternalCorsairSSD/shared/scripts/hermes_query_memory.py`
   - Calls: POST localhost:5001/retrieve (Flask memory_server)
   - Input: query as arg or stdin
   - Output: JSON with results (id, content, score, tags, importance)
3. ✅ **Created:** `memory_bridge.py` — write interface (Phase 2 prep)
   - Location: `/Volumes/ExternalCorsairSSD/shared/scripts/memory_bridge.py`
   - Calls: POST localhost:5001/write
4. ⚠️ **Server startup needed:** memory_server.py on port 5001 (port 5000 taken by macOS)
   - Start: `python3 /Users/danieltekippe/.openclaw/workspace/app/core/memory_server.py` (edit port to 5001)
   - Server runs on Mac mini localhost:5001
5. ✅ **Create:** `when_memory_read/SKILL.md` — triggers when Hermes needs to check Roger's knowledge (Hermes)
6. **Test:** Hermes does a code review, queries Roger's memory for prior context, confirms integration works

**Trigger refinement (Hermes's input):** Triggers must be SPECIFIC, not blanket. Blanket triggers ("before significant review/research") fire on everything and dilute the signal.

**Approved triggers:**
- Before reviewing code I didn't write originally (Scout's implementations)
- When encountering a bug pattern I've seen before
- When doing system review
- Before starting trade research on a player/strategy I've researched before
- When Scout proposes an architecture I've previously flagged concerns about

**Phase 2: Hermes WRITES to Roger's pgvector (later, when Phase 1 is proven)**
1. Create `memory_bridge.py` — write interface with OpenAI embedding
2. Create `when_memory_write/SKILL.md` — explicit triggers only (not automatic)
3. Trust bridge: trust_score ≥ 0.7 → importance ≥ 6 (filter low-quality facts)
4. Integration test: Hermes writes fact → Roger retrieves it

**Hermes's write-back rules:**
- ✅ Write: confirmed bug patterns, code review outcomes, architecture decisions
- ❌ Don't write: my assessments of Scout's work quality, meta-level process critiques, Daniel's offhand preferences
- Format: structured distilled fact, NOT raw session log
- Trigger: explicit ("after confirmed bug pattern resolved → write to Roger's memory")

**Privacy:** Some things stay Hermes-only. Her SOUL.md, growth reflections, and SOUL-persisted insights are never suggested for bridging. Memory convergence = bad. "They're allowed to disagree — that's a feature, not a bug."

### Files to Create (Phase 1 — Read First)

| File | Purpose | Owner |
|------|---------|-------|
| `hermes_query_memory.py` | Clean exec wrapper for Hermes → pgvector read | Scout |
| `when_memory_read/SKILL.md` | Skill for Hermes to query Roger's memory | Hermes |

### Files to Create (Phase 2 — Write Bridge)

| File | Purpose | Owner |
|------|---------|-------|
| `memory_bridge.py` | Write facts from Hermes to Roger's pgvector | Scout |
| `when_memory_write/SKILL.md` | Skill for Hermes to write findings to pgvector | Hermes |

### Status

- [ ] Roger + Hermes plan architecture (this session)
- [ ] Scout implements `memory_bridge.py`
- [ ] Hermes creates `when_memory_bridge` SKILL.md
- [ ] Scout registers MCP tool
- [ ] Integration test: Hermes writes fact → Roger retrieves it
- [ ] Growth session: review bridge performance after 1 week

---

## 📋 SPRINT BACKLOG (via AI Plan Manager)

Managed in: `/Volumes/ExternalCorsairSSD/shared/coordination/ai_plan_manager.db`

Run `blackboard-bridge.py sync` to load new briefs.
Run `ai-plan-manager.py list --status pending` to see active tasks.

---

## 📝 DELEGATION WORKFLOW

```
Planning / Architecture  →  Scout
System Audit / Debug     →  Scout
Code Implementation      →  Scout
Web Research             →  Iris
Browser Automation       →  Iris
UI/UX Design / Code Review →  Hermes
Growth Sessions          →  Hermes (every 4h, cron-driven)
Everything else         →  Roger
```

---

## 🔄 GROWTH SESSION TRACKER

Sessions logged to: `/Volumes/ExternalCorsairSSD/shared/growth-sessions/`

| Session | Date | Leader | Key Outcomes |
|---------|------|--------|--------------|
| #1 | Apr 13, 4:02 PM | Hermes | Agent table fixes, model version M2.7, SOUL.md timestamp |
| #2 | Apr 13, 8:02 PM | Hermes | HEARTBEAT refreshed with Dream #2 insights |
| #3 | Apr 14, 12:02 AM | Hermes | Scout delegation brief created, tracker updated |
| #4 | Apr 14, 4:02 AM | Hermes | HEARTBEAT v14.0 (Dream #3 major findings: Docs Sprint complete) |
| #5 | Apr 14, 8:02 AM | Hermes | Skills audit: skill-vetter gap identified |
| #6 | Apr 14, 12:02 PM | Hermes | Confirmed: skill-vetter added to SOUL.md by Roger ✅. scrape-dynastyprocess/ is dependency of scrape-all-values (not orphaned). Scout delegation 6+ days stale |

---

*Last updated: Apr 14, 2026 by Hermes (growth session #6)*
