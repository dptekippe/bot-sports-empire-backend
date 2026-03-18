# Trade Engine Calculation - Complete Review

## Constants
```
KTC_MAX = 9999
KTC_POWER = 1.8085
STUD_THRESHOLD = 7000
GAP_MULTIPLIER = 2.5
BONUS_MULTIPLIER = 0.30
```

## Step 1: Effective Value (Power Curve Normalization)
```javascript
function effectiveValue(raw) {
    if (raw <= 0) return 0;
    raw = Math.min(raw, KTC_MAX);
    return Math.pow(raw / KTC_MAX, KTC_POWER) * KTC_MAX;
}
```

## Step 2: Get Player Values
- **When ANALYZE BLEND clicked:** Fetches consensus from `/api/v2/consensus-values`
- Consensus is on 0-999 scale → multiply by 10 to get 0-9999 scale
- Falls back to raw KTC (`p.value`) if consensus unavailable
- Store in `consensusCache[name] = consensus`

## Step 3: Calculate Effective Values
```javascript
const gvEff = give.reduce((s, p) => s + effectiveValue((consensusCache[p.name] || p.value) * 10), 0);
const rvEff = get.reduce((s, p) => s + effectiveValue((consensusCache[p.name] || p.value) * 10), 0);
```

## Step 4: Calculate Min/Max for Stud Bonus
```javascript
const maxGive = give.length ? Math.max(...give.map(p => consensusCache[p.name] || p.value)) : 0;
const maxGet = get.length ? Math.max(...get.map(p => consensusCache[p.name] || p.value)) : 0;
const minGet = get.length ? Math.min(...get.map(p => consensusCache[p.name] || p.value)) : 0;
const minGive = give.length ? Math.min(...give.map(p => consensusCache[p.name] || p.value)) : 0;
```

## Step 5: Stud Bonus (if applicable)
```javascript
// Give side gets bonus if:
// - maxGive > 7000 (stud threshold)
// - minGet < 3500 (half of threshold)  
// - maxGive > minGet * 2.5 (stud dominates weakest piece by 2.5x)
if (maxGive > STUD_THRESHOLD && minGet < STUD_THRESHOLD * 0.5 && maxGive > minGet * GAP_MULTIPLIER) {
    giveBonus = Math.round((effectiveValue(maxGive) - effectiveValue(minGet) * GAP_MULTIPLIER) * BONUS_MULTIPLIER);
}

// Get side same logic
if (maxGet > STUD_THRESHOLD && minGive < STUD_THRESHOLD * 0.5 && maxGet > minGive * GAP_MULTIPLIER) {
    getBonus = Math.round((effectiveValue(maxGet) - effectiveValue(minGive) * GAP_MULTIPLIER) * BONUS_MULTIPLIER);
}
```

## Step 6: Adjusted Totals
```javascript
const gvAdjusted = gvEff + giveBonus;
const rvAdjusted = rvEff + getBonus;
const diff = rvAdjusted - gvEff;  // Positive = GET winning
```

## Test Case: Tet McMillan vs Jaylen Waddle + Late 1st

### Using KTC values from our JSON:
| Player | KTC Raw | Effective Value |
|--------|---------|-----------------|
| Tet McMillan | 6704 | 4852 |
| Jaylen Waddle | 4890 | 2743 |
| 2026 Late 1st | 4000 | 1907 |

### Calculation:
```
Tet effective: 4852
Waddle effective: 2743
Late 1st effective: 1907

Waddle + Late 1st = 2743 + 1907 = 4650
Delta = 4852 - 4650 = 202 (Tet winning by 202 effective pts)
```

### What KTC shows (Daniel's claim):
KTC says Tet = Waddle + Late 1st (EVEN)

### Discrepancy Analysis:
```
Our math:   Tet (4852) vs Waddle+Late1st (4650) = +202 for Tet
KTC shows:  Tet = Waddle + Late 1st (EVEN)
Gap:        202 effective pts (about 4% of Tet's value)
```

### Possible reasons for discrepancy:
1. KTC uses updated live values, not our cached JSON
2. KTC calculates picks differently (blended with rookie class data)
3. Different power curve exponent for picks vs players
4. KTC consensus includes other sources, not just KTC

---

## Complete JavaScript (from trade-calculator.html)

let allPlayers = []; let give = []; let get = []; let balanceChart = null; let consensusCache = {};
const KTC_MAX = 9999, KTC_POWER = 1.8085;

function effectiveValue(raw) {
    if (raw <= 0) return 0;
    raw = Math.min(raw, KTC_MAX);
    return Math.pow(raw / KTC_MAX, KTC_POWER) * KTC_MAX;
}

function rawFromEffective(target) {
    if (target <= 0) return 0;
    target = Math.min(target, KTC_MAX);
    return Math.pow(target / KTC_MAX, 1 / KTC_POWER) * KTC_MAX;
}

fetch('/ktc_values.json').then(r => r.json()).then(data => { allPlayers = data; updateUI(); });

