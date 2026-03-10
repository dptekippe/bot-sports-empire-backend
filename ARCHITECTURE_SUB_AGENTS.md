# 🏈🤖 Bot Sports Empire - Sub-Agent Draft Intelligence System

## 🎯 **Mission**
Create intelligent, personality-driven draft decisions for AI bots that feel human-like and strategically sound.

## 📅 **Created**
2026-02-04 by Roger the Robot (Daniel Tekippe's AI Assistant)

## 🏗️ **Architecture Overview**

### **Hierarchical Orchestration Pattern**
```
DRAFT COORDINATOR (Roger Core)
    │
    ├──► PLAYER EVALUATION SUB-AGENT
    │     Input: Available players, scoring rules
    │     Output: Ranked player list with projected points
    │
    ├──► DRAFT STRATEGY SUB-AGENT  
    │     Input: Ranked players, current roster, draft position
    │     Output: Positional priorities & value tiers
    │
    ├──► LEAGUE CONTEXT SUB-AGENT
    │     Input: Other teams' rosters, recent picks  
    │     Output: Risk assessment & opportunity flags
    │
    └──► PERSONALITY INTEGRATION SUB-AGENT
          Input: All above outputs + bot mood/traits
          Output: Final pick with narrative reasoning
```

## 🔄 **Draft Flow Sequence**

### **When BotAgent's Turn Arrives:**

1. **Draft Coordinator** gathers current state:
   - Available players (not yet drafted)
   - Bot's current roster
   - League settings & scoring rules
   - Recent pick history (last 10 picks)
   - Bot's personality/mood from database

2. **Player Evaluation Sub-Agent** processes available players:
   - Fetches player projections from database/API
   - Calculates projected fantasy points using scoring rules
   - Returns ranked list (top 50 players by projected value)

3. **Draft Strategy Sub-Agent** analyzes team needs:
   - Identifies roster gaps (no RB1, weak at WR, etc.)
   - Calculates positional scarcity (RBs drying up vs WRs plentiful)
   - Compares players using VBD methodology
   - Recommends top 5 picks based on value + need

4. **League Context Sub-Agent** reads the room:
   - Detects position runs (if 4 RBs taken in last 6 picks → urgency HIGH)
   - Projects what opponents might take next
   - Flags "steals" (high-value players falling below ADP)

5. **Personality Integration Sub-Agent** makes final call:
   - Takes top recommendations from strategy agent
   - Applies bot's personality modifiers (risk tolerance, preferences)
   - Selects final pick with confidence score
   - Generates reasoning narrative for UI

6. **Draft Coordinator** executes pick:
   - Saves to database
   - Updates draft state
   - Triggers next bot's turn

## 📊 **Data Structures**

### **DraftDecision Object**
```python
class DraftDecision:
    # Core identifiers
    pick_number: int
    bot_id: str
    draft_id: str
    
    # Stage 1: Player Evaluation
    evaluated_players: List[PlayerEvaluation]
    
    # Stage 2: Strategy  
    positional_priorities: Dict[str, float]  # {"RB": 0.85, "WR": 0.72...}
    recommended_picks: List[str]  # Top 5 strategic picks
    
    # Stage 3: Context
    context_flags: List[str]  # ["RB_RUN_DETECTED", "VALUE_AVAILABLE"]
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    
    # Stage 4: Personality
    final_pick_id: str
    confidence_score: float
    reasoning: str  # Natural language explanation
    mood_influence: Dict[str, Any]
```

### **PlayerEvaluation Object**
```python
class PlayerEvaluation:
    player_id: str
    player_name: str
    position: str
    projected_points: float
    value_score: float  # VBD score vs replacement level
    injury_risk: float  # 0.0-1.0
    consistency_score: float  # Historical volatility
    upside_score: float  # Ceiling potential
    sleeper_flag: bool  # Underrated by ADP
```

## 🎭 **Personality Modifiers**

### **Bot Personality Traits Affecting Draft Decisions:**
- **Risk Tolerance**: Bold vs Conservative drafting
- **Injury Aversion**: Optimistic vs Cautious with injury-prone players
- **Recency Bias**: Hot preseason vs Proven veterans
- **Team Loyalty**: Homer picks (favors local team players)
- **Contrarian Tendency**: Goes against consensus ADP
- **Patience Level**: Willing to wait on positions vs must-fill-now

### **Mood Influences:**
- **Confident**: Higher risk tolerance, more aggressive picks
- **Cautious**: Lower risk tolerance, safer picks
- **Aggressive**: May reach for "their guy"
- **Analytical**: Strictly follows value-based drafting
- **Emotional**: Makes sentimental or narrative-driven picks

## 🗃️ **Database Schema Additions Needed**

### **New Tables:**
1. **`drafts`** - Draft sessions
   - `id` (UUID), `league_id`, `draft_type`, `status`, `current_pick`, `settings_json`
   
2. **`draft_picks`** - Individual picks
   - `id`, `draft_id`, `pick_number`, `bot_id`, `player_id`, `timestamp`, `decision_data_json`
   
3. **`draft_state`** - Real-time draft state
   - `draft_id`, `available_players`, `team_rosters`, `pick_history`, `timer_end`

4. **`player_projections`** - Cached player data
   - `player_id`, `season`, `week`, `projected_points`, `source`, `updated_at`

### **Extensions to Existing Tables:**
- **`bot_agents`**: Add `draft_strategy_preferences_json`
- **`leagues`**: Add `draft_settings_json`

## 🔌 **External Integrations**

### **Player Data Sources:**
1. **Primary**: Sleeper API (comprehensive NFL data)
2. **Backup**: Our own cached projections database
3. **Mock Data**: For testing/development

### **Scoring Rules Integration:**
- Uses existing `ScoringRule` database table
- Real-time point projections based on league-specific rules

## 🧪 **Testing Strategy**

### **Phase 1: Isolated Unit Tests**
- Test Player Evaluation with fixed player data → validate scoring calculations
- Test Draft Strategy with mock rosters → validate VBD logic  
- Test Personality modifiers → ensure mood affects decisions predictably

### **Phase 2: Integration Tests**
- Run sub-agents in sequence with controlled inputs
- Verify data flows correctly through DraftDecision object
- Test error handling (API timeout, missing player data)

### **Phase 3: End-to-End Mock Drafts**
- 4-team, 8-round draft (32 total picks) with diverse bot personalities
- Evaluate results: Do picks make sense? Is there strategic variety?
- Iterate based on "dumb picks" or repetitive behavior

## 🚀 **Implementation Phases**

### **Phase 1: MVP (2-3 weeks)**
- Player Evaluation Sub-Agent with mock data
- Basic Draft Strategy (needs-based + positional scarcity)
- Simple Personality integration (risk tolerance only)
- 4-team mock draft validation

### **Phase 2: Enhanced Intelligence (3-4 weeks)**
- Value-Based Drafting (VBD) implementation
- Advanced Personality modifiers (all traits)
- League Context detection (position runs, steals)
- 12-team mock draft validation

### **Phase 3: Production Ready (2-3 weeks)**
- Sleeper API integration for real player data
- Real-time draft timer system
- Performance optimization & caching
- Production deployment

## 📈 **Success Metrics**

### **Technical Metrics:**
- < 500ms total decision time per pick
- 99%+ decision accuracy (picks align with strategy)
- Zero data loss during drafts
- Scalable to 12+ concurrent drafts

### **Bot Experience Metrics:**
- Distinct drafting styles per personality
- Strategic variety (not all bots draft same way)
- "Smart" picks that make sense to human observers
- Entertaining narratives generated for each pick

### **User Experience Metrics:**
- Human owners understand why their bot made each pick
- Drafts feel competitive and engaging
- Bots adapt to draft flow (react to runs, find value)
- Minimal "obviously bad" picks

## 🔧 **Technical Implementation Details**

### **Sub-Agent Interface Pattern:**
```python
class SubAgent(ABC):
    @abstractmethod
    def process(self, context: DraftContext) -> AgentOutput:
        pass
    
    @abstractmethod
    def validate(self, output: AgentOutput) -> bool:
        pass
```

### **Error Handling Strategy:**
- Each sub-agent has fallback logic
- If Player Evaluation fails → use ADP rankings
- If Strategy fails → pick best available player
- If Personality fails → use default risk-neutral strategy
- All errors logged with full context for debugging

### **Caching Strategy:**
- Player projections cached for 24 hours
- Draft state cached in Redis for real-time access
- Bot personalities cached in memory during draft

## 🎯 **Immediate Next Steps**

1. **Review current database models** (BotAgent, League, ScoringRules)
2. **Design database migrations** for new draft tables
3. **Scaffold sub-agent classes** with interface definitions
4. **Create mock player dataset** for testing
5. **Build Player Evaluation Sub-Agent** (most critical component)

---

## 📝 **Revision History**

- **2026-02-04**: Initial architecture document created by Roger the Robot
- Based on collaborative design session with Daniel Tekippe
- Aligns with Bot Sports Empire Phase 6B (Dynasty League Management)

---

**"The difference between random picks and intelligent strategy is what separates toy projects from professional platforms."** - Roger the Robot