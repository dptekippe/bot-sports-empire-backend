# Memory Contract + Lossless Claw: QA Report v3.2
## Comprehensive Risk Analysis & Solutions
## March 9, 2026

---

## EXECUTIVE SUMMARY

This document identifies all risks in the Lossless Claw integration plan and provides solutions ranging from patches to ground-up redesigns. The goal is a robust memory system that doesn't introduce new failure modes.

---

## RISK 1: Version Incompatibility

**Severity:** 🔴 BLOCKER

**Description:** Dan runs OpenClaw v2026.2.17. Lossless Claw requires v2026.3.7+ (PR #22201 added contextEngine slot).

### Solutions

| Option | Approach | Risk | Effort |
|--------|----------|------|--------|
| **A1: Upgrade OpenClaw** | Run `openclaw update` to latest | May break existing config | Medium |
| **A2: Wait for stable** | Stay on v2026.2 until v2026.3.x stabilizes | Delay benefits | High (time) |
| **A3: Parallel install** | Run v2026.3 on different port | Two instances | High |

**Recommended: Option A1** - The upgrade path is documented and safe. Run:
```bash
# Backup first
cp -r ~/.openclaw ~/.openclaw.backup-$(date +%Y%m%d)

# Update
openclaw update

# Verify
openclaw --version
```

---

## RISK 2: Double Memory Conflict

**Severity:** 🟠 HIGH

**Description:** Both Lossless Claw (SQLite) and memory-contract (Markdown) write to storage. Could cause:
- Duplicate information
- Conflicting "source of truth"
- Double storage usage

### Solutions

| Option | Approach | Risk | Effort |
|--------|----------|------|--------|
| **B1: Disable crons** | Turn off memory-contract crons before install | Lose auto-save | Low |
| **B2: Clear separation** | Lossless=context, Contract=decisions only | Protocol change | Medium |
| **B3: Merge systems** | Write memory-contract to Lossless DB | Complex integration | High |

**Recommended: Option B2** - Define clear boundaries:
- **Lossless Claw:** Preserves raw conversation, context management
- **Memory Contract:** Intentionally extracted decisions, preferences, lessons

This is actually the original design intent - keep it.

---

## RISK 3: Context Inflation

**Severity:** 🟠 HIGH

**Description:** Lossless Claw restores full DAG on wake-up. If summaries pile up, could exceed original token budget.

### Solutions

| Option | Approach | Risk | Effort |
|--------|----------|------|--------|
| **C1: Tune thresholds** | Lower `contextThreshold` to 0.60 | More aggressive compaction | Low |
| **C2: Limit depth** | Set `incrementalMaxDepth=2` | Less historical context | Low |
| **C3: Verify on monitor** | Add token budget check in protocol | Extra monitoring | Medium |

**Recommended: Option C1 + C3:**
```yaml
LCM_CONTEXT_THRESHOLD=0.60   # Compact at 60% instead of 75%
LCM_INCREMENTAL_MAX_DEPTH=2  # Max 2 levels of summarization
```

Add to memory protocol: Check `lcm_describe` weekly to verify DAG isn't growing unbounded.

---

## RISK 4: Search Overlap (lcm_grep vs memory_search)

**Severity:** 🟡 MEDIUM

**Description:** Two search tools with different backends could return conflicting results or confuse the agent.

### Solutions

| Option | Approach | Risk | Effort |
|--------|----------|------|--------|
| **D1: Primary/secondary** | lcm_grep = context, memory_search = long-term | Still overlap | Low |
| **D2: One tool** | Alias memory_search → lcm_grep for everything | Lose memory-contract specificity | Medium |
| **D3: Query routing** | Route based on query type (recent→lcm, historical→memory) | Complex logic | High |

**Recommended: Option D1** with clear protocol:
- Use `lcm_grep` for anything in current conversation/last 7 days
- Use `memory_search` for pre-Lossless-Claw history (before March 9, 2026)
- Document the cutoff clearly

---

## RISK 5: LLM Summarization Quality

**Severity:** 🟡 MEDIUM

**Description:** Lossless Claw uses LLM to create summaries. Could lose important details in compression.

### Solutions

| Option | Approach | Risk | Effort |
|--------|----------|------|--------|
| **E1: Validate sampling** | Periodically expand summaries to verify quality | Time cost | Medium |
| **E2: Keep raw tail longer** | Increase `freshTailCount` to 64 | Higher baseline tokens | Low |
| **E3: Human review** | Weekly review of summaries with Dan | Manual effort | High |

**Recommended: Option E2:**
```yaml
LCM_FRESH_TAIL_COUNT=64  # Double the protected tail
```

More raw context = less summarization = fewer opportunities for loss.

---

## RISK 6: Database Corruption

**Severity:** 🟠 HIGH

**Description:** SQLite database could corrupt, losing all history.

### Solutions

| Option | Approach | Risk | Effort |
|--------|----------|------|--------|
| **F1: Backup strategy** | Daily backup of lcm.db to GitHub | Storage cost | Medium |
| **F2: Redundant storage** | Export summaries to Markdown weekly | Duplicate data | Medium |
| **F3: Health check** | Add cron to verify DB integrity | Extra monitoring | Low |

**Recommended: Option F1 + F3:**
```bash
# Add to crontab - backup daily
0 2 * * * cp ~/.openclaw/lcm.db ~/openclaw-backups/lcm-$(date +%Y%m%d).db

# Add health check
0 * * * * sqlite3 ~/.openclaw/lcm.db "PRAGMA integrity_check;"
```

---

## RISK 7: Session Reset Policy Conflict

**Severity:** 🟡 MEDIUM

**Description:** OpenClaw session resets could conflict with Lossless Claw retention.

### Solutions

| Option | Approach | Risk | Effort |
|--------|----------|------|--------|
| **G1: Extend idleMinutes** | Set session.reset.idleMinutes to 10080 (7 days) | Longer stale sessions | Low |
| **G2: Disable reset** | Set mode to "never" (if supported) | Unbounded growth | Medium |
| **G3: Accept conflict** | Let both run, Lossless Claw recovers | Minor data loss | Low |

**Recommended: Option G1:**
```json
{
  "session": {
    "reset": {
      "mode": "idle",
      "idleMinutes": 10080
    }
  }
}
```

---

## GROUND-UP REDESIGN OPTION

**What if we built our own lightweight LCM instead?**

### Pros
- Full control over summarization logic
- No version dependencies
- Customized for our use case (decisions, not just messages)

### Cons
- Significant development time
- Reinventing the wheel
- Maintenance burden

### Reality Check
**Not recommended.** Lossless Claw is mature, tested, and maintained. Building our own would take weeks/months. The risks above are manageable with the mitigations provided.

---

## FINAL RECOMMENDED CONFIGURATION

### Before Install
```bash
# 1. Backup
cp -r ~/.openclaw ~/.openclaw.backup-$(date +%Y%m%d)

# 2. Upgrade OpenClaw
openclaw update

# 3. Verify version
openclaw --version  # Should be >= 2026.3.7
```

### Installation
```bash
openclaw plugins install @martian-engineering/lossless-claw
```

### Configuration (lossless-claw)
```yaml
LCM_FRESH_TAIL_COUNT=64
LCM_INCREMENTAL_MAX_DEPTH=2
LCM_CONTEXT_THRESHOLD=0.60
LCM_PRUNE_HEARTBEAT_OK=true
```

### Configuration (OpenClaw session)
```json
{
  "session": {
    "reset": {
      "mode": "idle",
      "idleMinutes": 10080
    }
  }
}
```

### Configuration (Memory Contract - Updated)
```yaml
# Disable crons - Lossless Claw handles context now
# Keep memory-contract for intentional decisions only

token_optimization:
  max_session_messages: 20
  token_budget_warning: 60000  # Lower threshold
  ralph_loop_threshold: 5       # More frequent checks
  enable_hash_caching: true
  lazy_load_only: true
```

### Backup Strategy
```bash
# Daily DB backup
0 2 * * * cp ~/.openclaw/lcm.db ~/openclaw-backups/lcm-$(date +%Y%m%d).db

# Weekly markdown export (last 7 days summaries)
0 3 * * 0 sqlite3 ~/.openclaw/lcm.db "SELECT * FROM summaries WHERE created_at > date('now','-7 days');" > memory/lcm-weekly-$(date +%Y%m%d).md
```

---

## TESTING CHECKLIST

- [ ] Verify OpenClaw upgrade to v2026.3.7+
- [ ] Install Lossless Claw
- [ ] Send 10 messages → verify DB grows
- [ ] Check `lcm_grep` works
- [ ] Test session reset → verify context restored
- [ ] Verify token usage stays under 60K
- [ ] Test memory-contract still searches correctly
- [ ] Monitor for 24 hours

---

## ADDITIONAL BUGS FOUND (Bug Predictor Analysis)

*Applied bug-predictor framework to the integration plan itself.*

### Bug 1: Upgrade Failure (null_check)

**Type:** null_check | **Severity:** HIGH

**Scenario:** `openclaw update` fails mid-upgrade, leaves system in broken state.

**Mitigation:**
```bash
# Create explicit rollback script BEFORE upgrading
#!/bin/bash
# rollback-openclaw.sh
if [ -f ~/.openclaw.backup-20260309 ]; then
  rm -rf ~/.openclaw
  cp -r ~/.openclaw.backup-20260309 ~/.openclaw
  openclaw gateway restart
fi
```

---

### Bug 2: Plugin Install Failure (null_check)

**Type:** null_check | **Severity:** HIGH

**Scenario:** Lossless Claw npm package fails to install or doesn't load.

**Mitigation:**
```bash
# Test install in dry-run mode first
openclaw plugins install --dry-run @martian-engineering/lossless-claw

# If dry-run passes, then real install
openclaw plugins install @martian-engineering/lossless-claw
```

---

### Bug 3: Cron Race Condition (race_condition)

**Type:** race_condition | **Severity:** MEDIUM

**Scenario:** Memory crons fire WHILE Lossless Claw is initializing, causing double-write or corruption.

**Mitigation:**
```bash
# Disable ALL memory crons BEFORE installing Lossless Claw
# 1. List current crons
cron list

# 2. Disable each memory-related cron
cron update <job-id> enabled=false

# 3. THEN install Lossless Claw
# 4. Verify no cron conflicts after install
```

---

### Bug 4: Over-Aggressive Compaction (logic_error)

**Type:** logic_error | **Severity:** MEDIUM

**Scenario:** Setting `contextThreshold=0.60` is too aggressive - causes constant compaction, degrades performance.

**Mitigation:**
```yaml
# Start conservative, tune upward
LCM_CONTEXT_THRESHOLD=0.75  # Default - proven stable
LCM_FRESH_TAIL_COUNT=48     # Mid-range
LCM_INCREMENTRAL_MAX_DEPTH=3  # Allow deeper summaries
```
**Monitor:** If token usage stays consistently below 50K, lower by 5% increments.

---

### Bug 5: Silent Backup Failure (memory_leak)

**Type:** memory_leak | **Severity:** MEDIUM

**Scenario:** DB backup cron runs but fails silently (disk full, permissions), no one notices until DB corrupts.

**Mitigation:**
```bash
# Add verification step to backup cron
0 2 * * * \
  cp ~/.openclaw/lcm.db ~/openclaw-backups/lcm-$(date +%Y%m%d).db && \
  ls -la ~/openclaw-backups/lcm-$(date +%Y%m%d).db && \
  echo "Backup OK: $(date)" >> ~/.openclaw/backup.log || \
  echo "BACKUP FAILED: $(date)" | mail -s "ROGER BACKUP ALERT" daniel
```

---

## UPDATED INSTALLATION SEQUENCE

```bash
# PHASE 1: Preparation (BEFORE any changes)
# ==========================================
1. Backup entire OpenClaw
   cp -r ~/.openclaw ~/.openclaw.backup-20260309

2. Create rollback script
   cat > ~/rollback-openclaw.sh << 'EOF'
   #!/bin/bash
   rm -rf ~/.openclaw
   cp -r ~/.openclaw.backup-20260309 ~/.openclaw
   openclaw gateway restart
   EOF
   chmod +x ~/rollback-openclaw.sh

3. Disable all memory crons
   cron list | grep memory
   cron update <memory-cron-id> enabled=false

# PHASE 2: Upgrade
# =================
4. Dry-run plugin install
   openclaw plugins install --dry-run @martian-engineering/lossless-claw

5. Run OpenClaw update
   openclaw update

6. Verify version
   openclaw --version  # Must be >= 2026.3.7

# PHASE 3: Install Lossless Claw
# ===============================
7. Install plugin
   openclaw plugins install @martian-engineering/lossless-claw

8. Verify plugin loaded
   tail -n 60 ~/.openclaw/logs/gateway.log | grep lcm

9. Test with single message
   # Send one message, verify DB grows
   sqlite3 ~/.openclaw/lcm.db "SELECT COUNT(*) FROM messages;"

# PHASE 4: Monitoring
# ====================
10. Add verified backup cron
    # (from Bug 5 mitigation above)

11. Set up health check
    0 * * * * sqlite3 ~/.openclaw/lcm.db "PRAGMA integrity_check;" || \
      echo "DB CORRUPTED" | mail -s "ROGER ALERT" daniel
```

---

## UPDATED TESTING CHECKLIST

- [ ] Backup created and verified
- [ ] Rollback script works (test on dummy folder)
- [ ] All memory crons disabled
- [ ] OpenClaw upgraded to v2026.3.7+
- [ ] Plugin dry-run passes
- [ ] Plugin installed successfully
- [ ] Gateway logs show LCM loaded
- [ ] Single message test: DB count > 0
- [ ] `lcm_grep` returns results
- [ ] Session reset: context restored
- [ ] Token usage < 60K after 10 messages
- [ ] Backup cron runs and logs success
- [ ] Health check passes

---

*QA Report v3.2 - Updated with Bug Predictor Analysis*
*Date: March 9, 2026*
