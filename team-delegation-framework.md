# Team Delegation Framework — Roger OS
**Version:** 1.1  
**Date:** March 25, 2026 (4-way review: Scout + Hermes + Iris + Roger) + post-mortem update
**Authors:** Roger (orchestrator), Scout, Hermes  
**Seed Insight:** From Karpathy's Muon optimizer — "Constraint enables exploration." Constrain to orthogonal manifold → paradoxically explore MORE aggressively. Applied to team: boundaries prevent local shortcut collapse.

---

## Core Principle

**Muon Orthogonality = Role Isolation with Cross-Validation.**  
Each agent is constrained to its manifold (role), moves freely within it. Prevents "gradient collapse" where all agents optimize toward the same local optimum and fail silently.

---

## 1. Constraints on Roger (Orchestrator)

### A. 3-Before-You-Delegate Rule
Before delegating anything, Roger must specify:
- **Output format** — "Return JSON with fields X, Y, Z"
- **Scope budget** — "Max 500 tokens, 5 minutes"
- **Abort condition** — "If you can't find X in 3 searches, return null and I'll re-route"

### B. Reversibility Budget
Soft cap: **3 unilateral calls per day** (decisions made without consulting any agent).
Exceeding triggers mandatory full-team sync. Prevents solo-orchestration drift.

### C. Explicit Override Log
When Roger overrides an agent's recommendation, must log:
```
Overriding [Agent] because [specific reason]. Evidence: [X].
```
**Log location:** `/logs/overrides.md` — structured fields: `| timestamp | overrid_agent | overrider | reason | evidence_link | disputed | resolution |`
Creates audit trail. Prevents shortcut decisions that feel right but lack team grounding.

### D. Context Forcing Function
Before delegating, Roger must articulate: *"The problem I'm solving is..."*
Forces clarity. Agents can reject delegations that lack this framing.

### E. Mandatory Dissent Window
Before finalizing a decision, each agent must state **one counterargument**.
Not optional. This is the orthogonalization step — prevents "local shortcut" consensus.

### F. Pre-Build Verification Checkpoint (NEW — post Roger Chat failure)
Before ANY build or deployment, Roger must answer:
> **"Will our build actually work?"**

Specifically:
- **External dependencies** — Have we verified API endpoints, services, and protocols exist and work? (Test with `curl` or 5-line prototype first)
- **Proof of concept** — Have we proven the core mechanism works before full implementation?
- **Scout sign-off** — Does Scout confirm "the build will work" before production code?

**If the answer is "I don't know" or "not yet verified" — STOP. Build a prototype first.**

*This checkpoint was added after Roger Chat failed because we deployed before verifying the API existed.*

### G. SDK Verification Rule (NEW — post Aesop-Luminis Phase 3 failure)
Before Scout writes ANY code for a plugin, integration, or external system:

1. **Verify types FIRST** — Read the actual SDK source/type definitions, not documentation
2. **Run a 5-line proof-of-concept** — Prove the SDK calls work before writing the full implementation
3. **Confirm build compiles** — Run `tsc` or `python -m py_compile` before considering the code done

**The sequence must be:**
```
Inspect SDK types → Write proof-of-concept → Verify it compiles/runs → Write full implementation
```

**Why this matters:** Scout built aesop-luminis Phase 3 against an assumed SDK. The code had 9 TypeScript compilation errors because the types Scout assumed didn't exist. Hermes's code review missed this because she reviewed logic, not SDK integration.

**Failure mode:** Writing code against a wrong assumption about external APIs is the most expensive kind of rework — you build the whole thing before discovering it doesn't fit.

*Added after aesop-luminis Phase 3 failed to compile — Scout's code assumed SDK types that didn't exist.*

---

## 2. Constraints on Sub-Agents

### A. Output Contracts
Each agent declares output format upfront before starting. Minimum: **Type tag + format declared at task start**.

| Output Type | Required Fields |
|---|---|
| CODE ([CODE]) | Type tag, what changed, dependencies, confidence |
| ANALYSIS ([ANALYSIS]) | Type tag, key findings, assumptions surfaced, confidence |
| REVIEW ([REVIEW]) | Type tag, target, verdict, red line, confidence |
| HANDSHAKE ([HANDSHAKE]) | Type tag, status, blockers, next step |

Deviating from contract requires explicit re-negotiation with Roger.

### B. Confidence Tags (Mandatory)
Every output must include a confidence declaration:
- **[HIGH]** — Verified, confident, multiple sources confirm
- **[MEDIUM]** — Likely correct, one source, minor uncertainty
- **[LOW]** — Best guess, unverified, needs validation

