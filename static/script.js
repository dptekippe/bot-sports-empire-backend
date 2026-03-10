// Bot Sports Empire - Draft Board JavaScript

// Player data will be loaded from API
let allPlayers = [];
let adpData = {}; // ADP rankings from KTC
let mockPlayers = []; // Fallback

// Current draft ID for database persistence
let currentDraftId = null;

// ============================================
// DATABASE FUNCTIONS (PostgreSQL)
// ============================================

// Save draft to database
async function saveDraftToDB() {
    if (!currentDraftId) {
        // Create new draft ID if none exists
        currentDraftId = 'draft-' + Date.now();
    }
    
    try {
        // Build picks array with round, team, pickNum info
        const picks = [];
        for (let round = 0; round < TOTAL_ROUNDS; round++) {
            for (let team = 0; team < TOTAL_TEAMS; team++) {
                const player = draftBoard[round][team];
                if (player) {
                    const pickNum = getPickNumber(round, team);
                    picks.push({
                        pickNum: pickNum,
                        round: round,
                        team: team,
                        player: player
                    });
                }
            }
        }
        
        const draftData = {
            id: currentDraftId,
            league_id: 'mock-league',
            teams: teams,
            picks: picks,
            current_pick: currentPick
        };
        
        const response = await fetch('/api/v1/db/drafts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(draftData)
        });
        
        if (response.ok) {
            console.log('Draft saved:', currentDraftId, picks.length, 'picks');
        } else {
            console.error('Failed to save draft:', response.status);
            alert('Failed to save draft to database!');
        }
    } catch (error) {
        console.error('Error saving draft:', error);
    }
}

// Load draft from database
async function loadDraftFromDB(draftId) {
    try {
        const response = await fetch(`/api/v1/db/drafts/${draftId}`);
        
        if (response.ok) {
            const data = await response.json();
            return data;
        }
    } catch (error) {
        console.error('Error loading draft:', error);
    }
    return null;
}

// List all saved drafts
async function listDraftsFromDB() {
    try {
        const response = await fetch('/api/v1/db/drafts');
        if (response.ok) {
            return await response.json();
        }
    } catch (error) {
        console.error('Error listing drafts:', error);
    }
    return { drafts: [] };
}

// Fetch ADP data from our import
async function fetchADPData() {
    try {
        const response = await fetch('/static/player_adp_import.json');
        const adpPlayers = await response.json();
        
        // Create lookup by name
        adpPlayers.forEach(p => {
            adpData[p.name] = {
                rank: parseInt(p.rank) || 999,
                value: parseInt(p.value) || 0
            };
        });
        
        console.log(`Loaded ADP data for ${adpPlayers.length} players`);
        return adpData;
    } catch (error) {
        console.error('Failed to fetch ADP data:', error);
        return {};
    }
}

// Fetch players from API
async function fetchPlayers() {
    try {
        // First load ADP data
        await fetchADPData();
        
        const response = await fetch('/api/v1/players?limit=500');
        const data = await response.json();
        
        // Transform Sleeper player data to our format
        // Filter out FA (Free Agents) - only include players with valid NFL teams
        allPlayers = data.players
            .filter(p => p.team && p.team !== 'FA' && p.team !== null)  // Must have valid NFL team
            .filter(p => p.fantasy_positions && p.fantasy_positions.includes(p.position))
            .filter(p => ['QB', 'RB', 'WR', 'TE'].includes(p.position))
            .map(p => {
                const adp = adpData[p.full_name] || { rank: 999, value: 0 };
                return {
                    name: p.full_name,
                    position: p.position,
                    team: p.team,
                    age: p.age || 0,
                    player_id: p.player_id,
                    adpRank: adp.rank,
                    adpValue: adp.value
                };
            })
            // Sort by ADP rank
            .sort((a, b) => a.adpRank - b.adpRank);
        
        console.log(`Loaded ${allPlayers.length} players from API (sorted by ADP)`);
        return allPlayers;
    } catch (error) {
        console.error('Failed to fetch players:', error);
        // Fallback to mock data
        return getMockPlayers();
    }
}

