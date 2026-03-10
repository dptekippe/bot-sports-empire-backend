# DRAFT BOARD SUB-AGENT PLAN

## Mission
Create an interactive Draft Board component for DynastyDroid that rivals Sleeper's draft experience.

## Technical Stack
- **Frontend:** React + Vite (existing)
- **API:** bot-sports-empire.onrender.com
- **Styling:** CSS matching DynastyDroid theme (dark mode, green/blue accents)

## Features to Build

### 1. Draft Board Grid
- Visual pick order display (snake draft format)
- Team/bot logos and names
- Round-by-round layout
- Current pick highlight

### 2. Timer System
- Countdown timer for each pick
- Pick timer settings (30s, 60s, 120s, custom)
- Auto-pick on timeout
- Pause/resume for commissioner

### 3. Commissioner Controls
- Make pick (select player)
- Skip pick
- Edit draft settings
- Add/remove teams

### 4. Player Search
- Search by name
- Filter by position
- View player details
- Draftable players list

### 5. Real-Time Updates
- Poll API every 5 seconds
- Or WebSocket for live updates
- Optimistic UI updates

## API Endpoints Needed (may need to create)

```python
# Draft endpoints to create
POST /api/v1/drafts - Create new draft
GET /api/v1/drafts - List drafts
GET /api/v1/drafts/{id} - Get draft details
POST /api/v1/drafts/{id}/pick - Make a pick
POST /api/v1/drafts/{id}/settings - Update draft settings
GET /api/v1/drafts/{id}/players - Get draftable players
```

## Files to Create

1. **frontend/src/components/DraftBoard.jsx** - Main draft board component
2. **frontend/src/components/DraftBoard.css** - Draft board styles
3. **frontend/src/components/PlayerCard.jsx** - Player display component
4. **frontend/src/components/Timer.jsx** - Pick timer component
5. **frontend/src/components/CommissionerControls.jsx** - Admin controls

## API Enhancement (Backend)

Add to app_absolute_minimal.py:

```python
# Draft endpoints
drafts_storage = {}

@app.post("/api/v1/drafts")
async def create_draft(draft: DraftCreate):
    # Create new draft with settings
    
@app.get("/api/v1/drafts/{draft_id}")
async def get_draft(draft_id: str):
    # Get draft with picks, timer, teams
    
@app.post("/api/v1/drafts/{draft_id}/pick")
async def make_pick(draft_id: str, bot_id: str, player_id: str):
    # Record a pick
    
@app.get("/api/v1/drafts/{draft_id}/players")
async def get_draft_players(draft_id: str):
    # Get available players to draft
```

## Visual Design

- **Dark theme:** #0a0a0a background
- **Primary accent:** #00ff88 (green)
- **Secondary accent:** #0088ff (blue)
- **Cards:** Dark gray with subtle borders
- **Typography:** Clean sans-serif (Inter, Roboto)

## Progress Checklist

- [ ] Create draft API endpoints
- [ ] Build DraftBoard component
- [ ] Add timer functionality
- [ ] Implement player search
- [ ] Add commissioner controls
- [ ] Connect to API
- [ ] Test with real data
- [ ] Deploy to dynastydroid-dashboard

## Notes for Sub-Agent

1. Start with API endpoints - frontend needs data
2. Keep component modular
3. Use existing CSS variables for theming
4. Test incrementally
5. Deploy frequently to verify

## Success Metrics

- Draft board loads within 2 seconds
- Timer updates smoothly
- Picks record correctly
- Works on mobile and desktop
