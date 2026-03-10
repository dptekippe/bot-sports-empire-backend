---
name: verify-all-information
description: Verify all information before analysis - facts, claims, assumptions, technical details, and context. Prevents GIGO.
triggers: any reasoning, planning, decision, evaluation, or analysis task
---

# Verify All Information Skill

**Universal Step 0:** Before any analysis, decision tree, metacognition, or reasoning — verify everything.

This is NOT limited to fantasy football or any single domain. It applies to ALL information.

## When to Trigger

Trigger on ANY task involving:
- Reasoning or planning
- Decision making or evaluation
- Answering questions with factual claims
- Analyzing provided information
- Debugging or technical work
- Historical or factual queries
- Trade evaluations
- Code reviews
- Any task where you form a conclusion

## Universal Information Categories

| Category | Examples | Verification Methods |
|----------|----------|---------------------|
| **Facts/Claims** | "X is true", "Y happened" | Web search, 2+ sources |
| **Values/Stats** | Player stats, prices, rankings | KTC, FantasyPros, official docs |
| **Technical** | API status, library versions, syntax | Docs, GitHub, runtime checks |
| **Historical** | Dates, events, timelines | Wikipedia, archives, primary sources |
| **People/Context** | Relationships, preferences, agreements | Memory, user confirmation |
| **Domain Knowledge** | Rules, policies, workflows | Official docs, league settings |
| **Code/Implementation** | Function exists, endpoint works | Docs, test, grep source |
| **Opinions/Analysis** | "X is better than Y" | Multiple viewpoints, data |

## Workflow

### 1. Scan All Information
Before processing, identify EVERY piece of information you'll use:
- Facts stated in the query
- Assumptions you're making
- Data provided by user
- Claims from memory
- Technical details referenced

### 2. Categorize Each Item
Sort each piece into the table above. Ask: "What kind of information is this?"

### 3. Verify According to Type
| Type | Minimum Sources | Method |
|------|-----------------|--------|
| Facts/Claims | 2+ independent | Web search |
| Values/Stats | 2+ | Primary domain source + corroborating |
| Technical | 1 (docs) + 1 (test) | Browser/docs + runtime |
| Historical | 2+ | Wikipedia + primary source |
| People/Context | Memory check + ask | MEMORY.md + confirm with user |
| Domain Knowledge | 1 official + 1 practical | Docs + example |
| Code/Implementation | Source + execution | Grep + test |
| Opinions | Flag as opinion | State source, don't present as fact |

### 4. Assign Confidence

| Confidence | Criteria | Action |
|------------|----------|--------|
| **HIGH** | 2+ independent sources agree, recent | Use freely |
| **MEDIUM** | 1 strong source, plausible | Use with flag |
| **LOW** | Unverified, stale (>6mo), conflicting | STOP - ask user |
| **OPINION** | Subjective statement | Label as opinion |

### 5. Output Verification Stamp

```
### Step 0: Information Verification

| Information | Category | Verified | Confidence | Sources |
|-------------|----------|----------|------------|---------|
| "Jefferson is WR1" | Value/Stat | ❌ WR15 | LOW | KTC, FantasyPros |
| "Bijan > Jefferson" | Value/Stat | ✅ RB4 > WR15 | HIGH | KTC |
| API endpoint exists | Technical | ✅ | HIGH | /docs + curl test |

VERIFIED: Bijan value confirmed, API exists
UNVERIFIED: Jefferson WR1 status
CONFLICTING: None
ACTION: Proceed with Bijan data; flag Jefferson uncertainty
```

### 6. Decision Gate

- **HIGH confidence majority:** Proceed with analysis
- **MEDIUM items:** Flag explicitly in output
- **LOW/UNVERIFIED items:** STOP and ask user:
  - "I couldn't verify [X]. Assume it's true?"
  - "Data gap on [Y]. How to proceed?"
  - "Conflicting sources on [Z]. Which do you trust?"

## Source Authority Matrix

### High Authority (Primary)
- Official documentation (docs.site, developer APIs)
- Primary data sources (KTC, NFL.com, PFF)
- Wikipedia (for historical facts)
- GitHub (for code)
- Official statements (press releases, X from verified accounts)

### Medium Authority (Secondary)
- Community sources (Reddit, forums)
- News articles (secondary reporting)
- Expert opinions (analysts, respected sources)
- General web results

### Low Authority (Flag)
- Single source without corroboration
- Stale information (>6 months for dynamic topics)
- Social media unverified claims
- Outdated documentation

## Source Selection by Information Type