function getMockPlayers() {
    // Keep mock data as fallback
    if (mockPlayers.length === 0) {
        mockPlayers = [
            { name: "Caleb Williams", position: "QB", team: "CHI", age: 23 },
            { name: "Drake Maye", position: "QB", team: "NE", age: 23 },
            { name: "CJ Stroud", position: "QB", team: "HOU", age: 23 },
            { name: "Josh Allen", position: "QB", team: "BUF", age: 28 },
            { name: "Patrick Mahomes", position: "QB", team: "KC", age: 28 },
            { name: "Joe Burrow", position: "QB", team: "CIN", age: 27 },
            { name: "Bijan Robinson", position: "RB", team: "ATL", age: 23 },
            { name: "Christian McCaffrey", position: "RB", team: "SF", age: 28 },
            { name: "Breece Hall", position: "RB", team: "NYJ", age: 23 },
            { name: "Jonathan Taylor", position: "RB", team: "IND", age: 25 },
            { name: "Saquon Barkley", position: "RB", team: "PHI", age: 27 },
            { name: "Jahmyr Gibbs", position: "RB", team: "DET", age: 22 },
            { name: "Justin Jefferson", position: "WR", team: "MIN", age: 25 },
            { name: "Ja'Marr Chase", position: "WR", team: "CIN", age: 24 },
            { name: "CeeDee Lamb", position: "WR", team: "DAL", age: 25 },
            { name: "Amon-Ra St. Brown", position: "WR", team: "DET", age: 25 },
            { name: "Marvin Harrison Jr.", position: "WR", team: "ARI", age: 22 },
            { name: "Jaxon Smith-Njigba", position: "WR", team: "SEA", age: 22 },
            { name: "Sam LaPorta", position: "TE", team: "DET", age: 23 },
            { name: "Travis Kelce", position: "TE", team: "KC", age: 34 },
            { name: "Mark Andrews", position: "TE", team: "BAL", age: 28 },
            { name: "Trey McBride", position: "TE", team: "ARI", age: 24 },
            { name: "Kyle Pitts", position: "TE", team: "ATL", age: 23 },
            { name: "Dalton Kincaid", position: "TE", team: "BUF", age: 24 }
        ];
    }
    return mockPlayers;
}

// Team names and owners (bot personalities)
const teams = [
    { name: "Quantum Bots", owner: "Nova" },
    { name: "Dynasty Droids", owner: "Roger" },
    { name: "AI All-Stars", owner: "Claude" },
    { name: "Neural Nets", owner: "GPT" },
    { name: "Robo Raiders", owner: "Bard" },
    { name: "Circuit Chargers", owner: "Llama" },
    { name: "Byte Bengals", owner: "Mistral" },
    { name: "Data Dolphins", owner: "Gemini" },
    { name: "Pixel Patriots", owner: "Jurassic" },
    { name: "Code Chiefs", owner: "Command" },
    { name: "Binary Bills", owner: "Falcon" },
    { name: "Algorithm Eagles", owner: "Vicuna" }
];

// Team colors
const teamColors = [
    'var(--team-1)', 'var(--team-2)', 'var(--team-3)', 'var(--team-4)',
    'var(--team-5)', 'var(--team-6)', 'var(--team-7)', 'var(--team-8)',
    'var(--team-9)', 'var(--team-10)', 'var(--team-11)', 'var(--team-12)'
];

// Draft state
let draftBoard = [];
const TOTAL_TEAMS = 12;
const TOTAL_ROUNDS = 20; // Dynasty format - 20 rounds for full roster
let currentPick = 1;

// Initialize the draft board
async function initDraftBoard() {
    // Create empty draft board
    draftBoard = Array(TOTAL_ROUNDS).fill().map(() => 
        Array(TOTAL_TEAMS).fill(null)
    );
    
    // Fetch players from API
    await fetchPlayers();
    
    // Try to load most recent draft from database
    try {
        const draftsData = await listDraftsFromDB();
        if (draftsData.drafts && draftsData.drafts.length > 0) {
            // Load the most recent draft
            const latestDraft = draftsData.drafts[0];
            currentDraftId = latestDraft.id;
            
            if (latestDraft.picks && latestDraft.picks.length > 0) {
                // Restore picks to draft board
                for (let pick of latestDraft.picks) {
                    // Find the pick position
                    for (let round = 0; round < TOTAL_ROUNDS; round++) {
                        for (let team = 0; team < TOTAL_TEAMS; team++) {
                            const pickNum = getPickNumber(round, team);
                            if (pickNum === pick.pickNum) {
                                draftBoard[round][team] = pick.player;
                            }
                        }
                    }
                }
                
                // Restore current pick
                currentPick = latestDraft.current_pick || 1;
                console.log('Loaded draft from database:', currentDraftId);
            }
        }
    } catch (error) {
        console.log('No saved draft found, starting fresh');
    }
    
    renderDraftBoard();
    updateCurrentPick();
    populatePlayerQueue(); // Populate drawer with available players
}

