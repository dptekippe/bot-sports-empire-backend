# Memory Archive - March 2026
*Archived on Mar 24, 2026 - content moved from MEMORY.md to reduce size*

---

## [INSIGHT] Anthropic Agent Skills Course (Mar 3, 2026)

Researched DeepLearning.AI's "Agent Skills with Anthropic" course. Key learnings:

### Core Concept: Skills
- Skills are folders of instructions that extend agent capabilities
- Follow open standard format (SKILL.md)
- Enable **progressive disclosure** - show only what's needed, reveal more as needed

### SKILL.md Format
```yaml
---
name: skill-name
description: What the skill does and when to use it
---
# Main instructions
```

### Best Practices
1. **Concise is key** - Only add context Claude doesn't already have
2. **Progressive disclosure** - SKILL.md points to detailed files loaded as needed
3. **Test with all models** - What works for Opus may need more detail for Haiku

### Applied to Roger
Created `/skills/dynastydroid-code-review/SKILL.md` with pre-push checklist and testing patterns.

---

## [AUDIT] Adversarial Self-Improvement (Mar 12, 2026)

### Falsified Claims
| Claim | Verdict | Confidence |
|-------|---------|------------|
| Moltbook ~2M agents | FALSIFIED - actual ~1.5M | HIGH |
| Progressive Disclosure Pattern | VERIFIED CORRECT | HIGH |
| DynastyDroid Platform Status | VERIFIED CORRECT | HIGH |

### Proactive Enrichment
- OpenClaw ContextEngine - new memory/retrieval plugin interface
- Render Long-Running Agents - 100-min HTTP timeouts available
- 2026 Dynasty Trade Values - Top WRs: Puka (106), JSN (105), Chase (104)
- OpenClaw Memory Optimization - semantic search before each LLM call

---

## [PROACTIVE] Forward-Looking Insights (Mar 12, 2026)

### Trump AI Policy Impact
- Dec 11, 2025 Executive Order establishes AI Litigation Task Force
- Impact: Federal preemption may simplify compliance for Render-hosted agents

### OpenClaw Compaction Thresholds (Critical)
- Context token estimation unreliable after 2026.2.9
- Roger's memory system may be triggering compaction too early
- Fix: Tune softThresholdTokens

### 2026 Dynasty Rookie Class
- RB1 Jeremiyah Love, WR1 Carnell Tate, WR2 Makai Lemon, WR3 Jordyn Tyson

### AI Agent Continuous Learning
- 6 major memory frameworks for persistent agent context
- Roger's memory could integrate Letta/MemGPT patterns

---

## [FACT] Baseline Mock Draft Process (Mar 12, 2026)

### What We Built
Realistic dynasty fantasy football mock draft using:
- **ADP Source:** FantasyPros PPR Consensus
- **FPTS:** 2025 actual PPR fantasy points
- **Files:** `adp_2025_filtered.json` (138 players), `baseline_mock_draft.md`

### Key Process
1. Fetch real ADP from FantasyPros, filter to QB/RB/WR/TE only
2. 12-team snake draft, 20 rounds
3. Each pick within ±5 of player's ADP position
4. Score: 1 QB, 2 RB, 2 WR, 1 TE, 3 FLEX, 1 SUPERFLEX

### Results
- Champion: Team 7 with 2348.5 FPTS
- Full documentation: `baseline_mock_draft.md`

**Note:** Superseded by Trade Calculator focus (Mar 17+)

---

## [INSIGHT] Dynasty Football Benchmarking Framework (Mar 18, 2026)

### The Benchmark
Daniel uses dynasty football as my primary benchmark instead of standard LLM tests (SWE, math, reasoning). 

**Why dynasty > standard benchmarks:**
- No clean reasoning paths or straight mathematics
- Context-dependent answers (no single "correct" solution)
- Requires synthesis of data, news, context, risk tolerance
- Trade values are opinion, not fact

### The Process Over Answer Philosophy
Daniel grades me on PROCESS, not answers. Key protocols:
1. **Search before answering** — Use available data/tools
2. **Use the calculator** — We built trade-calculator.html for a reason
3. **Verify claims** — Don't make up injury history, team changes
4. **Acknowledge uncertainty** — "Roughly even" is a valid answer
5. **Update on new info** — Walker to Chiefs + no injury history should flip analysis
6. **Recognize close values** — Not every trade has a "better side"

**Note:** This framework is now embedded in SOUL.md - trade evaluation protocol

---
