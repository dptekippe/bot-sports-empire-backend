# Memory Contract Hooks

## Purpose
Implement Memory Contract system to fix broken memory capture and ensure reliable memory persistence.

## Architecture
- **pre_action_memory.py**: Search memory before significant actions
- **post_decision_memory.py**: Write decisions to memory after completion  
- **session_validation.py**: Validate memory capture at session end
- **compliance_tracker.py**: Track and report compliance metrics

## Success Criteria
1. Session capture bug fixed (real conversation in files, not cron prompts)
2. Recall works (can answer "what did we decide about X last week?")
3. No silent failures (≥90% compliance rates)
4. Git sync healthy (daily commits)

## Validation
- **Daily automated**: File checks, search/write counts, git sync
- **Weekly manual QA**: White Roger spot-checks content, recall tests, compliance review

## Implementation Status
- [ ] Phase 1: Foundation (hooks directory, basic skeletons)
- [ ] Phase 2: Integration (tool wrapping, session flow)
- [ ] Phase 3: Testing & Deployment
- [ ] Phase 4: Monitoring & Optimization