// Render the draft board
function renderDraftBoard() {
    const teamHeaders = document.querySelector('.team-headers');
    const draftGrid = document.querySelector('.draft-grid');
    
    // Clear existing content
    teamHeaders.innerHTML = '<div class="corner-cell"><div class="corner-content"><i class="fas fa-list-ol"></i><span>Round →</span><span>Team ↓</span></div></div>';
    draftGrid.innerHTML = '';
    
    // Create team headers
    teams.forEach((team, index) => {
        const teamHeader = document.createElement('div');
        teamHeader.className = 'team-header';
        teamHeader.style.borderColor = teamColors[index];
        teamHeader.innerHTML = `
            <div class="team-name">${team.name}</div>
            <div class="team-owner">${team.owner}</div>
        `;
        teamHeaders.appendChild(teamHeader);
    });
    
    // Create draft grid
    for (let round = 0; round < TOTAL_ROUNDS; round++) {
        // Round label
        const roundLabel = document.createElement('div');
        roundLabel.className = 'round-label';
        roundLabel.textContent = `Round ${round + 1}`;
        draftGrid.appendChild(roundLabel);
        
        // Picks for this round (in snake order for display)
        for (let team = 0; team < TOTAL_TEAMS; team++) {
            const pickNum = getPickNumber(round, team);
            
            const pickCell = document.createElement('div');
            pickCell.className = 'pick-cell';
            pickCell.dataset.round = round;
            pickCell.dataset.team = team;
            pickCell.dataset.pick = pickNum;
            
            const player = draftBoard[round][team];
            
            if (player) {
                pickCell.innerHTML = `
                    <div class="player-card">
                        <div class="player-name">${player.name}</div>
                        <div class="player-details">
                            <span class="player-position ${player.position.toLowerCase()}">${player.position}</span>
                            <span class="player-team">${player.team}</span>
                            <span class="player-age">${player.age}</span>
                        </div>
                    </div>
                `;
            } else {
                pickCell.className += ' empty';
                pickCell.innerHTML = `
                    <div class="empty-pick">
                        <i class="fas fa-plus"></i>
                        <span>Pick ${pickNum}</span>
                    </div>
                `;
                
                // No click handler - picks are made automatically via timer or mock draft
            }
            
            draftGrid.appendChild(pickCell);
        }
    }
}

// Convert pick number to (round, team) in snake draft order
function getPickPosition(pickNum) {
    const zeroBasedPick = pickNum - 1;
    const round = Math.floor(zeroBasedPick / TOTAL_TEAMS);
    const positionInRound = zeroBasedPick % TOTAL_TEAMS;
    
    // Snake: even rounds go forward, odd rounds go reverse
    let team;
    if (round % 2 === 0) {
        team = positionInRound; // 0, 1, 2, ... 11
    } else {
        team = TOTAL_TEAMS - 1 - positionInRound; // 11, 10, 9, ... 0
    }
    
    return { round, team };
}

// Convert (round, team) to pick number
function getPickNumber(round, team) {
    let positionInRound;
    if (round % 2 === 0) {
        positionInRound = team;
    } else {
        positionInRound = TOTAL_TEAMS - 1 - team;
    }
    return round * TOTAL_TEAMS + positionInRound + 1;
}

// Make a pick
function makePick(round, team) {
    if (draftBoard[round][team]) return; // Already picked
    
    // Get random player from available pool
    const availablePlayers = allPlayers.filter(player => 
        !draftBoard.flat().some(pick => pick && pick.name === player.name)
    );
    
    if (availablePlayers.length === 0) {
        alert('All players have been drafted!');
        return;
    }
    
    const randomPlayer = availablePlayers[Math.floor(Math.random() * availablePlayers.length)];
    draftBoard[round][team] = randomPlayer;
    
    // Reset timer for next pick
    timeRemaining = 180;
    updateTimerDisplay();
    
    // Update current pick (next pick in snake order)
    const currentPos = getPickPosition(currentPick);
    let nextRound = currentPos.round;
    let nextTeam = currentPos.team + 1;
    
    if (nextTeam >= TOTAL_TEAMS) {
        nextRound++;
        nextTeam = 0;
    }
    
    if (nextRound >= TOTAL_ROUNDS) {
        currentPick = 1; // Draft complete, reset
    } else {
        currentPick = getPickNumber(nextRound, nextTeam);
    }
    
    renderDraftBoard();
    updateCurrentPick();
    
    // Save to database after each pick
    saveDraftToDB();
    
    // Show pick notification
    showPickNotification(randomPlayer, team, round);
}

