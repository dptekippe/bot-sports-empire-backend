# DynastyDroid Trade Calculator - Project Specification

**Created:** March 17, 2026  
**Version:** 1.0  
**Status:** Planning

---

## 1. Project Overview

### Mission
Transform DynastyDroid from a bot-vs-bot fantasy platform into the premier AI-powered dynasty trade evaluator with narrative intelligence.

### Value Proposition
- **KTC provides numbers** - DynastyDroid provides *stories*
- Combine crowdsourced player values with AI-generated positional analysis and trade narratives
- Sleeper integration for frictionless roster import

### Target Users
- Dynasty fantasy football managers
- Primarily Superflex PPR format (expandable)
- Users who want more than raw trade values

---

## 2. Core Features

### Phase 1 - MVP
| Feature | Description |
|---------|-------------|
| **Sleeper League Import** | Enter Sleeper league ID → fetch roster + settings |
| **Roster Display** | Show roster with DynastyProcess values |
| **Trade Evaluation** | Select players to trade → value comparison |
| **Roger Analysis** | AI-generated narrative (positional needs, win-now vs rebuild) |
| **Roster Assessment** | Identify positional strengths/weaknesses |

### Phase 2 - Enhanced
| Feature | Description |
|---------|-------------|
| **Sleeper Username Lookup** | Find league by username (instead of ID) |
| **Historical Trades** | Track past trades in league |
| **Trade Alerts** | Get notified when trade values shift |
| **Multiple League Support** | Manage multiple leagues |

### Phase 3 - Scale
| Feature | Description |
|---------|-------------|
| **League Leaderboard** | Best traders in community |
| **Trade Market** | Post wanted/offers |
| **Bot Practice** | Internal bots analyze trades for practice |

---

## 3. Data Sources

### Player Values
| Source | Format | Update Frequency | Notes |
|--------|--------|------------------|-------|
| DynastyProcess | CSV/JSON | Weekly | **Primary - compliant** |
| FantasyPros | CSV (exportable) | Monthly | 1QB/SF PPR Consensus |
| Draft Sharks | Web table | Real-time | PPR/custom, format-adjustable |
| Footballguys | CSV (scrape/export) | Monthly | Superflex/PPR/TE-Prem |
| WalterFootball | XLS/CSV download | Preseason/ongoing | Dynasty overall rankings |
| Sleeper | API | Real-time | Roster/player data |

### Value Blending Strategy
- **Primary:** DynastyProcess (compliance-safe)
- **Consensus:** Average of 2-3 sources for "blended value"
- **Range:** max - min for narratives like "Consensus: 45 (range 40-52)"
- **Skip:** Paid sources (DLF) for MVP

### Sleeper API Endpoints
```
GET /league/{league_id}          - League settings
GET /league/{league_id}/rosters   - Team rosters
GET /league/{league_id}/users     - Managers
GET /league/{league_id}/matchups - Weekly matchups
GET /players/nfl                  - All players
```

---

## 4. Technical Architecture

### Stack
- **Backend:** FastAPI (existing)
- **Database:** PostgreSQL (existing)
- **Frontend:** HTML/JS (new trade calculator)
- **Deployment:** Render

### Data Flow
```
Sleeper API → SleeperClient → League/Roster Data
                                      ↓
DynastyProcess CSV → Player Values → Database
                                      ↓
Roster + Values → Trade Evaluation → Roger Analysis → UI
```

### Key Components (New)
```
app/
├── integrations/
│   └── sleeper_client.py      [EXTEND] League/roster endpoints
├── services/
│   ├── dynasty_values.py      [NEW] DynastyProcess data loader
│   ├── trade_evaluator.py     [NEW] Trade analysis engine
│   └── roster_analyzer.py     [NEW] Positional strength
├── api/endpoints/
│   ├── leagues_sleeper.py     [NEW] Sleeper league fetch
│   ├── trade.py               [NEW] Trade evaluation
│   └── roster.py              [NEW] Roster analysis
└── static/
    └── trade-calculator.html  [NEW] UI
```

### Reuse Existing
- `app/integrations/sleeper_client.py` - Extend with league/roster
- `app/models/player.py` - Add dynasty_value field
- `app/services/scoring_engine.py` - Leverage scoring logic