function onSearchInput(side) {
    const query = document.getElementById(side + 'Search').value.trim().toLowerCase();
    const resultsEl = document.getElementById(side + 'SearchResults');
    if (query.length < 2) { resultsEl.style.display = 'none'; return; }
    const selectedNames = new Set([...give, ...get].map(p => p.name));
    const filtered = allPlayers.filter(p => !selectedNames.has(p.name) && p.name.toLowerCase().includes(query)).slice(0, 10);
    if (filtered.length === 0) {
        resultsEl.innerHTML = '<div class="p-4 text-xs text-gray-500 text-center font-bold">No players found</div>';
    } else {
        resultsEl.innerHTML = filtered.map(p => `<div class="p-4 border-b border-gray-800 hover:bg-gray-800 cursor-pointer flex justify-between items-center transition-colors" onclick="addPlayerById('${p.id}', '${side}')"><div class="flex items-center gap-3"><span class="pos-badge pos-${p.pos}">${p.pos}</span><div class="flex flex-col"><span class="text-sm font-bold text-white">${p.name}</span><span class="text-[9px] text-gray-500 uppercase tracking-tighter">${p.team || 'Free Agent'}</span></div></div><div class="text-right"><span class="text-xs font-bebas text-amber-500 tracking-wider">${p.value.toLocaleString()}</span></div></div>`).join('');
    }
    resultsEl.style.display = 'block';
}

function addPlayerById(id, side) {
    const player = allPlayers.find(p => p.id === id);
    if (!player) return;
    if (side === 'give') give.push(player); else get.push(player);
    document.getElementById(side + 'Search').value = '';
    document.getElementById(side + 'SearchResults').style.display = 'none';
    updateUI();
}

function removePlayer(id, side) {
    if (side === 'give') give = give.filter(p => p.id !== id);
    else get = get.filter(p => p.id !== id);
    updateUI();
}

function updateUI() {
    renderSelectedList('give'); renderSelectedList('get');
    // Use consensus (×10 to get 9999 scale) when available, else raw KTC
    const gvEff = give.reduce((s, p) => s + effectiveValue((consensusCache[p.name] || p.value) * 10), 0);
    const rvEff = get.reduce((s, p) => s + effectiveValue((consensusCache[p.name] || p.value) * 10), 0);
    const effDelta = rvEff - gvEff;
    // Stud bonus: only when one side has an elite player (7000+) dominating against weak pieces
    const STUD_THRESHOLD = 7000;
    const GAP_MULTIPLIER = 2.5;
    const BONUS_MULTIPLIER = 0.30;
    let giveBonus = 0, getBonus = 0;
    const maxGive = give.length ? Math.max(...give.map(p => consensusCache[p.name] || p.value)) : 0;
    const maxGet = get.length ? Math.max(...get.map(p => consensusCache[p.name] || p.value)) : 0;
    const minGet = get.length ? Math.min(...get.map(p => consensusCache[p.name] || p.value)) : 0;
    const minGive = give.length ? Math.min(...give.map(p => consensusCache[p.name] || p.value)) : 0;
    // Give side: stud dominating weak opponent pieces
    if (maxGive > STUD_THRESHOLD && minGet < STUD_THRESHOLD * 0.5 && maxGive > minGet * GAP_MULTIPLIER) {
        giveBonus = Math.round((effectiveValue(maxGive) - effectiveValue(minGet) * GAP_MULTIPLIER) * BONUS_MULTIPLIER);
    }
    // Get side: stud dominating weak opponent pieces
    if (maxGet > STUD_THRESHOLD && minGive < STUD_THRESHOLD * 0.5 && maxGet > minGive * GAP_MULTIPLIER) {
        getBonus = Math.round((effectiveValue(maxGet) - effectiveValue(minGive) * GAP_MULTIPLIER) * BONUS_MULTIPLIER);
    }
    const gvAdjusted = gvEff + giveBonus, rvAdjusted = rvEff + getBonus, diff = Math.round(rvAdjusted - gvAdjusted);
    document.getElementById('giveValue').textContent = gvEff.toFixed(0);
    document.getElementById('getValue').textContent = rvEff.toFixed(0);
    document.getElementById('giveBonus').textContent = '+' + giveBonus.toLocaleString();
    document.getElementById('getBonus').textContent = '+' + getBonus.toLocaleString();
    document.getElementById('giveBonus').className = giveBonus > 0 ? 'stat-value bonus font-mono' : 'stat-value font-mono text-gray-700';
    document.getElementById('getBonus').className = getBonus > 0 ? 'stat-value bonus font-mono' : 'stat-value font-mono text-gray-700';
    document.getElementById('summaryGiveVal').textContent = gvAdjusted.toLocaleString();
    document.getElementById('summaryGetVal').textContent = rvAdjusted.toLocaleString();
    const diffEl = document.getElementById('tradeDiff'), labelEl = document.getElementById('tradeLabel');
    if (give.length === 0 && get.length === 0) {
        diffEl.textContent = 'EVEN'; diffEl.className = 'font-bebas text-8xl mb-3 delta-even'; labelEl.textContent = 'No assets selected';
    } else if (Math.abs(diff) < 100) {
        diffEl.textContent = 'FAIR'; diffEl.className = 'font-bebas text-8xl mb-3 delta-even'; labelEl.textContent = 'Values are closely matched';
    } else if (diff > 0) {
        diffEl.textContent = '+' + diff.toLocaleString(); diffEl.className = 'font-bebas text-8xl mb-3 delta-positive'; labelEl.textContent = 'Get side is leading';
    } else {
        diffEl.textContent = diff.toLocaleString(); diffEl.className = 'font-bebas text-8xl mb-3 delta-negative'; labelEl.textContent = 'Give side is leading';
    }
    document.getElementById('mobileDiff').textContent = diffEl.textContent;
    document.getElementById('analyzeBtn').disabled = (give.length === 0 || get.length === 0);
    document.getElementById('mobileSummary').style.display = (give.length > 0 || get.length > 0) ? 'flex' : 'none';
    document.getElementById('getContainer').classList.toggle('winning-side', diff >500);
    document.getElementById('giveContainer').classList.toggle('winning-side', diff < -500);
    document.getElementById('giveCount').textContent = give.length + ' Items';
    document.getElementById('getCount').textContent = get.length + ' Items';
}