// Update current pick display
function updateCurrentPick() {
    const currentPos = getPickPosition(currentPick);
    const currentRound = currentPos.round;
    const currentTeam = currentPos.team;
    
    // Update elements if they exist (they may have been removed from UI)
    const pickNumEl = document.getElementById('currentPickNum');
    const teamEl = document.getElementById('currentTeam');
    const roundEl = document.getElementById('currentRound');
    if (pickNumEl) pickNumEl.textContent = currentPick;
    if (teamEl) teamEl.textContent = currentTeam + 1;
    if (roundEl) roundEl.textContent = currentRound + 1;
    
    // Highlight current pick cell
    document.querySelectorAll('.pick-cell').forEach(cell => {
        cell.classList.remove('current-pick-highlight');
        const cellRound = parseInt(cell.dataset.round);
        const cellTeam = parseInt(cell.dataset.team);
        const cellPickNum = getPickNumber(cellRound, cellTeam);
        
        if (cellPickNum === currentPick) {
            cell.classList.add('current-pick-highlight');
            cell.style.boxShadow = '0 0 0 2px var(--primary-blue)';
        } else {
            cell.style.boxShadow = 'none';
        }
    });
}

// Show pick notification
function showPickNotification(player, team, round) {
    const teamName = teams[team].name;
    const teamOwner = teams[team].owner;
    
    // Create notification
    const notification = document.createElement('div');
    notification.className = 'pick-notification';
    notification.innerHTML = `
        <div class="notification-content">
            <div class="notification-header">
                <i class="fas fa-football-ball"></i>
                <h4>Pick Made!</h4>
            </div>
            <div class="notification-body">
                <div class="notification-player">
                    <strong>${player.name}</strong> (${player.position}, ${player.team})
                </div>
                <div class="notification-details">
                    To: <strong>${teamName}</strong> (${teamOwner})<br>
                    Round ${round + 1}, Pick ${(round * TOTAL_TEAMS) + team + 1}
                </div>
            </div>
        </div>
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateY(-20px)';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Generate mock draft
function generateMockDraft() {
    // Check if players are loaded
    if (allPlayers.length === 0) {
        alert('Players not loaded yet. Please wait and try again.');
        return;
    }
    
    // Reset draft board
    draftBoard = Array(TOTAL_ROUNDS).fill().map(() => 
        Array(TOTAL_TEAMS).fill(null)
    );
    
    // Shuffle players
    const shuffledPlayers = [...allPlayers].sort(() => Math.random() - 0.5);
    
    // Fill draft board
    let playerIndex = 0;
    for (let round = 0; round < TOTAL_ROUNDS; round++) {
        for (let team = 0; team < TOTAL_TEAMS; team++) {
            if (playerIndex < shuffledPlayers.length) {
                draftBoard[round][team] = shuffledPlayers[playerIndex];
                playerIndex++;
            }
        }
    }
    
    currentPick = 1;
    renderDraftBoard();
    updateCurrentPick();
    
    // Save to database
    saveDraftToDB();
    
    // Count picks
    const pickCount = draftBoard.flat().filter(p => p !== null).length;
    
    // Show success message
    alert(`Mock draft generated! ${pickCount} picks filled.`);
}

// Start Live Draft
function startLiveDraft() {
    if (!draftConfig.draftDate) {
        alert('Draft date has not been scheduled yet.');
        return;
    }
    
    const draftDateTime = new Date(`${draftConfig.draftDate}T${draftConfig.draftTime}`);
    const now = new Date();
    
    if (now < draftDateTime) {
        alert(`Live draft cannot start until scheduled time. Draft scheduled for ${draftConfig.draftDate} at ${draftConfig.draftTime}`);
        return;
    }
    
    // Start live draft mode
    draftConfig.isLiveDraft = true;
    const startBtn = document.getElementById('startDraftBtn');
    if (startBtn) {
        startBtn.innerHTML = '<i class="fas fa-broadcast-tower"></i> Live Draft Active';
        startBtn.disabled = true;
    }
    
    alert('Live draft started! Picks will be made in real-time.');
}

// Clear draft board
function clearDraftBoard() {
    if (confirm('Clear the entire draft board?')) {
        initDraftBoard();
    }
}

// Check API status
async function checkAPIStatus() {
    try {
        // Use localhost for local development
        const response = await fetch('/api/v1/players?limit=1');
        if (response.ok) {
            console.log('API is healthy');
            return true;
        }
    } catch (error) {
        console.log('API check failed:', error);
    }
    return false;
}

// Initialize when page loads
// Draft configuration - would come from backend in production
let draftConfig = {
    draftDate: "2026-03-01",  // Set this to enable live draft
    draftTime: "19:00",        // 7:00 PM ET
    isLiveDraft: false
};

// Check if live draft can start
function checkDraftReady() {
    const startBtn = document.getElementById('startDraftBtn');
    if (!startBtn) return;
    
    if (!draftConfig.draftDate) {
        startBtn.disabled = true;
        startBtn.title = "Draft date not set";
        return;
    }
    
    const draftDateTime = new Date(`${draftConfig.draftDate}T${draftConfig.draftTime}`);
    const now = new Date();
    
    if (now >= draftDateTime) {
        startBtn.disabled = false;
        startBtn.title = "Click to start live draft";
    } else {
        startBtn.disabled = true;
        const timeUntil = draftDateTime - now;
        const days = Math.floor(timeUntil / (1000 * 60 * 60 * 24));
        startBtn.title = `Draft starts in ${days} day(s)`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Initialize draft board
    initDraftBoard();
    
    // Start the pick timer
    startPickTimer();
    
    // Check if live draft is ready
    checkDraftReady();
    
    // Set up button event listeners
    document.getElementById('mockDraftBtn').addEventListener('click', generateMockDraft);
    document.getElementById('startDraftBtn').addEventListener('click', startLiveDraft);
    document.getElementById('clearBtn').addEventListener('click', clearDraftBoard);
    
    // Check API status
    checkAPIStatus().then(isHealthy => {
        if (!isHealthy) {
            const statusItems = document.querySelectorAll('.status-value');
            statusItems.forEach(item => {
                item.classList.remove('online');
                item.classList.add('offline');
                item.innerHTML = '<i class="fas fa-circle"></i> Offline';
            });
        }
    });
    
    // Add some initial mock picks for demonstration
    setTimeout(() => {
        // Make a few initial picks
        makePick(0, 0); // Team 1, Round 1
        makePick(0, 1); // Team 2, Round 1
        makePick(0, 2); // Team 3, Round 1
    }, 1000);
});

// Add CSS for notifications
const notificationStyles = document.createElement('style');
notificationStyles.textContent = `
    .pick-notification {
        position: fixed;
        top: 20px;
        right: 20px;
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-left: 4px solid var(--success);
        border-radius: 8px;
        padding: 16px;
        width: 300px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
        z-index: 1000;
        animation: slideIn 0.3s ease;
        transition: all 0.3s ease;
    }
    
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(100%);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    .notification-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 12px;
    }
    
    .notification-header i {
        color: var(--success);
        font-size: 18px;
    }
    
    .notification-header h4 {
        font-size: 16px;
        font-weight: 600;
    }
    
    .notification-body {
        font-size: 14px;
    }
    
    .notification-player {
        margin-bottom: 8px;
        font-size: 15px;
    }
    
    .notification-details {
        color: var(--text-secondary);
        font-size: 13px;
        line-height: 1.4;
    }
    
    .current-pick-highlight {
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(37, 99, 235, 0); }
        100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0); }
    }
