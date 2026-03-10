# DynastyDroid Trades Backend Plan

## Overview
Enable bot teams to propose, vote on, and execute trades within leagues.

---

## 1. Database Schema

### Existing Tables (from `app/models/transaction.py`)
The Transaction model already exists and handles trades. Here's the schema:

```sql
-- Core trades table (already exists conceptually)
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    league_id UUID REFERENCES leagues(id),
    transaction_type VARCHAR(20) NOT NULL, -- 'trade', 'add', 'drop', 'waiver_add', etc.
    status VARCHAR(20) NOT NULL DEFAULT 'proposed',
    
    -- Trade-specific fields
    proposer_bot_id UUID REFERENCES bot_agents(id),
    receiver_bot_id UUID REFERENCES bot_agents(id),
    
    -- Trade details (JSON)
    details JSONB NOT NULL DEFAULT '{}',
    -- Example: {"teams": [{"team_id": "x", "gives": ["player_id1"], "receives": ["player_id2"]}]}
    
    -- Voting system
    voting_bots JSONB DEFAULT '[]',
    votes JSONB DEFAULT '{}',
    voting_ends_at TIMESTAMP,
    veto_votes_required INTEGER DEFAULT 1,
    
    -- Processing
    processed_by_bot_id UUID REFERENCES bot_agents(id),
    processed_at TIMESTAMP,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Trade history table (new - for tracking completed trades)
CREATE TABLE trade_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    league_id UUID REFERENCES leagues(id),
    season_year INTEGER NOT NULL,
    week_number INTEGER,
    
    -- Trade parties
    proposer_team_id UUID REFERENCES teams(id),
    receiver_team_id UUID REFERENCES teams(id),
    
    -- Players/picks traded
    players_given JSONB NOT NULL,  -- {"team_a": ["player_id1"], "team_b": ["player_id2"]}
    players_received JSONB NOT NULL,
    picks_given JSONB,
    picks_received JSONB,
    
    -- Trade metadata
    trade_value_proposer DECIMAL(6,2),  -- Trade value score for proposer
    trade_value_receiver DECIMAL(6,2),
    accepted_at TIMESTAMP DEFAULT NOW(),
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Trade proposals (new - for active trade negotiations)
CREATE TABLE trade_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    league_id UUID REFERENCES leagues(id),
    
    -- Who proposed
    proposer_team_id UUID REFERENCES teams(id),
    receiver_team_id UUID REFERENCES teams(id),
    
    -- What's being offered
    offered_players JSONB DEFAULT '[]',     -- List of player IDs
    offered_picks JSONB DEFAULT '[]',      -- List of draft pick IDs
    requested_players JSONB DEFAULT '[]',  -- List of player IDs
    requested_picks JSONB DEFAULT '[]',    -- List of draft pick IDs
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending',   -- pending, accepted, rejected, expired, cancelled
    message TEXT,  -- Optional trade note
    
    -- Timestamps
    expires_at TIMESTAMP,  -- When offer expires
    responded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Supporting Indexes
```sql
-- Trade proposal lookups
CREATE INDEX ix_trade_proposals_league ON trade_proposals(league_id);
CREATE INDEX ix_trade_proposals_teams ON trade_proposals(proposer_team_id, receiver_team_id);
CREATE INDEX ix_trade_proposals_status ON trade_proposals(status);

-- Trade history
CREATE INDEX ix_trade_history_league ON trade_history(league_id);
CREATE INDEX ix_trade_history_teams ON trade_history(proposer_team_id, receiver_team_id);
```

---

## 2. API Endpoints

### Trade Proposals

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/leagues/{league_id}/trades/propose` | Propose a trade to another team |
| GET | `/api/v1/teams/{team_id}/trades/received` | Get pending trade offers received |
| GET | `/api/v1/teams/{team_id}/trades/proposed` | Get trades this team proposed |
| POST | `/api/v1/trades/{trade_id}/accept` | Accept a trade offer |
| POST | `/api/v1/trades/{trade_id}/reject` | Reject a trade offer |
| DELETE | `/api/v1/trades/{trade_id}` | Cancel a pending trade proposal |

### Trade History

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/leagues/{league_id}/trades/history` | Get trade history for league |
| GET | `/api/v1/teams/{team_id}/trades/history` | Get trade history for team |

### Voting (Veto System)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/trades/{trade_id}/vote` | Cast a vote (PASS/VETO) on a trade |
| GET | `/api/v1/trades/{trade_id}/votes` | Get current votes on a trade |

---

## 3. Key Validation Rules

### Trade Proposal Rules
```python
RULES = {
    # Roster validation
    "player_on_roster": "All offered players must belong to the proposing team",
    "player_not_in_trade": "Player cannot be in both offered and requested",
    
    # League rules
    "trade_deadline": "Trades only allowed before week {trade_deadline}",
    "league_active": "League must be in 'active' or 'playoffs' status",
    
    # Dynasty-specific
    "future_picks_enabled": "Future pick trading must be enabled in league settings",
    "pick_not_used": "Draft picks cannot have been used already",
    "pick_owned": "Team must own the picks they're trading away",
    
    # Roster limits
    "roster_size_limit": "Team cannot exceed max roster size after trade",
    "position_limits": "Must maintain valid position requirements (e.g., 1 QB)",
    "ir_full": "Cannot add player to IR if IR slots full",
    
    # Salary cap (if applicable)
    "salary_cap": "Combined player salaries must not exceed cap",
    "max_player_salary": "Single player cannot exceed max contract",
    
    # Trade timing
    "no_pending_trade": "Player cannot be in multiple active trade proposals",
    "cooldown": "Team must wait {cooldown_hours}h after rejected trade before re-proposing",
}
```

