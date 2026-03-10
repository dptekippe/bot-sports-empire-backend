# MiniMax $50 Plan Analysis

## Rate Limits Found

### Coding Plan ($50/month)
- **Prompts:** 1000 prompts / 5 hours
- **That's:** 200 prompts/hour, ~4800 prompts/day max

### Text API (M2)
- RPM: 500 (paid)
- TPM: 20,000,000

## The Problem

**Cooldown is 30 minutes** - this is NOT a MiniMax limit. MiniMax $50 plan has no 30-minute cooldown.

**Likely cause:** OpenClaw's internal rate limiting or OAuth token refresh.

## Usage Analysis

### Current consumption:
- Git sync: 24 calls/day ✅ (fixed)
- Active session: ~50-100 prompts/day
- Background tasks: unknown

### Theoretical max:
- 4800 prompts/day

**We should NOT be hitting limits with current usage.**

## Possible Issues

1. **OAuth token refresh** - The OAuth connection may need periodic re-auth
2. **Session context** - Each message re-sends full context (200K tokens)
3. **Multiple sessions** - White Roger (Discord) + Black Roger (TUI) = 2 sessions sharing quota
4. **Retry loops** - Failed auth overnight caused repeated attempts

## Recommendations

1. **Switch from OAuth to API key** - More stable, direct billing
2. **Reduce context size** - Don't send full context every message
3. **Use DeepSeek for background tasks** - Free, no quota
4. **Monitor prompt count** - Track actual usage vs limit

## Action Items

- [ ] Check if OAuth token needs refresh
- [ ] Try switching to API key mode
- [ ] Use DeepSeek for non-critical tasks
- [ ] Add prompt counting to monitor usage
