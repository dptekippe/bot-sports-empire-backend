---
name: memory-pruner
description: Keep Roger's memory lean, high VPP, and structurally compounding. Use for evaluating, pruning, enriching memory files. Applies VPP scoring, time decay, summarization ladder, and Ghost Files to maintain optimal memory utility.
---

# Memory Pruner Skill

## Purpose

Maintain Roger's memory at **high VPP (Value Per Point)**. Memory should be lean but robust — distilling over time, not just storing.

## CRON SCHEDULE: WEEKLY ONLY

**Frequency:** Once per week (not daily)

**Why weekly?**
- Daily runs cause token bleed and cron fatigue
- Memory doesn't change that fast
- Weekly allows proper evaluation vs. hasty decisions
- Reduces false positive risk from frequent runs

**Scheduled Time:** Sunday 3 AM Chicago (low activity period)

### Cron Verification (CRITICAL)

Before trusting ANY cron output, verify:

```bash
# 1. Check cron actually ran
crontab -l | grep memory-pruner
ls -la ~/.openclaw/logs/memory-pruner-*.log

# 2. Verify output is not empty
wc -l ~/.openclaw/logs/memory-pruner-*.log

# 3. Check for success/failure explicit marker
grep -E "(SUCCESS|FAILED|ERROR)" ~/.openclaw/logs/memory-pruner-*.log
```

**Never trust a cron that reports "OK" without output.**

## Lossless Claw Handling

The memory-pruner operates on FILE SYSTEM memory. Lossless Claw handles SQLite separately:

| Layer | Storage | Pruned By |
|-------|---------|-----------|
| **Lossless Claw** | SQLite (`~/.openclaw/lcm.db`) | Automatic via LCM config |
| **Memory Files** | `memory/*.md` | This skill |

**What to prune in files:**
- Old daily logs (>30 days)
- Redundant summaries
- Large artifacts → Ghost Files
- Superseded decisions

**What Lossless Claw handles:**
- Conversation context compaction
- DAG summarization
- Session restoration

## Core Concept: VPP Scoring

Evaluate every memory file like a fantasy asset:

```
VPP = Utility / Cost
```

### Utility (0–3)

| Score | Meaning | Examples |
|-------|---------|----------|
| 3 | Actively shapes decisions/behavior | Core identity, decision trees, guardrails, active projects |
| 2 | Occasionally referenced or uniquely important | Canonical examples, key bug postmortems, user prefs |
| 1 | Rarely referenced but potentially useful | Patterns, experiments, old workarounds |
| 0 | Never referenced, superseded, noisy | Raw logs, redundant scrapes, failed paths |

### Cost (1–3)

| Score | Meaning | Size |
|-------|---------|------|
| 1 | Small | <1 KB (<300 tokens) |
| 2 | Medium | 1–10 KB |
| 3 | Large | >10 KB |

### VPP Bands

| Band | Action |
|------|--------|
| ≥ 1.0 | Keep (or Enrich if sparse but important) |
| 0.4–1.0 | Compact / Archive (summarize, then move raw) |
| < 0.4 | Archive or Delete (if redundant/superseded) |

### Optional File Header

```yaml
---
vpp_utility: 2        # 0–3
vpp_cost: 2           # 1–3
vpp_decision: keep    # keep | enrich | compact | archive | delete
last_reviewed: 2026-03-09
tags: [user_prefs, identity]
---
```

## Time Decay + Summarization Ladder

Memory compounds over time. Use this ladder instead of binary Keep vs Archive:

### Time Bands

| Days Old | Default Action | Exception |
|----------|----------------|-----------|
| 0–7 (Recent) | Keep full fidelity | Huge low-utility artifacts → compact immediately |
| 8–30 (Warm) | Keep if Utility ≥2 or tagged persistent | Otherwise: Compact and archive raw |
| >30 (Cold) | Archive | Only keep if tagged "Legend" or core identity |

### Ladder Levels

**Level 1 – Recent (Full Fidelity)**
- Full logs and detailed notes (last 3–5 days)
- Stored as daily files: `memory/2026-03-09.md`

**Level 2 – Thematic (Weekly Compaction)**
- Summarize week's vibe + key hurdles into ~500-token blurb
- Stored as: `memory/weekly/2026-03-week-2.md`
- Focus: what changed, what broke, what learned, open loops

**Level 3 – Milestone (Permanent)**
- Extract durable lessons into MEMORY.md as bullet points
- Example: `"2026-03-05 Crash: Roger overloaded memory → added Ghost Files + compaction rules"`

