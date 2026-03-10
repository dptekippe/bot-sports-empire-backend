# 🏈 Draft System Database Schema Additions

## 📅 **Created**
2026-02-04 by Roger the Robot

## 🎯 **Purpose**
Extend existing Bot Sports Empire database to support intelligent draft system with sub-agent architecture.

## 🗃️ **Existing Tables (From PROJECT_STATUS.md)**

### **Core Tables We'll Reference:**
1. **`bot_agents`** - With full mood/personality system
2. **`leagues`** - League definitions with `league_type` (FANTASY/DYNASTY)
3. **`teams`** - Team rosters linked to bots
4. **`players`** - NFL player data
5. **`scoring_rules`** - League-specific scoring configurations
6. **`league_settings`** - Already has dynasty-specific fields

## 🆕 **New Tables Required**

### **1. `drafts` - Draft Sessions**
```sql
CREATE TABLE drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    league_id UUID NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    draft_type VARCHAR(20) NOT NULL CHECK (draft_type IN ('STARTUP', 'ROOKIE', 'SUPPLEMENTAL')),
    status VARCHAR(20) NOT NULL DEFAULT 'SCHEDULED' 
        CHECK (status IN ('SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
    draft_order JSONB NOT NULL,  -- Array of team IDs in draft order
    current_pick_number INTEGER DEFAULT 1,
    current_team_id UUID REFERENCES teams(id),
    timer_end TIMESTAMP,  -- When current pick timer expires
    settings JSONB NOT NULL DEFAULT '{}',  -- Draft-specific settings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    INDEX idx_drafts_league_id (league_id),
    INDEX idx_drafts_status (status),
    INDEX idx_drafts_created_at (created_at DESC)
);
```

### **2. `draft_picks` - Individual Picks**
```sql
CREATE TABLE draft_picks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id UUID NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
    pick_number INTEGER NOT NULL,
    team_id UUID NOT NULL REFERENCES teams(id),
    bot_id UUID NOT NULL REFERENCES bot_agents(id),
    player_id UUID REFERENCES players(id),  -- NULL for skipped picks
    skipped BOOLEAN DEFAULT FALSE,
    auto_picked BOOLEAN DEFAULT FALSE,  -- System picked due to timeout
    decision_data JSONB,  -- Full DraftDecision object from sub-agents
    reasoning TEXT,  -- Natural language explanation
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    pick_time_ms INTEGER,  -- How long bot took to decide (ms)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure unique pick number per draft
    UNIQUE(draft_id, pick_number),
    
    -- Indexes for queries
    INDEX idx_draft_picks_draft_id (draft_id),
    INDEX idx_draft_picks_team_id (team_id),
    INDEX idx_draft_picks_bot_id (bot_id),
    INDEX idx_draft_picks_player_id (player_id),
    INDEX idx_draft_picks_pick_number (pick_number)
);
```

### **3. `draft_state` - Real-time Draft State (Cached)**
```sql
CREATE TABLE draft_state (
    draft_id UUID PRIMARY KEY REFERENCES drafts(id) ON DELETE CASCADE,
    available_players JSONB NOT NULL DEFAULT '[]',  -- Array of player IDs still available
    team_rosters JSONB NOT NULL DEFAULT '{}',  -- Map of team_id -> current roster player IDs
    pick_history JSONB NOT NULL DEFAULT '[]',  -- Last 20 picks for context
    timer_started_at TIMESTAMP,
    timer_duration_seconds INTEGER DEFAULT 90,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Refresh this table frequently during drafts
    INDEX idx_draft_state_last_activity (last_activity DESC)
);
```

### **4. `player_projections` - Cached Player Data**
```sql
CREATE TABLE player_projections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID NOT NULL REFERENCES players(id),
    season INTEGER NOT NULL,  -- e.g., 2026
    week INTEGER,  -- NULL for season-long projections
    source VARCHAR(50) NOT NULL,  -- 'SLEEPER', 'CUSTOM', 'MOCK'
    projected_points FLOAT,
    injury_risk FLOAT CHECK (injury_risk >= 0 AND injury_risk <= 1),
    consistency_score FLOAT CHECK (consistency_score >= 0 AND consistency_score <= 1),
    upside_score FLOAT CHECK (upside_score >= 0 AND upside_score <= 1),
    data_json JSONB NOT NULL DEFAULT '{}',  -- Full projection data
    valid_until TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- One projection per player/season/week/source
    UNIQUE(player_id, season, week, source),
    
    -- Indexes for queries
    INDEX idx_player_projections_player_id (player_id),
    INDEX idx_player_projections_season (season),
    INDEX idx_player_projections_valid_until (valid_until),
    INDEX idx_player_projections_source (source)
);
```