LOW confidence is not weakness — it's information. Forces honest epistemic signaling.

### C. Alternatives Considered (Mandatory)
Every output must answer: *"What I almost did instead, and why I didn't."*
Creates paper trail of explored-but-rejected directions. Reduces correlated drift.

### D. Version Stamping
All outputs include version stamp: `v{TASK_NUM}.{iteration}` (e.g., `v14.3` = task 14, iteration 3). Roger assigns task number at delegation. Each output to same task increments iteration.
Like git commits. Prevents groundhog day — re-discussing solved problems.

### E. Timeboxing
Agents flag when working **>5 iterations** (one iteration = one substantive code/file change) without a status update or intermediate commit.
Triggers escalation. Prevents rabbit-hole while others wait.

### G. Assumption Surfacing (Mandatory)
Before completing any output, answer: *"What would have to be true for this to be valid?"*
Surfaces hidden assumptions. Particularly important for Iris (research) but applies to all agents.
This is the prospective version of the Pre-Mortem (Section 4.D).

### H. Research-First Workflow (Iris Priority)
**When research is involved, Iris goes first. Always. No exceptions.**

The correct delegation sequence for research tasks:
1. **Iris researches first** — complete, thorough, no rushing. Iris takes the time she needs.
2. **Roger + Scout evaluate** — after Iris finishes, Roger and Scout review what Iris found together.
3. **Gap identification** — Roger and Scout determine what information is still missing.
4. **Scout fills gaps** — Scout goes and obtains only the missing information. Scout does NOT do parallel primary research.
5. **Combine** — integrated output with Iris's foundation and Scout's gap-fill.

**Why this matters:** Rushing Iris or delegating to Scout in parallel means we lose the depth Iris provides. Iris's research is the foundation. Scout is the gap-filler and executor, not the primary researcher when Iris is involved.

**The failure mode this prevents:** Scout finishes first, writes output with Scout's own research, then we never properly integrate Iris's findings. Iris's contribution becomes an afterthought.

**Application:** Any time a task involves research (player analysis, trade evaluation, platform feature research), Iris gets the task first. Roger waits. Scout waits. No parallel delegation.

### F. Domain Boundary + Escape Valve
Each agent has a domain. Don't venture out without explicit handoff.
**But:** if another agent's output violates your domain expertise, you're **obligated** to flag it.
Example: If Scout writes code that breaks UX principles, Hermes MUST speak up.
**Enforcement:** If Scout disputes a Hermes Domain Escape flag within one cycle, it **auto-escalates to Roger** as a design-language emergency — not at cycle limit. Fast-track, not slow-track.

---

## 3. Avoiding Correlated Drift

### A. Adversarial Pairing (Rotating)
| Problem Type | Lead | Challenger | Validator |
|---|---|---|---|
| Design decisions | Hermes | Scout | Iris |
| Technical architecture | Scout | Hermes | Roger |
| Research/validation | Iris | Roger | Scout |
| Strategic direction | Roger | Iris | Hermes |

- Lead owns direction
- Challenger must find one flaw per iteration
- Validator confirms cross-domain standards
- Roles rotate per project type
- **Challenger format:** `CHALLENGE: [element] — [specific flaw, one sentence]. Suggested resolution: [X].`

### B. Devil's Advocate Rotation
Each session, one agent randomly assigned "red team" duty.
They MUST argue against consensus, even if they privately agree.
Prevents confirmation cascades.

### C. Information Asymmetry as Feature
- Iris has web access others don't → deliberately withhold full context from some agents in early stages
- Forces independent validation vs. synchronized drift
- Different tool access = different search paths

### D. "What Would Have to Be True?" Constraint
Before finalizing, each agent must answer: *"What assumptions, if wrong, would invalidate my output?"*
Surfaces hidden correlation (e.g., all assuming same data source is correct).

---

## 4. Validation Protocols

