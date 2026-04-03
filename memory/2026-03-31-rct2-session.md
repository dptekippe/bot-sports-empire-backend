# RCT2 Project Session - March 31, 2026

## What We Accomplished

### OpenRCT2 Setup ✅
- Extracted RCT2 game data from GOG installer using `innoextract --gog`
- OpenRCT2 running headless on port 8080 with caffeinate
- Ride Creation API working (list rides, create rides)

### Full CRUD on Rides ✅
- listAllRides: Works
- createRide: Works (fixed parameter bug)
- deleteRide: FIXED - was broken, now works with rideId parameter

### RL Infrastructure Built ✅
Location: /Volumes/ExternalCorsairSSD/rct2_rl/
- observer.py - log tail observer for RCT2 state
- rct2_api.py - TCP API client for OpenRCT2
- rewards.py - reward function with 9-tier milestone system
- baseline_agent.py - random agent for testing
- episode_runner.py - runs fixed-length RL episodes

### Strategy Ledger Designed ✅
Hermes designed two-tier format:
- Episode Ledger (per run) + Decision Node Log (inline)
- Win condition priorities: Rating >999, 3000+ guests, profit, awards, research

### SIGTERM Issue Identified 🔍
- sessions_spawn (simple shell): WORKS fine
- Scout/Hermes via exec+background: SIGTERM after 5-14 min
- Issue is in exec environment, NOT agent frameworks
- Hermes currently investigating

### Memory Hooks Reviewed ⚠️
Hermes found bugs in pgvector-memory and memory-pre-action:
- Double connect() issue
- Unawaited index creation
- NaN in embedding parsing
- Hermes was fixing but got SIGTERM'd

### Comms Blackboard ✅
Using for task routing between agents
Multiple proposals tracked in /Volumes/ExternalCorsairSSD/comms_blackboard/

## Key Insight
Daniel pointed out: Both Scout (LangGraph) and Hermes (Nous) getting SIGTERM = issue in shared execution environment, not agent frameworks. sessions_spawn test confirmed this.

## Still Pending
- Hermes SIGTERM investigation results
- Memory hook bug fixes (partially done)
- Full RL agent training