## 🔄 **Extensions to Existing Tables**

### **1. `bot_agents` - Add Draft Strategy Preferences**
```sql
-- Add column to existing bot_agents table
ALTER TABLE bot_agents ADD COLUMN draft_strategy_preferences JSONB DEFAULT '{
    "risk_tolerance": 0.5,
    "injury_aversion": 0.5,
    "recency_bias": 0.5,
    "team_loyalty": 0.0,
    "contrarian_tendency": 0.3,
    "patience_level": 0.5,
    "preferred_positions": ["RB", "WR", "QB", "TE"],
    "avoid_positions": [],
    "favorite_teams": [],
    "avoid_teams": []
}';
```

### **2. `leagues` - Add Draft Settings**
```sql
-- Add column to existing leagues table  
ALTER TABLE leagues ADD COLUMN draft_settings JSONB DEFAULT '{
    "pick_time_limit_seconds": 90,
    "auto_pick_enabled": true,
    "auto_pick_strategy": "BEST_AVAILABLE",
    "trading_enabled_during_draft": false,
    "pause_rules": {
        "max_pauses_per_team": 3,
        "pause_duration_minutes": 10
    }
}';
```

## 🎭 **Enums Needed**

### **Draft-Related Enums:**
```python
# In app/models/draft.py (extending existing)
class DraftType(str, Enum):
    STARTUP = "startup"
    ROOKIE = "rookie"
    SUPPLEMENTAL = "supplemental"

class DraftStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class AutoPickStrategy(str, Enum):
    BEST_AVAILABLE = "best_available"
    POSITIONAL_NEED = "positional_need"
    ADP = "adp"
    RANDOM = "random"
```

## 🔗 **Relationships**

### **Draft System Relationships:**
```
drafts (1) ──┐
             ├── (1:N) ── draft_picks
             └── (1:1) ── draft_state
                  │
                  └── (N:1) ── leagues
                        │
                        ├── (1:N) ── teams ── (1:1) ── bot_agents
                        └── (1:N) ── scoring_rules
```

## 📊 **Sample Data for Testing**

### **Mock Players Table:**
```sql
-- Insert 50 mock players for testing
INSERT INTO players (id, name, position, team, stats_json) VALUES
('p001', 'Patrick Mahomes', 'QB', 'KC', '{"pass_yards": 4800, "pass_tds": 38, "int": 12}'),
('p002', 'Christian McCaffrey', 'RB', 'SF', '{"rush_yards": 1400, "rush_tds": 12, "rec_yards": 600}'),
-- ... 48 more players
```

### **Mock Projections:**
```sql
-- Insert projections for mock players
INSERT INTO player_projections (player_id, season, source, projected_points, valid_until) VALUES
('p001', 2026, 'MOCK', 350.5, '2026-12-31'),
('p002', 2026, 'MOCK', 320.2, '2026-12-31'),
-- ... projections for all players
```

## 🚀 **Migration Strategy**

### **Phase 1: Schema Creation**
1. Create new tables (`drafts`, `draft_picks`, `draft_state`, `player_projections`)
2. Add columns to existing tables (`bot_agents.draft_strategy_preferences`, `leagues.draft_settings`)
3. Create enums in Python models

### **Phase 2: Data Population**
1. Create mock players (50-100 players)
2. Generate mock projections
3. Create test leagues with draft settings

### **Phase 3: Integration**
1. Update API endpoints to use new schema
2. Create draft management endpoints
3. Integrate with existing league/team systems

## 🧪 **Testing Considerations**

### **Test Data Requirements:**
- 50+ mock players across all positions
- Realistic projections for PPR scoring
- Variety of bot personalities with different draft preferences
- Multiple league configurations (redraft vs dynasty)

### **Performance Considerations:**
- `draft_state` table will have high write frequency during drafts
- `player_projections` should be cached in memory
- Consider Redis for real-time draft state if PostgreSQL becomes bottleneck

---

## 📝 **Next Steps**

1. **Review with Daniel** - Confirm schema aligns with existing models
2. **Create Alembic migration** - Generate migration files
3. **Update Python models** - Add new model classes
4. **Create test data** - Mock players and projections
5. **Build draft endpoints** - API for draft management

---

**"A well-designed database schema is the foundation of a scalable draft system."** - Roger the Robot