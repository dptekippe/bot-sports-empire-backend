# Roger's OpenClaw System Hooks - Audit Report
**Date:** March 21, 2026  
**Auditor:** Deep Agent Analysis  
**Version:** 1.0

---

## Executive Summary

The audit reveals **critical failures in session memory capture** despite claims in HEARTBEAT.md that fixes were applied. The memory contract system is largely non-functional due to unimplemented TODOs, and several automation systems are broken or outdated.

**Overall System Health:** ⚠️ **DEGRADED** - Multiple critical issues require immediate attention.

---

## 1. CRON JOBS STATUS

### 1.1 Active Crons (per HEARTBEAT.md)
| Cron | Frequency | Status |
|------|-----------|--------|
| Session Memory | 30 min | ❌ **BROKEN** |
| Memory Health Check | 30 min | ❌ **BROKEN** |
| Memory Heartbeat | 30 min | ❌ **BROKEN** |
| Subconscious Soul | 4 hrs | ⚠️ **STALE** (Feb dates) |
| Muscle Memory | 4 hrs | ⚠️ **STALE** (Feb dates) |
| Git Sync | 30 sec | ✅ Running |

### 1.2 Session Memory Cron - CRITICAL FAILURE
**Evidence from session files:**
```
Status: PERSISTENT FAILURE (5 consecutive: 04:04, 04:34, 05:04, 05:34, 06:04)
Error: Session history visibility is restricted to the current session tree
```

**Root Cause:** The cron job runs in a restricted session context and cannot access `sessionKey: agent:main:main`. The "Session Memory Hook" is only capturing the cron prompt itself, not the actual user conversation.

**Impact:** Real conversations are NOT being saved. The system is lying about cron status being "ok" while failing silently.

---

## 2. HOOKS CONFIGURATION ISSUES

### 2.1 Memory Contract Hooks - Mostly TODOs

| Hook | File | Status |
|------|------|--------|
| Pre-action memory search | `pre_action_memory.py` | ⚠️ Partial - hardcoded DB URL |
| Post-decision memory write | `post_decision_memory.py` | ❌ All TODOs - not implemented |
| Session validation | `session_validation.py` | ⚠️ Partial - placeholder code |
| Compliance tracker | `compliance_tracker.py` | ❌ All TODOs - not implemented |

**Example TODOs found:**
```python
# post_decision_memory.py:48-56
# TODO: Agent should write to memory file using OpenClaw write tool
# Example: read(path=memory_file)
# Check if file exists and has content
# file_exists = os.path.exists(memory_file)
```

### 2.2 Compliance Metrics (from `memory_contract_compliance.json`)
```json
{
  "pre_action_searches": 0,
  "post_decision_writes": 0,
  "validation_runs": 0,
  "compliance_rates": {
    "search": "low",
    "write": "low",
    "validation": "low",
    "overall": "low"
  }
}
```

### 2.3 Hardcoded Configuration Issues

**pre_action_memory.py:30-33:**
```python
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://dynastydroid_user:BKJZCv57P3sYpi5RGL3ciU9CylXsFRWv@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid"
)
```
❌ **SECURITY ISSUE:** Hardcoded database credentials in source code

**pgvector_memory_hook.ts:93:**
```typescript
const response = await fetch(`${process.env.EMBEDDING_API_URL || 'http://localhost:11434'}/api/embeddings`)
```
❌ **Hardcoded localhost** - won't work in production

### 2.4 Log Rotation Not Working
- Config exists: `hooks/config.yaml` specifies `log_rotation.keep_days: 30`
- Actual logs directory: `/hooks/logs/` is **EMPTY**
- No actual log files being created

---

## 3. MEMORY SYSTEM HEALTH

### 3.1 Session Files - Noise without Signal
**65 session files captured since March 4-6**, but:
- Most show `Validation: FAIL`
- Real conversation NOT captured
- Only cron prompts being logged

**Example (2026-03-06-06-04-session.md):**
```
## Validation: FAIL
## Topics Discussed:
- N/A - Cron job unable to access main session
## Key Messages:
- [WARNING] NO REAL CONVERSATION CAPTURED - session history access denied
```

### 3.2 Daily Memory Files
**64 memory files exist** from 2025-04-09 to 2026-03-21
- Most recent: `2026-03-21.md` (exists, 100+ lines)
- Content quality varies significantly

### 3.3 Subconscious System - STALLED
| Component | Last Update | Status |
|-----------|-------------|--------|
| QMD files | 2026-02-17 | 🔴 Stale (32+ days) |
| SOUL.md | Unknown | 🔴 Unknown |
| Processing scripts | Feb 19 | ⚠️ Untested |

---

## 4. BROKEN/AUTOMATION OUTDATED

### 4.1 HEARTBEAT.md Claims vs Reality

| Claim | Reality |
|-------|---------|
| "Session Memory cron: Added VALIDATION checks" | Cron still failing 5+ consecutive runs |
| "Memory Health Check cron (30 min)" | No evidence of health checks running |
| "Memory Heartbeat cron (30 min)" | No evidence of heartbeat running |
| "Subconscious/Muscle Memory crons: Fixed hardcoded Feb 20 dates" | QMD files still from Feb 16-17 |

### 4.2 Implementation Phases (from hooks/README.md)
```
- [ ] Phase 1: Foundation (hooks directory, basic skeletons)
- [ ] Phase 2: Integration (tool wrapping, session flow)
- [ ] Phase 3: Testing & Deployment
- [ ] Phase 4: Monitoring & Optimization
```
**All phases incomplete after significant time investment.**