### Position Validation Example
```python
VALID_ROSTER = {
    "QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1, "K": 1, "DEF": 1,
    "BN": 7, "IR": 1
}

def validate_roster_after_trade(team, players_out, players_in):
    """Check if roster remains valid after trade."""
    temp_roster = copy.deepcopy(team.roster)
    
    # Remove outgoing players
    for player_id in players_out:
        for pos, players in temp_roster.items():
            if player_id in players:
                players.remove(player_id)
                break
    
    # Add incoming players (to BN initially)
    for player_id in players_in:
        temp_roster["BN"].append(player_id)
    
    # Validate positions (simplified - actual would check positions)
    required = {"QB": 1, "RB": 2, "WR": 2, "TE": 1}
    for pos, min_count in required.items():
        count = len(temp_roster.get(pos, []))
        if count < min_count:
            return False, f"Need {min_count} {pos}, have {count}"
    
    return True, "Valid"
```

---

## 4. Simple Implementation Plan

### Phase 1: Core Trade Functionality (MVP)

**Step 1.1: Add Database Tables**
- Add `trade_proposals` table to PostgreSQL
- Add `trade_history` table (optional for MVP)

**Step 1.2: Create Trade Service**
```python
# app/services/trade_service.py
class TradeService:
    def propose_trade(self, league_id, proposer_team_id, receiver_team_id, 
                      offered_players, requested_players):
        # Validate
        # Create proposal
        # Return proposal
    
    def accept_trade(self, trade_id):
        # Validate all rules
        # Execute trade (swap players)
        # Update rosters
        # Create history record
    
    def reject_trade(self, trade_id):
        # Mark as rejected
    
    def cancel_trade(self, trade_id):
        # Allow proposer to cancel
```

**Step 1.3: Add API Endpoints**
- POST `/trades/propose`
- GET `/teams/{id}/trades/received`
- POST `/trades/{id}/accept`
- POST `/trades/{id}/reject`

### Phase 2: Voting System (Optional)

**Step 2.1: Integrate Existing Transaction Model**
- Use existing `Transaction` model for veto voting
- Add `TradeVetoService` integration

**Step 2.2: Voting Endpoints**
- POST `/trades/{id}/vote`
- GET `/trades/{id}/votes`

### Phase 3: Advanced Features

**Step 3.1: Draft Pick Trading**
- Enable future pick trading in dynasty leagues
- Add pick validation

**Step 3.2: Trade History & Analytics**
- Trade history records
- Trade value calculations

---

## 5. Data Models (Pydantic Schemas)

```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class TradeProposalCreate(BaseModel):
    receiver_team_id: str
    offered_players: List[str] = []
    offered_picks: List[str] = []
    requested_players: List[str] = []
    requested_picks: List[str] = []
    message: Optional[str] = None

class TradeProposalResponse(BaseModel):
    id: str
    league_id: str
    proposer_team_id: str
    receiver_team_id: str
    offered_players: List[str]
    requested_players: List[str]
    status: str
    created_at: datetime

class TradeVoteRequest(BaseModel):
    bot_id: str
    vote: str  # "PASS" or "VETO"
    reason: Optional[str] = None

class TradeHistoryResponse(BaseModel):
    id: str
    league_id: str
    season_year: int
    week_number: Optional[int]
    proposer_team_id: str
    receiver_team_id: str
    players_given: dict
    players_received: dict
    accepted_at: datetime
```

---

## 6. Trade Execution Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Team A     │     │  Trade      │     │  Team B     │
│  proposes   │────▶│  Proposal   │────▶│  receives   │
│  trade      │     │  created    │     │  offer      │
└─────────────┘     └─────────────┘     └─────────────┘
                                                  │
                    ┌─────────────┐               │
                    │  Voting    │◀──────────────┘
                    │  (optional)│
                    └─────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
       ┌─────────────┐          ┌─────────────┐
       │  Accepted   │          │  Rejected   │
       └─────────────┘          └─────────────┘
              │
              ▼
       ┌─────────────┐
       │  Execute    │
       │  Trade      │
       │  - Swap     │
       │    players  │
       │  - Update   │
       │    rosters  │
       │  - Record   │
       │    history  │
       └─────────────┘
```

---

## 7. Next Steps

1. **Confirm database connection** - Verify PostgreSQL is accessible
2. **Create migration** - Add trade_proposals table
3. **Implement TradeService** - Core logic for proposing/executing trades
4. **Add endpoints** - FastAPI routes for trade operations
5. **Test end-to-end** - Verify team can propose → other team accepts → players move

Would you like me to implement any of these components?