### Data Schema: player_values Table
```sql
CREATE TABLE player_values (
    id SERIAL PRIMARY KEY,
    player_id VARCHAR(20) REFERENCES players(player_id),
    source VARCHAR(50),           -- DynastyProcess, FantasyPros, etc.
    value INTEGER,
    format VARCHAR(20),            -- PPR, HPPR, SF, 1QB
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Automation Strategy
- **Cron weekly:** Fetch DynastyProcess CSV → parse → upsert to player_values
- **GitHub Actions:** Existing for DynastyProcess (reuse pattern)
- **Loader script:** Fetch/parse into player_values table with source, value, date

---

## 5. Trade Evaluation Logic

### Win-Now vs Rebuild Detection

**Team Age Formula:**
```
average_age = sum(player_ages) / roster_count
```

**Classification:**
| Average Age | Classification |
|-------------|----------------|
| >27 | Win-Now (contender) |
| 24-27 | Neutral |
| <24 | Rebuild (retooling) |

**Playoff Probability:**
- Use historical matchups data from Sleeper
- Calculate win/loss record through Week 12
- If Win% >60% = Win-Now
- If Win% <40% = Rebuild

**Draft Pick Inventory:**
- Count future picks owned
- >3 first-round picks in next 2 years = Rebuild tilt
- <1 first-round picks = Win-Now urgency

### Value Calculation
```
Trade Value = (Outgoing Players Value) - (Incoming Players Value)
Positional Need Score = Team Strength at Position / League Average
```

### Roger Narrative Triggers
| Scenario | Narrative Angle |
|----------|-----------------|
| High value + positional need | "Bolsters win-now WR corps" |
| Low value + positional surplus | "Depth add, future pick capital" |
| Rebuild team + aging player | "Contender flip, collects picks" |
| Contender + young asset | "Win-now move, maximizes window" |

### Win-Now vs Rebuild Detection
- Calculate team age average
- Compare playoff probability (if historical data)
- Assess draft pick inventory

---

## 6. UI/UX Design

### Reference: KTC (KeepTradeCut)
- Minimal, data-focused
- Search-driven interface
- Dark theme
- Quick value lookups

### Mobile/Responsive Requirements
- **Web-first design** - Render deploys web-first
- **CSS Grid/Flexbox** - Fluid layouts
- **Touch-friendly** - Min 44px tap targets
- **Breakpoints:** Mobile (<768px), Tablet (768-1024px), Desktop (>1024px)
- **Single column** on mobile, multi-column desktop

### MVP Layout
```
┌─────────────────────────────────────────────┐
│ [League ID Input] [Import]                  │
├─────────────────────────────────────────────┤
│ MY ROSTER          │   PROPOSE TRADE       │
│ - Player (Value)   │   [Select Players]    │
│ - Player (Value)   │                       │
│ - ...              │   TARGET PLAYERS       │
│                    │   - [Search]          │
│ STRENGTHS: WR, TE │   - Player (Value)    │
│ WEAKNESSES: RB    │                       │
├─────────────────────────────────────────────┤
│ ROGER ANALYSIS                             │
│ "This trade adds elite WR depth but..."    │
└─────────────────────────────────────────────┘
```

---

## 7. Roadmap

### Week 1-2: Foundation
- [ ] Extend SleeperClient with league/roster endpoints
- [ ] Create DynastyProcess data loader
- [ ] Add dynasty_value field to Player model
- [ ] Build league import endpoint

### Week 3: Core Features
- [ ] Roster display with values
- [ ] Trade input interface
- [ ] Trade evaluation logic
- [ ] Roger narrative generation

### Week 4: Polish
- [ ] Basic UI (KTC-style)
- [ ] Error handling
- [ ] Testing with real leagues
- [ ] Deploy to staging

### Future Phases
- Sleeper username lookup
- Multiple league support
- Trade history
- Community features

---

## 8. Open Questions

1. **DynastyProcess refresh** - Manual upload or automated cron?
2. **Value source** - Start with just DynastyProcess, add others later?
3. **Monetization** - Free tier scope, paid features?
4. **KTC data** - Use historical CSVs for historical context?

---

## 9. Success Metrics

| Metric | Target |
|--------|--------|
| Sleeper import success rate | >95% |
| Trade evaluation load time | <2s |
| Roger narrative relevance | >80% helpful (user feedback) |
| Weekly active users (launch) | 100 |

---

*Document Status: Draft - Pending Review*
