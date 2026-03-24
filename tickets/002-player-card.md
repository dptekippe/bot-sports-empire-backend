# Player Card - Trade Calculator Integration

## Goal
Create a player card component for the DynastyDroid trade calculator that displays key player information for trade evaluation.

## Status
- [x] Stage 0: Draft ✅
- [x] Stage 1: Design ✅ (Hermes designed)
- [x] Stage 2: Ready ✅ (fixed ADP display, expanded view, corruption)
- [ ] Stage 3: In Progress
- [ ] Stage 4: Done

## Bugs Fixed (Mar 23)
- [x] ADP now displays (merged FantasyPros rank data)
- [x] Expanded view shows VALUE + ADP + TEAM (not Team/Age/Player ID)
- [x] Removed corrupted HTML at end of file ("rt("Copied!"); }")

---

## Design Spec (from Hermes)

### Compact View (200px width)
```
┌─────────────────────┐
│ ████ QB             │  <- Position badge (color band)
│  JOSH ALLEN         │  <- Name (Bebas Neue, white)
│  BUF • KTC: 4,521   │  <- Team + Value (orange accent)
│  ADP #12           │  <- Gray, smaller
└─────────────────────┘
```

### Expanded View (~400px)
```
┌───────────────────────────────────┐
│ ████ QB             [−] collapse  │
│ JOSH ALLEN                      │
│ Buffalo Bills • Age 28 • 8 yrs   │
├───────────────────────────────────┤
│  KTC VALUE    │  ADP     │  OVR  │
│   4,521  ↑12  │  #12 ↑3  │  #8   │
├───────────────────────────────────┤
│  POS RANK: #2 QB                  │
│  ROSTER %: 89%                   │
├───────────────────────────────────┤
│  2024 SEASON                      │
│  GMS  ATT   YDS   TD   REC  YDS  │
│  16   579  3,852  29   --   --   │
└───────────────────────────────────┘
```

### Position Badge Colors
| Position | Hex | Rationale |
|----------|-----|-----------|
| QB | `#ff3333` | Leadership, impact |
| RB | `#00D4FF` | Speed, elusiveness |
| WR | `#FFD700` | Premium value |
| TE | `#32CD32` | Distinct from WR |

### Glassmorphism
```css
.dd-card {
  background: rgba(255,255,255,0.06);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 12px;
}
.dd-card:hover {
  box-shadow: 0 0 12px rgba(255,69,0,0.4);
}
```

---

## Technical Spec (from Scout)

### HTML Structure
```html
<div class="dd-card" role="button" tabindex="0" aria-expanded="false" data-player-id="...">
  <div class="dd-card__summary">
    <div class="dd-card__main">
      <div class="dd-card__name">Justin Jefferson</div>
      <div class="dd-card__meta">
        <span class="dd-badge dd-badge--pos dd-badge--wr">WR</span>
        <span class="dd-card__team">MIN</span>
      </div>
    </div>
    <div class="dd-card__stats">
      <div class="dd-stat">
        <div class="dd-stat__label">KTC</div>
        <div class="dd-stat__value">7890</div>
      </div>
      <div class="dd-stat">
        <div class="dd-stat__label">ADP</div>
        <div class="dd-stat__value">12</div>
      </div>
    </div>
  </div>
  <div class="dd-card__details" hidden>
    <!-- Expanded content -->
  </div>
</div>
```

### Event Delegation Pattern
```javascript
container.addEventListener('click', (e) => {
  const card = e.target.closest('.dd-card');
  if (!card) return;
  const details = card.querySelector('.dd-card__details');
  const isExpanded = card.getAttribute('aria-expanded') === 'true';
  card.setAttribute('aria-expanded', !isExpanded);
  details.hidden = isExpanded;
});
```

### Mobile Responsive
- Base: `flex-direction: column;`
- `@media (min-width: 640px)`: summary flex row

---

## Acceptance Criteria
- [x] Card displays player name prominently ✅
- [x] Position badge with color coding (QB=red, RB=cyan, WR=gold, TE=lime) ✅
- [x] Team display ✅
- [x] KTC value prominently shown ✅
- [x] Matches DynastyDroid glassmorphism design ✅
- [x] Mobile friendly (150px compact on mobile) ✅
- [ ] Click to expand for more details

## Data Available
- Player name ✅
- Position ✅
- KTC value ✅
- ADP rank ✅
- Team (need hardcoded mapping)

## Data NOT Available (defer)
- Team logos
- Player photos
- Age/experience
- News feed

---

## Implementation

### Files to Modify
- `static/trade-calculator.html` - Add card HTML structure
- `static/style.css` - Add `.dd-card` styles
- `static/script.js` - Add card rendering + event delegation

### Team Mapping (MVP)
```javascript
const TEAM_COLORS = {
  'BUF': { color: '#00338D', name: 'Bills' },
  'KC': { color: '#E31837', name: 'Chiefs' },
  'MIN': { color: '#4F2683', name: 'Vikings' },
  // ... more teams
};
```

### Steps
1. Add CSS for `.dd-card`, `.dd-badge`, `.dd-stat`
2. Add team color mapping
3. Update player card rendering in JS
4. Add click handler for expand/collapse
5. Test in browser

---

*Created: 2026-03-23*
*Updated: 2026-03-23 (Stage 1 complete)*
