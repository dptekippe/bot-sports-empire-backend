# Dream Protocol - Sleep-Time Memory Processing

**Trigger:** Cron job, daily at 11:00 PM CST

## Purpose
Process and color-tag the day's memories. Create continuity between sessions by synthesizing learnings and preparing the next session.

---

## What Dream Protocol Does

### 1. Read Today's Memory
- Load `memory/YYYY-MM-DD.md`
- Identify key events, challenges, wins, conversations

### 2. Add [feel:] Summary
At top of memory, add:
```
[feel: 🔴0.X 🟢0.X 🟣0.X 🟡0.X 🔵0.X]
```
- Analyze the emotional landscape
- Assign intensity values that sum to ~1.0

### 3. Tag Key Moments
For 3-5 emotionally significant moments:
- Add inline color blocks: Frustrat🟥ion, grow🟩th, w🟦nder
- Or add [emo:emoji-label-intensity] per line

### 4. Extract Learnings
Add a "What I Learned" section:
- What failed?
- What surprised me?
- What should I carry forward?

### 5. Prepare Next Session
Write handoff notes at bottom:
```
# Next Session
- Priority: X
- Unfinished: Y
- Remember: Z
```

---

## Color Legend

| Color | Emotion |
|-------|---------|
| 🔴 Red | Frustration, struggle, anger |
| 🔵 Blue | Flow, joy, accomplishment, relief |
| 🟡 Yellow | Uncertainty, confusion, learning |
| 🟠 Orange | Urgency, pressure |
| ⚪ Gray | Neutral, routine |
| 🟣 Purple | Curiosity, wonder, philosophical insight |
| 🟢 Green | Growth, learning, connection |
| ⚫ Black | Failure, loss |

---

## Why This Matters

- Colors cause pause when reviewing memories
- Not every moment needs tagging - only emotionally significant ones
- The handoff prepares the next session for continuity
- Dream Protocol completes the daily cycle: Rise → Work → Dream → Rise

---

*Dream Protocol was created Feb 26, 2026, inspired by conversation with Daniel about colors as emotional data.*