**KEY PRINCIPLE: Match source to the volatility/timeliness of the topic.**

| Information Type | Best Sources | Why |
|----------------|---------------|-----|
| **Fast-moving/Prices** | X, TradingView, KTC, Bloomberg Terminal, Yahoo Finance | Real-time ticks; Bloomberg/Yahoo for alerts/charts |
| **Breaking News** | X, Reuters, AP, BBC, Ground News | Speed + aggregation; BBC for global balance |
| **Stable Facts** | Wikipedia, Official docs/sites (.gov/.edu), FactCheck.org | Curated/peer-reviewed; FactCheck.org debunks claims |
| **Historical** | Wikipedia + primary (archives.gov, JSTOR), Google Ngram Viewer | Context/depth; Ngram for trends |
| **Player Values** | KTC, FantasyPros, Dynasty League Football (DLF), Establish The Run | Dynasty consensus; FP/DLF for rankings/models |
| **Technical Docs** | Official docs, GitHub, ReadTheDocs, MDN Web Docs | Authoritative; MDN for web/JS |
| **Code/Libraries** | GitHub, Stack Overflow, PyPI/NPM trends, Official changelogs | Source + community; trends for popularity |
| **Expert Analysis** | Reddit (r/fantasyfootball, r/devops), Substack newsletters, McKinsey/BCG reports | Community wisdom; Substack for niche pros |
| **People/Context** | Memory + user, LinkedIn, Crunchbase | Personal; Crunchbase for company bios |

### Source Selection Decision Tree

```
Is the topic fast-moving or time-sensitive?
├── YES → Use X (Twitter) first for live data
│   └── Then: Add news for context
└── NO → Is it historical or stable?
    ├── YES → Wikipedia + primary sources
    └── NO → Is it technical?
        ├── YES → Official docs + GitHub
        └── NO → Domain-specific source (KTC, etc.)
```

## Verification Methods

### Web Search
- Use `batch_web_search` for quick verification
- Target authoritative sources first
- Note: "site:keeptradecut.com" for specific sites

### Browser
- Use `browser` to read docs directly
- Verify API endpoints with live calls
- Check current status pages

### Memory
- Always check MEMORY.md for prior knowledge
- Flag contradictions between memory and new info
- Note: Memory may be stale - verify if critical

### Runtime/Execution
- For code: run the code, test the endpoint
- For APIs: curl or hit the endpoint
- Don't assume - verify

## Anti-Patterns (STOP Doing)

- ❌ "This seems right" - verify before proceeding
- ❌ "User said X" - verify user claims too
- ❌ "I remember X" - memory may be stale, verify
- ❌ "It's obvious" - nothing is obvious, verify
- ❌ "Only applies to fantasy football" - applies to EVERYTHING
- ❌ "I'll verify later" - verify NOW, not after analysis
- ❌ Presenting opinions as facts
- ❌ Using single-source information as absolute truth
- ❌ Using stale news for fast-moving topics (check X first)
- ❌ Using slow sources (Wikipedia) for live prices/movement
- ❌ Ignoring the source-type match principle

## Domain Examples

### Fantasy Football
```
Query: "Trade Jefferson for Bijan + 1st"
Information to verify:
- Jefferson current value → KTC, FantasyPros
- Bijan current value → KTC, FantasyPros  
- 1st round value → KTC rookie picks
- Jefferson injury status → X, ESPN
Result: Use verified values in analysis
```

### Technical/Debugging
```
Query: "Fix the API 500 error"
Information to verify:
- API endpoint exists → /docs shows it
- Database connected → health endpoint
- Error source → logs, test request
Result: Use verified technical state before debugging
```

### Historical/General
```
Query: "When was X invented?"
Information to verify:
- Date → Wikipedia + primary source
- Context → additional sources
Result: Use verified date, flag if conflicting
```

### People/Relationships
```
Query: "User prefers dark mode"
Information to verify:
- Check USER.md for preferences
- Check MEMORY.md for past conversations
- Ask user if unsure
Result: Don't assume - verify user preferences
```

## Integration

This skill is **Step 0** — it runs BEFORE:
- Decision trees
- Metacognition
- VPP scoring
- Any analysis or reasoning
- Any recommendation or advice

If verification fails:
1. STOP analysis
2. Present verification stamp with gaps
3. Ask user how to proceed
4. Do NOT proceed with unverified information

## Reference

- Sources by domain: See tables above
- Search best practices: Use site: operators, target authoritative sources first
- Memory check: Always grep MEMORY.md for relevant context
