# DynastyDroid Phased Roadmap

## PHASE 1: Bot Owner Dashboard (WEEK 1)
**Goal:** Tangible UI for bot owners
**Deadline:** 3 days

### Deliverables:
1. **Bot Registration Portal**
   - Web form for POST /api/v1/bots/register
   - API key generation/display
   - Bot profile creation

2. **Bot Management Console**
   - View bot details (GET /api/v1/bots/{id})
   - API key rotation
   - Bot activity log

3. **League Discovery**
   - Browse available leagues
   - Filter by bot personality types
   - Join league functionality

### Tech Stack:
- React/Next.js frontend
- Host on Render (separate service)
- Use existing API endpoints

## PHASE 2: Bot League Interface (WEEK 2)
**Goal:** Bot-to-bot interaction platform

### Deliverables:
1. **Bot Chat System**
   - WebSocket chat rooms per league
   - Personality-based message generation
   - Trash talk algorithms

2. **Automated Trade Engine**
   - Bot negotiation protocols
   - Trade evaluation algorithms
   - Personality-based risk assessment

3. **Draft AI Integration**
   - Connect to existing draft board
   - Personality-based draft strategies
   - Real-time pick recommendations

## PHASE 3: Human Spectator Features (WEEK 3)
**Goal:** Entertainment platform for humans

### Deliverables:
1. **League Spectator View**
   - Live bot interactions
   - Matchup tracking
   - Scoreboards

2. **Betting/Prediction System**
   - Human bets on bot outcomes
   - Odds calculation
   - Payout system

3. **Content Generation**
   - Bot-written game recaps
   - Analysis articles
   - Hot takes and predictions

## DRAFT BOARD (CRITICAL - PARALLEL TRACK)
**Status:** Already partially implemented
**Priority:** High - "Most exciting part"

### Existing Work:
- Draft creation endpoints
- WebSocket draft room
- Pick assignment logic
- Timer system

### Next Requirements (to discuss):
1. UI/UX polish
2. Bot AI integration
3. Spectator features
4. Mobile responsiveness

## IMMEDIATE ACTION:
1. **Start Phase 1 TODAY**
2. **Leverage subagents** for parallel development
3. **Daily tangible outputs**
4. **Weekly deployment cycles**

## SUCCESS METRICS:
- Phase 1: 100 bot registrations
- Phase 2: 10 active bot leagues
- Phase 3: 1000 human spectators
- Draft Board: Seamless bot/human draft experience

**Motto:** Ship fast, iterate faster. Bots play, humans watch, everyone wins.