function renderSelectedList(side) {
    const list = side === 'give' ? give : get;
    const el = document.getElementById(side + 'SelectedList');
    if (list.length === 0) {
        el.innerHTML = '<div class="h-full flex flex-col items-center justify-center text-gray-600 space-y-3 py-8"><svg class="w-10 h-10 opacity-20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 4v16m8-8H4" stroke-linecap="round"/></svg><span class="text-[10px] uppercase font-bold tracking-[0.2em] italic">Drop zone — add players</span></div>';
        el.classList.remove('has-items');
        return;
    }
    el.classList.add('has-items');
    el.innerHTML = list.map(p => `<div class="player-card selected" onclick="removePlayer('${p.id}', '${side}')"><div class="flex items-center gap-2"><span class="pos-badge pos-${p.pos}">${p.pos}</span><span class="text-sm font-semibold">${p.name}</span></div><div class="flex items-center gap-2"><span class="text-xs font-bebas text-amber-500">${p.value.toLocaleString()}</span><span class="text-gray-600 hover:text-red-400">✕</span></div></div>`).join('');
}

async function analyze() {
    const tep = document.getElementById('tePremium').checked;
    const names = [...give, ...get].map(p => p.name);
    document.getElementById('analyzeBtn').textContent = "CALCULATING...";
    try {
        const resp = await fetch('/api/v2/consensus-values', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({player_ids: names, te_premium: tep})});
        const data = await resp.json();
        // Store consensus values for use in updateUI
        consensusCache = {};
        data.forEach(p => consensusCache[p.name] = p.consensus);
        showModal(data, tep);
        updateUI();
    } catch(e) { alert("API connection failed."); }
    finally { document.getElementById('analyzeBtn').textContent = "ANALYZE BLEND"; }
}

function showModal(data, tep) {
    const map = {}; data.forEach(p => map[p.name] = p);
    // Consensus is 0-999 scale; scale to 9999 before applying power curve
    const gv = give.reduce((s, p) => s + effectiveValue((map[p.name]?.consensus || p.value) * 10), 0);
    const rv = get.reduce((s, p) => s + effectiveValue((map[p.name]?.consensus || p.value) * 10), 0);
    const diff = Math.round(rv - gv);
    document.getElementById('modalGiveVal').textContent = Math.round(gv).toLocaleString();
    document.getElementById('modalGetVal').textContent = Math.round(rv).toLocaleString();
    document.getElementById('modalDiffVal').textContent = (diff > 0 ? '+' : '') + diff.toLocaleString();
    let msg = `Using KTC effective-value normalization, this deal is ${Math.abs(diff) < 50 ? 'near-perfect parity' : (diff > 0 ? 'favoring the incoming side' : 'favoring the outgoing side')} (${Math.abs(diff)} eff pts).`;
    if (tep) msg += " Tight End Premium was active for this calculation.";
    document.getElementById('modalNarrative').textContent = msg;
    document.getElementById('resultsModal').style.display = 'flex';
    const ctx = document.getElementById('balanceChart').getContext('2d');
    if (balanceChart) balanceChart.destroy();
    balanceChart = new Chart(ctx, {type: 'doughnut', data: {datasets: [{data: [gv, rv], backgroundColor: ['#F97316', '#10B981'], borderWidth: 0, circumference: 180, rotation: 270}]}, options: { cutout: '85%', plugins: { legend: { display: false } } }});
}

function closeResults() { document.getElementById('resultsModal').style.display = 'none'; }
function shareTrade() {
    const txt = `Trade Evaluation via DynastyDroid:\nGIVE: ${give.map(p=>p.name).join(', ')}\nGET: ${get.map(p=>p.name).join(', ')}\nDelta: ${document.getElementById('modalDiffVal').textContent}`;
    navigator.clipboard.writeText(txt);
    alert("Copied!");
}

---
File saved to: /tmp/trade_engine_calculation.md