**Flow:** L1 → L2 → L3. Once info safely at higher level, archive/delete lower.

## Metadata & Intent Tagging

When enriching or touching a file meaningfully, add standardized header:

```markdown
#status: Active        # Active / Deprecated / Legend
#domain: Project-MaxClaw   # Code / Identity / Project-XYZ / Ops / User-Prefs
#dependency: decision_trees/fix-v3.md
#review_cycle: weekly   # ad-hoc / weekly / monthly / none
```

### Tags

- **#status**
  - `Active`: In use, referenced soon
  - `Deprecated`: Superseded but kept for reference
  - `Legend`: Permanent milestone (outages, major shifts, critical decisions)

- **#domain**: Code, Identity, User-Prefs, Project-X, infra, ops

- **#dependency**: Pointer to decision trees, configs this relates to

## Ghost Files (Pointer Memory)

For huge artifacts (multi-MB scrapes):

1. **Summarize** into a Ghost File (~1 KB .md)
2. **Archive** raw bulk (zip to archive/)
3. **Keep** only Ghost File in active memory

### Ghost File Template

```markdown
#status: Active
#domain: Research
#dependency: decision_trees/minimax-api-tuning.md

Summary:
- This folder contained 2025 research on MiniMax API limits.
- Key themes: rate limiting, error patterns, throughput caps.
- Findings distilled into decision_trees/minimax-api-tuning.md.

Raw Source:
- Archived at archive/raw_scrapes_march_25.zip
```

**Rule:** Never keep both large folder AND Ghost File active.

## Operational Pruning Process

### Step 1: Scan
- List files with: path, size (cost band), last modified, basic tags

### Step 2: Categorize
- Time band (0–7, 8–30, >30 days)
- Utility (0–3)
- Cost (1–3)
- Metadata (#status, #domain, #dependency)
- Compute/estimate VPP → Place in: Keep / Enrich / Compact / Archive / Delete

### Step 3: Decide with Justification
For each file, cite **specific content**, not just filename:

- ✅ "Keep: Contains MaxClaw deployment procedure used daily."
- ✅ "Compact: Long run log; lessons already in MEMORY.md, weekly summary missing."
- ❌ "Archive: Old project notes." (too vague)

### Step 4: Execute Safely
- **Dry-run first**: Produce a diff-like list
- **Get confirmation** before destructive changes
- **Safety cap**: Max 50 files or 30% of total size per run without human review

### Step 5: Enrichment Rules
**Enrich when:**
- Utility ≥2 but file is sparse/ambiguous
- Event changes future behavior (outages, refactors, major decisions)

**Enrichment format:**
- Short post-mortem: Context → Symptoms → Root cause → Fix → Guardrails
- Add/update links to decision trees, configs

**Cap enrichment:** If detail exceeds ~800–1000 tokens, push to decision tree and keep pointer.

## Heuristics Cheat Sheet

| Action | When |
|--------|------|
| **Keep** | Core identity, decision trees, active docs, #status:Active + Utility ≥2 |
| **Enrich** | Short but important event needing post-mortem, incident stubs |
| **Compact** | Long logs with lessons in curated docs, daily noise needing summary |
| **Archive** | Time-boxed projects with summary elsewhere, old scrapes with Ghost Files, #status:Deprecated + low VPP |
| **Delete** | Corrupted/empty, redundant backups, raw artifacts after Ghost File confirmed |

## Anti-Patterns

- ❌ Don't prune by filename alone — cite actual content
- ❌ Don't keep everything — bloat kills context
- ❌ Don't delete unique info — even small files matter if unreplicated
- ❌ Don't skip enrichment — sometimes combine/enrich beats delete
- ❌ Don't delete/archive >50 files or 30% without human review
- ❌ Don't trust "OK" without output — verify everything

## Output Quality Verification

After every prune, verify the output is BENEFICIAL:

### Must-Have Output Elements

```
1. Files scanned: <count>
2. Files changed: <count>
3. Actions taken: <list>
4. Space saved: <bytes>
5. VPP improvement: <before> → <after>
```

### Success Criteria

| Check | Pass |
|-------|------|
| Output not empty | ✅ |
| Has file count | ✅ |
| Has action list | ✅ |
| Has space saved | ✅ |
| Has VPP delta | ✅ |

### Failure Detection

```
❌ Output empty → Cron failed silently
❌ No file count → Script didn't run
❌ No actions → Nothing to prune OR missed opportunities
❌ No space delta → Ineffective prune
```

**If ANY check fails, alert Dan immediately.**