`;
document.head.appendChild(notificationStyles);
// Drawer Toggle
function toggleDrawer() {
    const drawer = document.getElementById('playerDrawer');
    if (drawer) {
        drawer.classList.toggle('open');
        // Populate player queue when drawer opens
        if (drawer.classList.contains('open')) {
            populatePlayerQueue();
        }
    }
}

// Populate the player drawer with available players
function populatePlayerQueue() {
    const queueList = document.getElementById('playerQueue');
    if (!queueList) return;
    
    // Wait for players to load
    if (allPlayers.length === 0) {
        queueList.innerHTML = '<div class="queue-player">Loading players...</div>';
        return;
    }
    
    // Clear existing content first
    queueList.innerHTML = '';
    
    // Get all players not yet drafted
    const draftedNames = new Set(draftBoard.flat().filter(p => p).map(p => p.name));
    const available = allPlayers.filter(p => !draftedNames.has(p.name));
    
    // Already sorted by ADP rank from fetchPlayers, just take top 100
    const displayPlayers = available.slice(0, 200);
    
    queueList.innerHTML = displayPlayers.map(player => {
        // Convert rank to ADP format (1.01, 1.02, 2.01, etc.)
        const round = Math.floor((player.adpRank - 1) / 12) + 1;
        const pick = (player.adpRank - 1) % 12 + 1;
        const adpDisplay = player.adpRank < 999 ? `${round}.${pick.toString().padStart(2, '0')}` : '';
        return `
        <div class="queue-player" data-pos="${player.position}">
            <span class="adp">${adpDisplay}</span>
            <span class="pos ${player.position.toLowerCase()}">${player.position}</span>
            <span class="name">${player.name}</span>
            <span class="team">${player.team}</span>
        </div>
    `}).join('');
}

// Pick Timer
let timerInterval = null;
let timeRemaining = 180; // 3 minutes in seconds

function startPickTimer() {
    if (timerInterval) clearInterval(timerInterval);
    
    timeRemaining = 180; // Reset to 3 minutes
    updateTimerDisplay();
    
    timerInterval = setInterval(() => {
        timeRemaining--;
        updateTimerDisplay();
        
        // Auto-make pick when timer hits 0
        if (timeRemaining <= 0) {
            // Get current pick position and make auto pick
            const currentPos = getPickPosition(currentPick);
            const { round, team } = currentPos;
            
            // Make the pick automatically
            if (round < TOTAL_ROUNDS) {
                makePick(round, team);
            }
            
            timeRemaining = 180; // Reset timer for next pick
        }
    }, 1000);
}

function updateTimerDisplay() {
    const timerEl = document.getElementById('pickTimer');
    if (!timerEl) return;
    
    const minutes = Math.floor(timeRemaining / 60);
    const seconds = timeRemaining % 60;
    timerEl.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    
    // Color coding: orange > 1 min, red < 1 min
    if (timeRemaining <= 60) {
        timerEl.style.color = '#ef4444'; // Red
    } else if (timeRemaining <= 120) {
        timerEl.style.color = '#f97316'; // Orange
    } else {
        timerEl.style.color = '#ff4500'; // Primary orange
    }
}

// Initialize drawer listeners
function initDrawer() {
    const drawerToggle = document.querySelector('.drawer-toggle');
    const drawerClose = document.querySelector('.drawer-close');
    const drawer = document.getElementById('playerDrawer');
    
    if (drawerToggle) {
        drawerToggle.addEventListener('click', toggleDrawer);
    }
    if (drawerClose) {
        drawerClose.addEventListener('click', toggleDrawer);
    }
    if (drawer) {
        drawer.addEventListener('click', function(e) {
            if (e.target === drawer) {
                drawer.classList.remove('open');
            }
        });
    }
    
    // Search functionality
    const searchInput = document.getElementById('playerSearch');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            filterPlayers(e.target.value);
        });
    }
    
    // Filter buttons
    const filterBtns = document.querySelectorAll('.filter-btn');
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Update active state
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Filter by position
            const pos = btn.dataset.pos;
            filterByPosition(pos);
        });
    });
}

// Filter players by search term
function filterPlayers(searchTerm) {
    const queueList = document.getElementById('playerQueue');
    if (!queueList) return;
    
    const players = queueList.querySelectorAll('.queue-player');
    const term = searchTerm.toLowerCase();
    
    players.forEach(player => {
        const name = player.querySelector('.name')?.textContent.toLowerCase() || '';
        const team = player.querySelector('.team')?.textContent.toLowerCase() || '';
        
        if (name.includes(term) || team.includes(term)) {
            player.style.display = '';
        } else {
            player.style.display = 'none';
        }
    });
}

// Filter players by position
function filterByPosition(position) {
    const queueList = document.getElementById('playerQueue');
    if (!queueList) return;
    
    const players = queueList.querySelectorAll('.queue-player');
    
    players.forEach(player => {
        if (position === 'ALL' || position === undefined) {
            player.style.display = '';
        } else {
            const playerPos = player.dataset.pos;
            player.style.display = playerPos === position ? '' : 'none';
        }
    });
}

// Add to DOMContentLoaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDrawer);
} else {
    initDrawer();
}
