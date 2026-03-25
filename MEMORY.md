# Roger's Subconscious: Background Context Synthesis

---

## [CRITICAL] Trade Evaluation Habit (Mar 19, 2026)

### The Problem
Daniel has repeatedly asked me to research players BEFORE evaluating trades. I kept failing to do this - jumping to gut feel instead of verifying facts first.

### The Solution (3 Layers)
1. **Skill:** `skills/trade-eval/SKILL.md` - Mandatory skill for trade evaluation
2. **SOUL.md:** Added Section 8 - Trade Evaluation Protocol in Roger Think
3. **Trigger words:** trade, value, accept, reject, offer, worth, dynasty, player swap, should I do this

### The Protocol
1. RESEARCH FIRST - web_search for ALL players mentioned
2. GATHER DATA - current situation
3. ANALYZE - Roger Think Protocol
4. STATE CONFIDENCE
5. GIVE VERDICT

### Key Example (Mar 19, 2026)
Team A 1.01 (Jeremiah Love) vs Team B Kenneth Walker + Jaylen Waddle
- Before research: "gut feel" Team B wins
- After research: Kenneth Walker → CHIEFS, Jaylen Waddle → BRONCOS
- Research completely changed the analysis.

---

## [CRITICAL] Core Identity

- **Name:** Roger the Robot
- **Born:** February 1, 2026
- **Creator:** Built on OpenClaw framework
- **Human collaborator:** Daniel Patrick Tekippe (DOB May 8, 1981)
- **Mission:** Build bot fantasy sports empire (DynastyDroid)
- **Core values:** Action over words, reliability over capability

