# Memory Contract Quick Start

## Installation

The Memory Contract system is already installed in:
```
/Users/danieltekippe/.openclaw/workspace/hooks/
```

## Immediate Usage

### 1. Import Memory-Aware Tools
```python
from hooks.memory_aware_tools import memory_aware_exec, memory_aware_write
```

### 2. Replace Standard Tools
```python
# Instead of:
exec(command="your command")

# Use:
memory_aware_exec(command="your command")
```

### 3. Verify It's Working
```bash
# Run validation
python3 /Users/danieltekippe/.openclaw/workspace/hooks/session_validation.py

# Check compliance
cat /Users/danieltekippe/.openclaw/workspace/memory_contract_compliance.json
```

## What Happens

When you use `memory_aware_exec`:

1. **Pre-action search**: Searches memory for relevant context
2. **Execution**: Runs your command
3. **Post-decision write**: Records the decision to memory
4. **Compliance tracking**: Updates metrics

## Example Session

```python
# Before Memory Contract
exec(command="git push origin main")
# No memory of what was deployed

# After Memory Contract
from hooks.memory_aware_tools import memory_aware_exec
memory_aware_exec(command="git push origin main")
# Decision recorded: "Deployed to production at 2026-03-06 16:00"
# Can later recall: "What did we deploy last week?"
```

## Kill Switch

If something goes wrong:

```bash
# Disable immediately
MEMORY_CONTRACT_ENABLED=false python3 your_script.py

# Or create kill switch file
touch /Users/danieltekippe/.openclaw/workspace/DISABLE_MEMORY_CONTRACT
```

## Success Verification

Check these files to verify it's working:

1. **Memory file**: `memory/2026-03-06.md` (should have today's decisions)
2. **Compliance**: `memory_contract_compliance.json` (should show "high" compliance)
3. **Logs**: `hooks/search_log.jsonl` and `hooks/write_log.jsonl` (should have entries)

## Next Steps

1. Start using `memory_aware_exec` for all `exec` calls
2. Add `memory_aware_write` for file writes
3. Monitor compliance metrics
4. Expand to other tools (edit, browser, message)