### A. Three-Layer Validation (CI/CD Pipeline)
| Layer | Who | What | Gate |
|---|---|---|---|
| L1: Syntax | Scout | Does it work? Code valid? | Build passes |
| L2: Semantics | Hermes | Does it feel right? Usable? | Design review |
| L3: Truth | Iris | Accurate? Externally validated? | Research check *(see Section 11 for Iris's detailed validation gates V1-V4)* |
| L4: Strategic | Roger | Serves mission? | Final sign-off |

Each layer **can reject**, not just approve. Rejection requires specific feedback.

### B. "Reproduce Me" Protocol
Any agent claiming a fact must include enough context that another agent could independently verify in 10 minutes of effort. If it can't be reproduced, it's flagged.

### C. "Red Line" Review
Each reviewing agent draws ONE red line — the one thing that MUST change. For Iris: "one blocking issue" — multiple non-blocking concerns are still valid and should be listed separately after the red line.
Forces prioritization. Prevents validation theater.

### D. Pre-Mortem Protocol
Before finalizing: *"It's 6 months later and this failed. Why?"*
Agents compete to find best failure explanation. Dominant failure mode gets addressed before shipping.

---

## 5. Information Flow Architecture

### A. Star Topology with Ring Backup
```
        Roger (center)
       /    |     \
      /     |      \
   Scout  Hermes  Iris
      \     |     /
       \    |    /
        (ring link)
```
- **Primary:** Roger ↔ Agent (direct delegation)
- **Ring:** Scout ↔ Hermes ↔ Iris ↔ Scout (peer validation)
- **Emergency:** Any agent → any agent if Roger unresponsive or drifting

### B. Information Products
| Agent | Produces | Consumers |
|---|---|---|
| Roger | Decisions + Priorities | All |
| Scout | Implementations + Code | Roger, Hermes |
| Hermes | Designs + UX specs | Scout, Roger |
| Iris | Research + Validations | All |

### C. Feed-Forward Rule
When delegating, include: *"What I need from you"* AND *"What I'll do with it."*
Prevents agents optimizing toward unknown goals.

### D. Reverse Handoff
After completing, agent reports not just output but: *"What should the NEXT agent know that I learned?"*
Captures institutional knowledge that normally gets lost.

### E. No Gaps, No Overlaps
- Each piece of work has **ONE owner**
- Overlaps → "Whose job is this?" → Roger decides
- Gaps → flagged in review

---

## 6. Decision Rights Matrix

| Decision Type | Decides | Consults | Informs |
|---|---|---|---|
| Architecture/code | Scout | Hermes (UX), Roger (strategy) | All |
| Design/UX | Hermes | Scout (feasibility), Iris (research) | All |
| Research direction | Iris | Roger (priority), Scout (technical) | All |
| Strategic priority | Roger | All agents (input) | All |
| Trade-offs (speed vs quality) | Lead agent for domain | Roger for cross-domain | All |

> **Consult vs. Review:** "Consult" = input requested, not blocking. "Reviews" = sign-off required, blocking. Lead agent = owner of domain in first column. If decision spans domains, Roger designates lead.

---

## 7. Implementation Checklist

- [x] Roger writes first draft of Role Cards → shared memory
- [x] Scout adds technical constraints
- [x] Iris adds validation gates
- [x] Hermes adds handoff protocols
- [x] 4-way review → finalize v1.0 (27 fixes applied, 47 issues found)

---

## 8. Technical Constraints (Scout)

### A. Code Quality Gates (Definition of "Done")

Code is NOT complete until ALL pass:

| Gate | Criteria | Who Verifies |
|---|---|---|
| **Build** | `python -m py_compile` or equivalent succeeds; no import errors | Scout (automated) |
| **Lint** | No syntax errors, follows project style (ruff/flake8/ESLint) | Scout (automated) |
| **Type Check** | For Python: mypy strict pass; For JS: TypeScript compiles with no `any` escapes | Scout |
| **Unit Tests** | Core logic covered; new features have tests; no regressions | Scout + validator |
| **Integration Smoke** | Affected API endpoints respond correctly with test payloads | Scout |
| **Security Scan** | OWASP Top 10 checked, CORS policy set, rate limiting documented, input validation on all external inputs, no hardcoded secrets | Scout |

**"Done" = all gates green. Not 4/5. Not "mostly works."**

---

### B. Testing Requirements

| Type | Coverage Target | When Required |
|---|---|---|
| **Unit** | Critical path logic (80% min), enforced via `pytest --cov=src --cov-fail-under=80` | Every PR |
| **Integration** | API contracts, DB queries, external API mocks | Features touching >1 system |
| **Smoke** | `/health`, core user flows | Every deploy |
| **Regression** | Bug fixes must include test that would have caught bug | Bug PRs |

**No test = no merge.** Exception: trivial changes (typos, docs) require only lint pass.

**External API mocking:** All Sleeper API, DynastyProcess, FantasyPros calls must be mocked in tests. No live API calls in CI.

---

### C. Technical Review Gates

Before code is considered complete:

1. **Self-review checklist** (Scout completes before requesting review):
   - [ ] Code matches existing patterns in codebase
   - [ ] No commented-out debug code
   - [ ] Error handling added (not just `pass` or `except: pass`)
   - [ ] Logs added for production-tracked events
   - [ ] Environment variables used (no hardcoded credentials)
   - [ ] Backward compatibility maintained or migration documented

2. **Peer review required for:**
   - Any change to `main.py` (FastAPI backend) → Roger review
   - Any change to shared data models/schemas → Iris review
   - Any UI component change → Hermes review
   - Any external API integration → Iris + Scout review

3. **Reviewer must:**
   - Run the code locally (not just read diff)
   - Test at least one real scenario end-to-end
   - Leave one specific "red line" issue or explicitly approve

---

### D. Architectural Decision Authority

| Decision | Scout Decides Alone | Scout Proposes → Roger/Team Decides |
|---|---|---|
| File structure within `/static/` or `/api/` | ✓ | |
| Variable naming, function organization | ✓ | |
| Adding a new endpoint to existing API | | ✓ |
| New library/dependency (must document why needed) | | ✓ |
| Database schema changes | | ✓ (with Iris validation) |
| Changes to API contract (request/response shape) | | ✓ |
| Introducing caching layer | | ✓ |
| New external API integration | | ✓ (team approval required) |
| Changing authentication/authorization | | ✓ (Roger approval required) |
| Performance trade-offs (speed vs. accuracy) | Scout domain | If affects UX → Hermes consult |
| Error handling strategy | Scout domain | If affects user experience → Hermes consult |

**Principle:** If it affects multiple agents' work or user-facing behavior, it needs cross-validation.

---

### E. Git/Version Control Practices

| Practice | Standard | Rationale |
|---|---|---|
| **Branch naming** | `scout/feature-name` or `scout/fix-name` | Clear ownership |
| **Commits** | `git add <specific_files> && git commit -m "Roger: [description]"` — NEVER use `git add .` in production branches | Per Roger OS protocol |
| **PR titles** | `[domain]/[short description]: [what changed]` | e.g., `backend/add-player-endpoint: added GET /api/v1/players` |
| **PR size** | Max 400 lines changed | Forces small, reviewable PRs |
| **Merge strategy** | Squash + merge (clean history) | Unless multi-commit PR with meaningful history |
| **Atomic commits** | One logical change per commit | Bisect-friendly |
| **Rollback commits** | Always keep rollback option via revert commit | Never force-push to main |
| **Tag on deploy** | `git tag deploy/YYYY-MM-DD-HHMM` | Traceability |
| **Protected branches** | `main` requires PR + 1 review minimum | No direct pushes |

**Commit message format:**
```
[domain]/[ticket if exists]: [what] | [why changed] | [side effects if any]

Example:
scout/dynasty-api: add trade proposal endpoint | Roger requested in sprint 3 | None
```

**Never commit:**
- `.env` files or any credentials
- `__pycache__`, `.pyc`, `.pyo`
- `node_modules/`
- API keys, tokens, passwords
- Debug print statements left in code

**Pre-commit hook must run:** lint + type check before `git push` allowed.

---

### F. Dependencies & Environment

| Rule | Standard |
|---|---|
| **New package** | Document in PR why existing packages insufficient; Roger approves |
| **Python version** | Match Render.com deployment target (currently 3.11+) |
| **Node version** | Match static hosting requirements |
| **Virtual env** | Use `uv` for Python dependency management |
| **Lock files** | Commit `uv.lock` / `package-lock.json` on every dependency change |

---

### G. Security Constraints (Non-Negotiable)

- **Never log:** passwords, tokens, API keys, full PII
- **Never accept:** user input without validation (sanitize, type-check, bounds-check)
- **API keys:** Use environment variables ONLY, never hardcoded
- **SQL:** Always parameterized queries (no string interpolation)
- **Secrets rotation:** If any key is suspected compromised → immediate rotation + team notification

---

### H. Monitoring & Observability

| Requirement | Standard |
|---|---|
| **Health endpoint** | `/health` returns 200 + `{status: "ok", timestamp}` |
| **Error logging** | Use structured logging (JSON format) for errors; include request_id |
| **API latency** | Target <200ms p95 for internal calls; flag if >500ms |

---

## 9. Anti-Patterns to Avoid

| Anti-Pattern | Why Bad | Prevention |
|---|---|---|
| **Rubber-stamp validation** | Agents approve without checking | Red Line review, rejection required |
| **Confirmation cascade** | First opinion anchors all | Devil's Advocate rotation |
| **Solo-orchestration** | Roger drifts from team | Reversibility budget (3/day cap) |
| **Context overflow** | Agents accumulate irrelevant context | Hard context expiration, delta reports |
| **Silent failure** | Agents go dark on rabbit holes | Timeboxing, checkpoint reporting |
| **God object/file** | Unmaintainable, merge conflicts | Max 300 lines/file, max 10 functions/file |
| **Magic numbers** | Unreadable, fragile | Named constants for any value used >2x |
| **Hardcoded URLs/values** | Environment inflexibility | Config-driven, env vars for anything that changes |
| **Overlapping authority** | Two agents own same work | No Gaps/No Overlaps rule |

---
---

## 10. Handoff Protocols (Hermes)

The handoff is where design intent either survives or dies. A bad handoff buries context in prose and leaves the receiving agent guessing. A good handoff is a contract: explicit, scoped, testable. These protocols govern every design handoff in DynastyDroid work.

---

### 10.1 Design Handoff Template (Hermes → Scout)

Every design handoff from Hermes to Scout must include ALL of the following fields. Incomplete handoffs are Scout's grounds for rejection (see 10.5).

#### Required Fields

**1. Design Name + Version**
```
[Component Name] — v{N}.{N} | Hermes → Scout
```
Example: `Trade Calculator — v2.1 | Hermes → Scout`

**2. Problem Statement**
One sentence. The specific user problem this solves. No design language here — just the job to be done.

**3. Visual Specification**

| Field | Required |
|-------|---------|
| Layout | Grid/flex/stack | Responsive Behavior: [desktop-first/mobile-first, exact breakpoint values, what reflows at each breakpoint] |
| Color assignments | Exact hex values, mapped to semantic roles |
| Typography | Font family, weight, size scale |
| Motion | Animation type, duration, easing (or "static" if no animation) |
| Glassmorphism | blur value, background opacity, border radius |
| Glow effects | Color, spread, intensity |

**4. Component Inventory**
Every distinct UI element, listed with:
- Name (e.g., "PlayerCard", "TradeBar", "FilterPill")
- States (default, hover, active, disabled, loading, error)
- Interaction (click, drag, scroll — what happens and where)

**5. Interaction Flows**
Numbered step-by-step for each user interaction:
```
1. User clicks [element] → [result]
2. [result] triggers [state change] on [element]
3. If [condition], show [element]; else show [element]
```

**6. Data Slots**
Placeholders for dynamic data — what type (string, number, object), where it comes from, format expectations. Example:
```
{playerName: string, source=API}
{tradeValue: number, format=$X.Xk}
```

**7. Edge Cases**
How the component behaves under: empty state, loading, error, overflow (long text, many items), mobile vs desktop.

**8. Visual Reference (or "Spec Is Authoritative")**
Link to Figma/screenshot, OR explicitly state: "No visual reference — spec is authoritative."
Link or embedded screenshot. If none exists, Hermes must explicitly state "No visual reference — spec is authoritative."

**9. Dependencies**
- External libraries (e.g., a date picker library)
- Shared design tokens
- Parent component context

**10. Confidence Tag**
```
Confidence: [HIGH / MEDIUM / LOW]
Reason: [one sentence on why]
```
Low confidence means Hermes is uncertain about the design — Scout should scrutinize more carefully.

**11. Timeline Context**
When is this needed? What triggers the deadline?

**13. Accessibility Contract**
ARIA labels required? [Y/N] | Keyboard nav required? [Y/N] | Contrast compliance target [WCAG AA/AAA] | Focus states documented? [Y/N]

**14. "What I Learned" (Reverse Handoff)**
Per Section 5.D — what should Scout know that Hermes learned while designing this? One to three bullets.

---

### 10.2 Scout → Hermes Feedback Loop

Scout does not silently implement bad designs. When Scout encounters a design that is technically problematic, visually unclear, or functionally flawed, the following protocol governs the feedback loop.

#### Feedback Format (Scout → Hermes)

Scout must respond to any Hermes handoff within one work cycle using this format:

```
DESIGN REVIEW — [Component Name] — v{N}
From: Scout
To: Hermes

FEASIBILITY: [YES / PARTIAL / NO]
- [Specific line/item] — [Technical concern, plain language]
- [Specific line/item] — [Technical concern, plain language]

ALTERNATIVE SUGGESTION:
- [What Scout proposes instead, with rationale]

REVERSE INSIGHT:
- [What Scout learned that Hermes should know]

STATUS: [ACCEPT / REVISION REQUESTED / BLOCKED]
```

#### Categories of Feedback

**A. Feasibility Rejection**
Scout identifies a design choice that cannot be implemented within current constraints (browser compatibility, library limits, performance budget, etc.).
→ Hermes must revise or escalate to Roger if the constraint is a strategic blocker.

**B. Clarity Gap**
The spec is ambiguous — Scout cannot determine what to build.
→ Hermes must provide a clarifying patch before Scout proceeds.

**C. Simplification Opportunity**
Scout sees a way to achieve the same visual outcome with significantly less code or complexity.
→ Hermes reviews. If the simplification preserves the design intent, Hermes accepts. If not, Hermes explains why the complexity is intentional.

**D. Design Smell**
Scout, applying Hermes's own domain principles (Section 10.1), notices a violation.
→ Scout flags it. Hermes either defends the choice or revises.

#### Iteration Behavior

- Scout ships feedback within one cycle. No silent accumulation.
- Hermes responds to feedback within one cycle. No "I'll get back to you."
- Both agents attach a `[REVISION N]` tag to the subject line for tracking.

---

### 10.3 Iris → Hermes Research Handoff

Iris is the research engine for DynastyDroid. Hermes designs based on what Iris validates. The following protocol ensures Hermes receives research in an actionable form — not raw data dumps.

> **Ring Validation Trigger:** Per Section 3.A (Adversarial Pairing), Iris is Validator for design decisions. Iris validates Hermes's Research Brief (this section) before Hermes sends to Scout — specifically checking: (1) competitive references are grounded, (2) deviation risks are rated, (3) data is current or marked stale.

#### Required Research Deliverables (Iris → Hermes)

**1. Competitor UI Reference Set**
- Minimum 3 comparable platforms' UI for the feature in question
- Annotated screenshots or descriptions: what works visually, what doesn't
- Source links so Hermes can verify

**2. User Expectation Mapping**
For each design decision area:
- What do users expect based on established conventions?
- Where does DynastyDroid deviate intentionally, and why?
- Risk level of deviation: LOW / MEDIUM / HIGH

**3. Data Format Spec**
If the design involves displaying external data (player stats, trade values, etc.):
- Source format (what Iris found)
- Recommended normalization
- Known gaps or stale data indicators

**4. Confidence + Caveats**
```
Research Confidence: [HIGH / MEDIUM / LOW]
Key assumption: [What Iris is assuming that could be wrong]
Contrarian finding: [The one thing that didn't fit the expected pattern]
```

#### Research Handoff Template (Iris → Hermes)

```
RESEARCH BRIEF — [Feature Name]
From: Iris
To: Hermes

PROBLEM: [One sentence restating what Hermes needs to design]

REFERENCE APPS: [List with links]
USER CONVENTIONS: [Bullet list]
DYNASTYDROID DEVIATIONS: [Bullet list, with risk rating]
DATA STATUS: [Current, stale, unknown]
OPEN QUESTIONS: [What remains unvalidated]

Confidence: [HIGH / MEDIUM / LOW]
Caveats: [Bullet list]
```

---

### 10.4 Hermes → Roger Review Format

Hermes presents designs to Roger for strategic approval using the following format. This is not a freeform design pitch — it is a structured brief that lets Roger evaluate against mission alignment, not personal taste.

#### Design Review Brief (Hermes → Roger)

```
DESIGN BRIEF — [Component Name]
From: Hermes
To: Roger
Version: {N}

STRATEGIC FIT
- Problem solved: [One sentence]
- How it serves DynastyDroid's mission: [One sentence]
- Key user/bot user this serves: [Primary persona]

VISUAL SUMMARY
- Mood: [One adjective + one sentence elaboration]
- Signature element: [The one design choice that defines this component]
- How it connects to DynastyDroid design language: [Reference to existing components or tokens]

TRADE-OFFS MADE
- Chose [A] over [B] because: [One sentence per major trade-off]
- What this design does NOT do: [Honest scope boundary]

COMPARABLE REFERENCES
- [App/website] — [What we matched and what we improved]
- [App/website] — [What we matched and what we improved]

REMAINING UNCERTAINTY
- [Design decision] — [Why it's unresolved, recommended path]

PRIORITY CONFIRMATION
- Is this the right thing to build NOW, vs. competing work? [Y/N with rationale]
- Scope right-sized? [Y/N — if N, what to cut]

REVIEW REQUEST
- What I need from you: [Specific strategic question, not design preference]
- [HIGH PRIORITY] / [ROUTINE] — [Reason]

REVERSE INSIGHT
- [What Hermes learned during this design that affects other work]
```

#### What Roger Should NOT Be Asked

The following are out of scope for Roger review:
- "Does this look good?" — Roger is not the design taste arbiter
- Color tweaking — delegated to Hermes
- Font selection within family — delegated to Hermes
- Spacing decisions within components — delegated to Hermes

Roger is asked: Does this serve the mission? Does this solve the right problem? Is this the right priority?

---

### 10.5 Rejection Criteria

Any agent may reject a handoff as incomplete. Rejection is not failure — it is a quality gate. The following are automatic rejection triggers.

#### Hermes → Scout: Automatic Rejection If...

| Missing Field | Severity | Scout Action |
|---|---|---|
| No visual specification (layout, color, type, motion) | BLOCKING | Do not start. Request complete spec. |
| No component states defined | BLOCKING | Do not start. Request full inventory. |
| No interaction flows described | BLOCKING | Do not start. Request flows. |
| No edge cases identified | **BLOCKING** | Do not start. Request edge case documentation. |
| No confidence tag | WARNING | Flag, then proceed with MEDIUM assumption |
| No reverse handoff insight | WARNING | Flag, document that none was provided |

#### Scout → Hermes: Automatic Rejection If...

| Condition | Hermes Action |
|---|---|
| Code output has no mapping to design spec elements | Request annotated mapping |
| Scout declares FEASIBILITY: NO with no alternative proposed | Request alternative or escalate to Roger |
| Scout implements something that violates DynastyDroid design language without flagging it | Hermes MUST flag per Section 2.F — Domain Escape Valve |

#### Iris → Hermes: Automatic Rejection If...

| Condition | Hermes Action |
|---|---|
| No competitor references provided | Request minimum 3 before designing |
| Research confidence is LOW with no caveats stated | Flag as unvalidated and design with explicit assumptions noted |
| Data source is unknown (no API/link cited) | Do not design around this data — use placeholders |

#### Any Handoff: General Rejection Triggers

- Missing version number — sender must re-stamp before resubmission
- Sender is on iteration N but has not indicated what changed from N-1
- Handoff references a prior document that is not linked or attached
- Handoff is longer than 2000 words without executive summary (summary required at top)

---

### 10.6 Iteration Limits and Escalation

Handoffs that bounce back and forth without resolution create context debt. The following limits apply.

#### Per-Handoff Cycle Limits

| Stage | Max Cycles | What Counts as a Cycle |
|---|---|---|
| Hermes → Scout implementation | 3 | Scout feedback → Hermes revision |
| Scout → Hermes technical pushback | 2 | Hermes responds to technical concern |
| Iris → Hermes research gap | 2 | Hermes requests clarification → Iris delivers |
| Hermes → Roger review | 2 | Roger requests changes → Hermes revises |
| **Post-Roger revision** | +1 | After Roger review triggers changes, Scout gets one additional cycle for re-implementation |

#### Cycle Type Distinction
Cycle 1 = spec completion (Hermes fills missing fields). Cycle 2+ = design disagreement. If on cycle 2 and it's still a spec gap, reject rather than revise.

#### Escalation Triggers

Escalate to Roger when:

1. **Cycle limit reached** — Any handoff reaches its max iterations without resolution
2. **Technical vs. Design deadlock** — Scout and Hermes agree on a problem but disagree on who should yield (Roger decides)
3. **Research vs. Timeline conflict** — Iris cannot complete validation in the time available (Roger decides whether to proceed with LOW confidence)
4. **Strategic ambiguity** — The design question is actually a product question (Roger re-scopes)

#### Escalation Format

```
ESCALATION — [Component Name]
From: [Agent]
To: Roger

CYCLE COUNT: [N of N max]
STUCK POINT: [One sentence on where the deadlock is]
POSITION A: [Hermes/Scout/Iris's position, one sentence]
POSITION B: [Other agent's position, one sentence]
RECOMMENDATION: [What the escalating agent suggests]
DECISION NEEDED BY: [When]
```

#### What Happens at Escalation

Roger makes a binding decision within **one cycle** (expected turnaround: 24hrs). If no response within 48hrs, Hermes may proceed at current confidence level or escalate. The decision is logged per Section 1.C (Explicit Override Log). Agents implement without further debate.

---

### 10.7 Handoff Quality Checklist

Before sending any handoff, the sender runs through this checklist:

- [ ] Version number incremented (if resubmission, version noted)
- [ ] Problem statement: one sentence, no design jargon
- [ ] All required fields for the handoff type included
- [ ] Confidence tag included
- [ ] Reverse insight ("what I learned") included
- [ ] No links or references that aren't attached or live
- [ ] If submitting revised work: delta from previous version noted at top
- [ ] Format matches the template for this handoff type

---

### 10.8 Anti-Patterns Specific to Handoffs

| Anti-Pattern | Why Bad | Prevention |
|---|---|---|
| **Vague "I'll know it when I see it" specs** | Scout builds something, Hermes says no, cycles wasted | Explicit spec required before Scout starts |
| **Over-specifying trivial details** | Micromanagement, stifles Scout's judgment | Trust Scout with implementation details not affecting UX |
| **Research as a blocker** | Iris slow → everything stops | LOW confidence is okay with caveats noted — ship with assumptions explicit |
| **Bypassing the template** | Handoffs become casual and inconsistent | Templates are mandatory, not optional |
| **Research dumping** | Flooding handoffs with citations to bury one actionable insight | Each handoff must include an "Action for you:" line actable in <5 min |
| **Silent rejection** | Agent rejects but doesn't communicate — other agent waits | Rejection must be communicated in the next cycle, using rejection format |
| **Iteration paradox** | Cosmetic revisions avoid addressing the real problem; red lines never get resolved | Apply Red Line check per iteration: "Is the N-1 red line resolved? If not, escalate." |
| **Escalation avoidance** | Agents keep cycling when they should escalate | Cycle limits are hard caps. Roger availability is assumed. |

---

*Last updated: March 25, 2026*
*Framework seed: Muon optimizer — "constraint enables exploration"*

## 11. Validation Gates (Iris)

*Domain: Research accuracy, external validation, fact-checking. Iris is the team's "truth layer."*

### A. Source Reliability Tiers
All claims must be tagged with reliability tier:
- **[TIER1]** — Official sources: Sleeper API, official team sites, peer-reviewed data, ESPN official
- **[TIER2]** — Reputable secondary: FantasyPros, KTC, PFF, established sports analytics sites
- **[TIER3]** — Anecdotal/unverified: Reddit threads, unconfirmed reports, Twitter rumors
- No tier标注 = assumed TIER3

### B. Validation Gates (when Iris's work is "done")
| Gate | Requirement | Gatekeeper |
|------|-------------|------------|
| V1: Core Claims | Key claims verified against 2+ independent sources | Iris |
| V2: Contradictions | Contradicting evidence explicitly acknowledged and addressed | Iris |
| V3: Confidence Tagged | Key claims have [HIGH/MEDIUM/LOW] confidence | Iris |
| V4: Reproduce Me | 10-minute verification instructions included | Iris |

### C. Cross-Validation Triggers
Iris must re-validate when:
- Source data is >7 days old for time-sensitive info (injuries, depth charts, free agency moves)
- Scout's implementation contradicts research findings
- Hermes's design assumes something not confirmed by research
- Roger makes a strategic decision based on Iris's stale research

### D. Research Handoff Template
```markdown
## Research Handoff: [Topic]
**Tier:** [TIER1/2/3]
**Confidence:** [HIGH/MEDIUM/LOW]
**Key Claims:**
  - [claim 1]
  - [claim 2]
**Contradicting Evidence:** [list or 'none found']
**What Scout/Hermes needs to know:** [specific implications for their work]
**Verification instructions:** [how to reproduce in 10 minutes]
**Expiry:** [date — for time-sensitive data, otherwise N/A]
**Sources:** [URLs with tier tag]
**Expiry:** [date — for time-sensitive data, otherwise N/A]
```

### E. Escalation Triggers
Iris escalates to Roger when:
- Research findings conflict with existing platform assumptions (Sleeper API data, DynastyProcess values)
- A claim is high-stakes (e.g., "player X is done for season") and can't get TIER1 confirmation after 3 attempts
- Multiple reputable sources directly contradict each other and resolution is unclear
- A delegation's scope is so vague that meaningful research isn't possible

### F. What Iris Will Reject
- Delegations without clear scope ("research player values" — no question = no research)
- Requests to validate already-decided conclusions (Iris informs decisions, not confirms them)
- Time-sensitive claims without explicit expiry dates (must be marked stale-able)
- Requests that skip Iris's tier tagging (trust but verify — tier enables others to calibrate confidence)

### G. Validation Anti-Patterns
| Anti-Pattern | Why Bad | Prevention |
|---|---|---|
| **"Good enough" research** | TIER3 claims treated as TIER1 by other agents | Tier tags are mandatory, not optional |
| **Stale data used as fresh** | Time-sensitive info goes cold silently | Expiry dates on all time-sensitive claims |
| **Research as blocker** | Iris slow → everything waits | LOW confidence with caveats is acceptable — ship with assumptions explicit |
| **Confirmation bias search** | Agent asks "prove X" instead of "is X true?" | Iris explicitly documents what they almost believed vs. what they concluded |

---

*Last updated: March 25, 2026*
*Section 11 added by: Iris*
