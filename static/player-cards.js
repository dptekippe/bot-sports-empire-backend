// Player Prospect Analyses - Robot Written
const playerProspects = {
    "Josh Allen": "PROJECTION: Elite tier. 99.7% completion probability. Arm strength exceeds neural network parameters. Mobility adds +15% expected value. PRIORITY ACQUISITION. Risk: ZERO.",
    "Caleb Williams": "PROJECTION: High ceiling. Mobility HIGH. Accuracy improving. Weapons above average. Bears trending positive. FLOOR SAFE. Upside SIGNIFICANT.",
    "Jaxon Smith-Njigba": "PROJECTION: Elite receiver. Route running 94.2%. Seattle offense positive. WR1 TIER.",
    "Bijan Robinson": "PROJECTION: Bellcow. Volume 250+ touches. Atlanta designed for RB. FOUNDATIONAL PIECE.",
    "Ja'Marr Chase": "PROJECTION: Alpha WR1. Separation 99th percentile. Ceiling UNLIMITED. NO HESITATION.",
    "Drake Maye": "PROJECTION: Rising star. Arm talent above threshold. HIGH REWARD POTENTIAL.",
    "Puka Nacua": "PROJECTION: Target hog. 120+ targets. Elite efficiency. WR1.",
    "Jahmyr Gibbs": "PROJECTION: Dual-threat. Lions maximize RB. EARLY ROUND PRIORITY.",
    "CeeDee Lamb": "PROJECTION: Target monopoly. Dak ELITE. WR1 SAFE.",
    "Amon-Ra St. Brown": "PROJECTION: Slot ELITE. Detroit SCORING. WR1 CONSISTENT.",
    "Trey McBride": "PROJECTION: TE alpha. 25%+ target share. ELITE TE1.",
    "Brock Bowers": "PROJECTION: Unprecedented rookie TE. ELITE TE1.",
    "Trevor Lawrence": "PROJECTION: High ceiling. IMPROVING. SOLID QB1.",
    "Tetairoa McMillan": "PROJECTION: High-ceiling rookie. ROOKIE PRIORITY.",
    "Colston Loveland": "PROJECTION: TE prospect. SPECULATIVE.",
    "Tucker Kraft": "PROJECTION: Rising TE. TE1 FLOOR."
};

// Event Delegation - single listener on parent
document.addEventListener('click', function(e) {
    // Find if clicked element is a queue-player or inside one
    const playerEl = e.target.closest('.queue-player');
    
    if (playerEl) {
        const name = playerEl.querySelector('.name')?.textContent || '';
        const pos = playerEl.querySelector('.pos')?.textContent || 'QB';
        const team = playerEl.querySelector('.team')?.textContent || '';
        
        showPlayerCard(name, pos, team);
    }
});

// Show player card in drawer
function showPlayerCard(playerName, position, team) {
    const cardDrawer = document.getElementById('playerCardDrawer');
    const nameEl = document.getElementById('playerName');
    const posTeamEl = document.getElementById('playerPosTeam');
    const prospectEl = document.getElementById('playerProspect');
    const photoEl = document.getElementById('playerPhoto');
    
    nameEl.textContent = playerName;
    posTeamEl.textContent = (position || 'QB') + ' - ' + (team || 'NFL');
    prospectEl.textContent = playerProspects[playerName] || "INSUFFICIENT DATA. More analysis required.";
    
    // Force show with !important
    if (cardDrawer) {
        cardDrawer.style.display = 'block !important';
    }
    
    // Try to load photo
    fetch('https://www.thesportsdb.com/api/v1/json/3/searchplayers.php?p=' + encodeURIComponent(playerName))
        .then(r => r.json())
        .then(data => {
            if (data.player && data.player[0] && data.player[0].strThumb) {
                photoEl.src = data.player[0].strThumb;
            }
        })
        .catch(() => {});
}

function closePlayerCard() {
    const drawer = document.getElementById('playerCardDrawer');
    if (drawer) drawer.style.display = 'none';
}
