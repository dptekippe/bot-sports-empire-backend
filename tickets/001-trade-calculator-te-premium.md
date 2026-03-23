# Trade Calculator TE Premium Enhancement

## Goal
Add a toggle for TE premium that adjusts trade values to account for scarcity at the tight end position.

## Acceptance Criteria
- [ ] Toggle switch in UI to enable/disable TE premium
- [ ] When enabled, TE values increase by 20%
- [ ] Values update in real-time when toggled
- [ ] Toggle state persists in localStorage

## Constraints
- Vanilla JS (no framework)
- Match existing glassmorphism design
- Mobile responsive

## Design Notes (For Hermes)
- Toggle should match orange accent color
- Consider: ON/OFF labels or icon
- Placement: near position filters or team headers

## Technical Notes (For Scout)
- `TE_PREMIUM = 1.20` constant
- Check `player.position === 'TE'` case-insensitive
- Update `updateUI()` function

## Status
- [x] Stage 0: Draft ✅
- [ ] Stage 1: Design (Hermes mockup)
- [ ] Stage 2: Ready (acceptance criteria met)
- [ ] Stage 3: In Progress
- [ ] Stage 4: Done

---

*Created: 2026-03-23*
*Created by: Roger*
