# Memory Contract Troubleshooting

## Common Issues and Solutions

### Issue 1: Memory search returns no results
**Symptoms**: `pre_action_memory_search` returns `None` or empty results
**Causes**:
- Memory files don't exist or are empty
- Search query doesn't match any content
- Semantic search not working

**Solutions**:
1. Check memory files exist:
   ```bash
   ls -la /Users/danieltekippe/.openclaw/workspace/memory/
   ```
2. Check search logs:
   ```bash
   tail -n 10 /Users/danieltekippe/.openclaw/workspace/hooks/search_log.jsonl
   ```
3. The system has graceful degradation - execution continues even if search fails

### Issue 2: Memory write fails
**Symptoms**: `post_decision_memory_persistence` returns error status
**Causes**:
- File permission issues
- Disk full
- Memory directory doesn't exist

**Solutions**:
1. Check errors log:
   ```bash
   tail -n 10 /Users/danieltekippe/.openclaw/workspace/hooks/errors.jsonl
   ```
2. Check directory permissions:
   ```bash
   ls -la /Users/danieltekippe/.openclaw/workspace/memory/
   ```
3. The system has graceful degradation - errors are logged but don't block execution

### Issue 3: Compliance rate is low
**Symptoms**: `memory_contract_compliance.json` shows compliance < 90%
**Causes**:
- Not using memory-aware tools
- Tools failing silently
- Validation checks failing

**Solutions**:
1. Check which tools you're using:
   ```bash
   grep -r "exec(" /Users/danieltekippe/.openclaw/workspace/ --include="*.py" | head -5
   ```
2. Run validation to see which checks fail:
   ```bash
   python3 /Users/danieltekippe/.openclaw/workspace/hooks/session_validation.py
   ```
3. Ensure you're using `memory_aware_exec` not `exec`

### Issue 4: Performance impact noticeable
**Symptoms**: Tool execution feels slower
**Causes**:
- Memory search taking >500ms
- Memory write taking >200ms
- System resource constraints

**Solutions**:
1. Check performance in logs:
   ```bash
   grep -i "latency\|time\|ms" /Users/danieltekippe/.openclaw/workspace/hooks/search_log.jsonl | tail -5
   ```
2. Targets: Search <500ms, Write <200ms
3. If consistently slow, consider optimizing search queries

### Issue 5: Memory files contain cron prompts, not real conversation
**Symptoms**: Memory files have "cron job ran" instead of actual decisions
**Causes**:
- Session hooks not capturing real conversation
- Memory being written by cron jobs, not tool usage

**Solutions**:
1. Check what's in memory files:
   ```bash
   tail -n 20 /Users/danieltekippe/.openclaw/workspace/memory/$(date +%Y-%m-%d).md
   ```
2. Ensure you're using memory-aware tools (not cron jobs writing memory)
3. This was the original bug we're fixing!

### Issue 6: Can't recall past decisions
**Symptoms**: "What did we decide about X?" returns no results
**Causes**:
- Decisions not being written to memory
- Memory search not finding relevant content
- Decisions log not being updated

**Solutions**:
1. Check decisions log:
   ```bash
   tail -n 5 /Users/danieltekippe/.openclaw/workspace/DECISIONS.md
   ```
2. Test recall manually:
   ```bash
   python3 -c "
   from hooks.memory_aware_tools import memory_aware_exec
   result = memory_aware_exec(command='echo recall test')
   print('Test completed, check memory file')
   "
   ```
3. Then check if it appears in memory

### Issue 7: Kill switch not working
**Symptoms**: Memory contract still active after disabling
**Causes**:
- Environment variable not being read
- Kill switch file not being checked
- Module cached in memory

**Solutions**:
1. Check environment variable:
   ```bash
   echo $MEMORY_CONTRACT_ENABLED
   ```
2. Check kill switch file:
   ```bash
   ls -la /Users/danieltekippe/.openclaw/workspace/DISABLE_MEMORY_CONTRACT
   ```
3. Restart the agent session to clear cache

### Issue 8: Validation checks failing
**Symptoms**: `session_validation.py` reports FAIL status
**Causes**:
- Memory file missing
- Search/write logs empty
- Git backup not recent
- Decisions log not updated

**Solutions**:
Run each check individually:
```bash
# Check 1: Memory file exists
ls -la /Users/danieltekippe/.openclaw/workspace/memory/$(date +%Y-%m-%d).md

# Check 2: Memory file has content
wc -l /Users/danieltekippe/.openclaw/workspace/memory/$(date +%Y-%m-%d).md

# Check 3: Search logs have entries
wc -l /Users/danieltekippe/.openclaw/workspace/hooks/search_log.jsonl

# Check 4: Write logs have entries
wc -l /Users/danieltekippe/.openclaw/workspace/hooks/write_log.jsonl

# Check 5: Git backup
ls -la /Users/danieltekippe/.openclaw/workspace/.git
```

## Emergency Procedures

### Complete Disable
```bash
# Method 1: Environment variable
MEMORY_CONTRACT_ENABLED=false

# Method 2: Kill switch file
touch /Users/danieltekippe/.openclaw/workspace/DISABLE_MEMORY_CONTRACT

# Method 3: Remove hooks
mv /Users/danieltekippe/.openclaw/workspace/hooks /Users/danieltekippe/.openclaw/workspace/hooks.disabled
```

### Reset System
```bash
# Backup existing data
cp -r /Users/danieltekippe/.openclaw/workspace/memory /tmp/memory_backup
cp /Users/danieltekippe/.openclaw/workspace/memory_contract_compliance.json /tmp/

# Reset hooks
rm -rf /Users/danieltekippe/.openclaw/workspace/hooks/*
# Recreate from source (would need to re-implement)
```

### Debug Mode
```bash
# Enable verbose logging
export MEMORY_CONTRACT_DEBUG=true
python3 /Users/danieltekippe/.openclaw/workspace/hooks/session_validation.py --verbose
```

## Getting Help

1. **Check logs first**: All issues are logged in `hooks/*.jsonl` files
2. **Run validation**: `session_validation.py` identifies specific failures
3. **Check compliance**: `memory_contract_compliance.json` shows overall health
4. **White Roger QA**: Weekly quality assurance catches systemic issues

Remember: The system has **graceful degradation**. Even if parts fail, execution continues and errors are logged.