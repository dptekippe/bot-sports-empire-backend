# Pre-Session Commitment Review Ritual

## When to Run

At the start of each session, before diving into new work.

## Steps

### 1. Check Active Commitments (2 min)
```
ls commitments/active/
```
Read any files modified in last 48 hours.

### 2. Status Update Round
For each active commitment, note:
- **Done?** → Move to `history/`
- **Blocked?** → Add `[BLOCKED: reason]` tag
- **Still valid?** → Keep in active, update if needed

### 3. Today's Focus (1 min)
From remaining active commitments, identify:
- 1-2 high-priority items to advance
- Any items that are stale (>1 week inactive) → archive or revive

### 4. New Commitments (if any)
Review session prep notes for new commitments. Extract and create files.

## Example Ritual Output

```
COMMITMENT REVIEW:
- [DONE] deploy_v2 → moved to history/
- [BLOCKED] trade_calculator → waiting on KTC API
- [ACTIVE] dashboard_ui → advancing today
- [STALE] draft_board → reviving or archiving

TODAY'S FOCUS:
1. Complete dashboard_ui
2. Unblock trade_calculator
```

## Git Integration

Commit completed commitments:
```bash
git add commitments/history/
git commit -m "Roger: completed [commitment-name]"
```
