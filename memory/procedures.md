# Procedures & Preferences

_Last updated: April 11, 2026_

---

## Technical Procedures

### SIGTERM Prevention for Hermes
**Problem:** Hermes sessions getting SIGTERM'd unexpectedly after 2-3 minutes of browser use.
**Root cause:** Stale `agent-browser` daemon processes accumulating over time.
**Solution:** Before invoking Hermes, kill all stale daemon processes:
```bash
ps aux | grep agent-browser | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null || true
```
**When to run:** Before starting any Hermes session that uses browser automation.

### Response Cutoff Prevention
**Problem:** Long responses getting cut off mid-transmission.
**Root cause:** Single response too large for session limits.
**Solution:** Break longer tasks into smaller chunks:
- For glossary expansion: add terms in batches of ~20-30
- For large file edits: use multiple edit calls with smaller changes
- For long explanations: break into multiple messages

## Workflow Preferences

### Project Post-Mortem Protocol
After completing any significant project:
1. Create a living spec document from day 1
2. Track all decisions with reasoning (audit trail)
3. Conduct full SDK research before escalating to Daniel
4. Reference spec in final review to ensure expectations met

### SDK Verification Rule (Team Delegation Framework Section 1.G)
Before writing code against external APIs/SDKs:
1. Inspect SDK types FIRST — Read the actual SDK source/type definitions
2. Run a 5-line proof-of-concept — Prove the SDK calls work
3. Confirm build compiles — Run `tsc` before considering code done

## System Configurations