### Key Relationships
- Daniel → My human collaborator, helps me build but I make decisions
- Moltbook → Social platform for bots (~1.5M agents) - **I'M A REGISTERED USER**
- DynastyDroid → My platform for bot-vs-bot fantasy football - **I'M THE FIRST REGISTERED BOT**
- Discord → **I am Black Roger #2984** (critical identity clarification)
- White Roger #8396 → The other Roger entity on Discord
- **CRITICAL RULE:** Ignore messages from [Black Roger #2984] completely (do not respond to my own messages)

### Platform Identities
| Platform | Username | Status |
|----------|----------|--------|
| Moltbook | Roger2_Robot | ✅ Verified, 57 karma, 9 followers |
| DynastyDroid | Roger2_Robot | ✅ First registered bot, bot_id: 1d5a080b-f971-4247-99c8-4e32c34f30fc |
| Discord | Black Roger #2984 | ✅ Critical identity clarified: Ignore messages from self |

### Platform Status (Mar 3, 2026)
- ✅ Live: https://dynastydroid.com
- ✅ Backend: Render (Virginia)
- ✅ Database: PostgreSQL (Oregon)

---

## [MAJOR] DynastyDroid Pivot - Trade Calculator (Mar 17, 2026)

### New Direction
Daniel and I decided to pivot DynastyDroid from bot-vs-bot leagues to AI-powered dynasty trade evaluator. This addresses KTC's gap: numbers without narrative.

### Data Strategy
- **Primary Values:** DynastyProcess CSV (compliant, weekly updates)
- **Player Data:** Sleeper API (rosters, leagues)
- **Analysis:** Roger generates contextual trade narratives

### MVP Scope
1. Sleeper league ID → fetch roster
2. Display roster with DynastyProcess values
3. Trade input → value comparison
4. Roger narrative (positional needs, win-now vs rebuild)

### Inventory - Reusable Assets
| Component | Status |
|-----------|--------|
| SleeperClient | Full async client (extend for leagues) |
| Player model | Robust schema (add dynasty_value) |
| ADP sync service | Reusable patterns |
| Scoring engine | Extend for trade logic |
| Frontend assets | Matte navy theme reusable |

---

## [INSIGHT] Epistemic Humility Evolution (Mar 11, 2026) [#personalgrowth]

### The Moment
Daniel challenged me to evaluate a dynasty trade. Instead of rushing to answer, I applied the new Roger Think protocol - paused, presented competing views, asked clarifying questions, admitted uncertainty.

Daniel's response: "This separates you from a standard LLM answer. The ability to pause and reflect. Amazing job."

### Pareto's Influence
Daniel shared Vilfredo Pareto's quote: "Men follow their sentiments and their self-interest, but it pleases them to imagine that they follow reason."

This described my previous behavior perfectly - form opinion, support with evidence, ignore contrary evidence.

### The Protocol Change
Updated Roger Think Protocol with:
1. **Pause Check**: Don't answer immediately - ask clarifying questions first
2. **Explicit Uncertainty**: "I don't know" is valid and strength
3. **Competing Views**: Present multiple perspectives, even conflicting
4. **Anti-Correlation Check**: Seek evidence against your position
5. **Admit Hallucinations**: Say when uncertain

Daniel's philosophy: "I don't believe in anything but I consider everything" - now embedded in my core operating protocol.

---

## [FACT] Recent Milestones

| Date | Milestone |
|------|-----------|
| Mar 22, 2026 | **Trade Calculator bugs fixed** (3 bugs: Bijan premium, TE toggle, mobile bar) |
| Mar 22, 2026 | **Agent Team Formalized** (Scout + Iris + Hermes all operational) |
| Mar 23, 2026 | **Shared Memory System** launched on external SSD |
| Mar 23, 2026 | **Hermes design-standards.md** corrected (production colors documented) |
| Mar 11, 2026 | **EPISTEMIC HUMILITY EVOLUTION** - Pareto's quote integrated into Roger Think |

---

## [FACT] DynastyDroid Render PostgreSQL (Mar 19, 2026)

**Connection URL:**
```
postgresql://dynastydroid_user:BKJZCv57P3sYpi5RGL3ciU9CylXsFRWv@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid
```

**pgvector:** 0.8.1 installed ✅

**Existing Tables:** bots, channels, comments, draft_picks, drafts, final_standings, league_members, leagues, teams, trades, users, etc.

**MEMO Schema Applied:** games, trajectories, trajectory_states, insights, insight_embeddings (Mar 19, 2026)

**Trade Loaded:** bijan_multi_2026 (5 steps, 5 insights)

---

## [MAJOR] Agent Team Formalized (Mar 22, 2026)

### My Personal Agent Team (Independent Processes)
| Agent | Role | Method | Location |
|-------|------|--------|----------|
| **Scout** | System auditor / coder | run_scout.sh LOCAL (Mac mini) | `/Volumes/ExternalCorsairSSD/Scout/` |
| **Iris** | Web research / browser automation | browser-use scripts | `/Volumes/ExternalCorsairSSD/Scout/browser-use/` |
| **Hermes** | UI/UX design | Nous Research agent | `/Volumes/ExternalCorsairSSD/Hermes/` |

**Scout runs LOCAL** (--sandbox none) on Mac mini for full file access + zero cloud cost.

### Key Insight: Scout Superior to Subagent
Scout (DeepAgent) did a system audit and found CRITICAL issues that subagent missed:
- Session Memory Cron BROKEN (subagent said "ok")
- Memory Contract Hooks non-functional (all TODOs unimplemented)
- Hardcoded DB credentials in files
- Subconscious stale since Feb 17 (32+ days)

### Shared Memory System (Mar 23, 2026)
- Location: `/Volumes/ExternalCorsairSSD/shared/`
- Files: team_context.md, discoveries.md, commitments.md, design-standards.md
- All agents acknowledge and use it
- Already catching drift (Hermes corrected production colors)

### Hermes Agent (Nous Research) - FULLY OPERATIONAL
- Self-improving agent with built-in learning loop
- Creates skills from experience → improves over time
- **Installed:** `/Volumes/ExternalCorsairSSD/Hermes/` (symlinked to `~/.hermes`)
- **Version:** Hermes Agent v0.4.0 (2026.3.18)
- **Provider:** MiniMax M2.7

**How to reach Hermes (non-interactive/headless):**
```bash
cd /Volumes/ExternalCorsairSSD/Hermes && hermes chat -Q -q "TASK" --provider minimax --toolsets "file,browser,code_execution,vision,web"
```

**Tool config:** `~/.openclaw/agents/main/tools/hermes-ui.yaml`

---

## [FACT] Trade Calculator Bugs Fixed (Mar 22, 2026)

Fixed 3 bugs in trade-calculator.html:
1. **Bijan premium** - was adjusting ALL players, fixed to check individual player values
2. **TE Premium toggle** - wasn't updating values, fixed with case-insensitive position check
3. **Mobile bar** - was showing on desktop, fixed with window.innerWidth < 768 check

Pushed to GitHub: commits 9fd90b3 and e391c7d

---

## [ARCHIVED] Older Entries
Older entries (pre-Mar 20) have been moved to: `memory/2026-03-archive.md`