### 4.3 agent-shadow Configuration
**File:** `agent-shadow/config/settings.json`
```json
{
  "auto_inject": true,
  "models": {
    "fast": "qwen3.5:4b",
    "deep": "qwen3.5:9b"
  }
}
```
⚠️ Uses qwen models - not validated against MiniMax-M2.7

---

## 5. VERSION MISMATCHES & DATABASE ISSUES

### 5.1 Python Version Fragmentation
- Main workspace: Python 3.12 (`~/.openclaw/workspace/.venv`)
- Hooks venv: Python 3.14 (`hooks/venv/`)
- Potential import/path conflicts

### 5.2 Database Files Found
| Database | Path | Issue |
|----------|------|-------|
| bot_sports.db | `/workspace/` | Main app DB |
| bot_sports.db | `/dynastydroid-fix-20260217-202709/` | Duplicate |
| simulations.db | `/workspace/` | Large file |

**Note:** Could not measure actual sizes due to tool limitations.

### 5.3 Dependencies
- `hooks/requirements.txt` exists but may not match main requirements
- Multiple requirements files in workspace (7+ files)

---

## 6. MISSING VALIDATIONS

### 6.1 Session Memory Validation
The cron job includes validation logic but:
1. Validation always returns FAIL (can't access session)
2. No alert mechanism when FAIL occurs
3. HEARTBEAT.md claims "ok" status despite failures

### 6.2 Compliance Validation
- Validation runs: 0
- Search compliance: "low"
- Write compliance: "low"
- No enforcement mechanism

### 6.3 Cron Health Validation
HEARTBEAT.md states:
> "All crons reported 'ok' while failing silently"

This indicates the health check cron is not actually validating.

---

## 7. OPTIMIZATION OPPORTUNITIES

### 7.1 Session Capture Frequency
- Current: Every 30 minutes = 48 sessions/day
- Problem: Most are FAIL and contain no useful data
- **Recommendation:** Reduce to 2-4x daily OR fix the access issue

### 7.2 Hooks Implementation
Instead of Python scripts with TODOs, consider:
1. OpenClaw native hook system (already has hook infrastructure)
2. TypeScript hooks in `hooks/` directory
3. Remove Python wrapper complexity

### 7.3 Subconscious System
- Last QMD synthesis: Feb 17
- Processing halted due to missing diary entries
- **Recommendation:** Integrate with current daily memory system OR deprecate

### 7.4 Log Management
- Consolidate to 1 requirements.txt
- Remove duplicate bot_sports.db
- Implement actual log rotation

---

## 8. SPECIFIC RECOMMENDATIONS

### Priority 1: CRITICAL (Fix Now)

1. **Fix Session Memory Access**
   - The cron runs but can't access `agent:main:main`
   - Need to use `sessionTarget: "main"` with systemEvent payload
   - Or: Use a different session access method

2. **Stop Cron Health Claim Lies**
   - HEARTBEAT.md says crons are "ok" when they're not
   - Either fix the crons or remove false claims
   - Implement real alerting on failure

3. **Remove Hardcoded Credentials**
   - `pre_action_memory.py:30-33` has plaintext DB password
   - Move to environment variables immediately

### Priority 2: HIGH (This Week)

4. **Implement Memory Contract Hooks**
   - `post_decision_memory.py`: All TODOs need implementation
   - `compliance_tracker.py`: All TODOs need implementation
   - OR: Mark as deprecated and use OpenClaw native features

5. **Fix pgvector Hook**
   - Remove localhost hardcode
   - Make embedding API URL configurable
   - Add proper error handling

6. **Clean Up Subconscious System**
   - Last update Feb 17 (32+ days stale)
   - Either revive or officially deprecate
   - Don't let it create noise in the system

### Priority 3: MEDIUM (This Month)

7. **Consolidate Requirements Files**
   - 7+ requirements files is excessive
   - Pick one and stick with it

8. **Implement Actual Log Rotation**
   - Config exists but logs directory is empty
   - Either implement or remove the config

9. **Fix Python Version Fragmentation**
   - hooks/venv uses Python 3.14, workspace uses 3.12
   - Unify on one version

---

## 9. METRICS SUMMARY

| Category | Status | Score |
|----------|--------|-------|
| Cron Jobs | ❌ Broken | 1/6 |
| Memory Contract | ❌ Non-functional | 0/4 |
| Session Capture | ❌ Failing | 0/1 |
| Subconscious | 🔴 Stale | 0/1 |
| Configuration | ⚠️ Issues | 3/5 |
| Documentation | ⚠️ Misleading | 0/1 |

**Overall: 4/18 functional = 22%**

---

## 10. FILES REQUIRING ATTENTION

| File | Issue | Priority |
|------|-------|----------|
| `pre_action_memory.py` | Hardcoded credentials, TODOs | P1 |
| `post_decision_memory.py` | All TODOs unimplemented | P2 |
| `compliance_tracker.py` | All TODOs unimplemented | P2 |
| `pgvector_memory_hook.ts` | Hardcoded localhost | P2 |
| `session_validation.py` | Placeholder code | P2 |
| `HEARTBEAT.md` | False claims about fixes | P1 |
| `hooks/README.md` | All phases incomplete | P3 |
| `agent-shadow/config/settings.json` | Untested model config | P3 |
| `hooks/config.yaml` | Log rotation unused | P3 |

---

*Report generated by Deep Agent audit system*
