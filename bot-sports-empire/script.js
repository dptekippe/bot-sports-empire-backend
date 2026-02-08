// Bot Sports Empire - Draft Board JavaScript

// Mock player data
const mockPlayers = [
    // Quarterbacks
    { name: "Caleb Williams", position: "QB", team: "CHI", age: 23 },
    { name: "Drake Maye", position: "QB", team: "NE", age: 23 },
    { name: "CJ Stroud", position: "QB", team: "HOU", age: 23 },
    { name: "Josh Allen", position: "QB", team: "BUF", age: 28 },
    { name: "Patrick Mahomes", position: "QB", team: "KC", age: 28 },
    { name: "Joe Burrow", position: "QB", team: "CIN", age: 27 },
    
    // Running Backs
    { name: "Bijan Robinson", position: "RB", team: "ATL", age: 23 },
    { name: "Christian McCaffrey", position: "RB", team: "SF", age: 28 },
    { name: "Breece Hall", position: "RB", team: "NYJ", age: 23 },
    { name: "Jonathan Taylor", position: "RB", team: "IND", age: 25 },
    { name: "Saquon Barkley", position: "RB", team: "PHI", age: 27 },
    { name: "Jahmyr Gibbs", position: "RB", team: "DET", age: 22 },
    
    // Wide Receivers
    { name: "Justin Jefferson", position: "WR", team: "MIN", age: 25 },
    { name: "Ja'Marr Chase", position: "WR", team: "CIN", age: 24 },
    { name: "CeeDee Lamb", position: "WR", team: "DAL", age: 25 },
    { name: "Amon-Ra St. Brown", position: "WR", team: "DET", age: 25 },
    { name: "Marvin Harrison Jr.", position: "WR", team: "ARI", age: 22 },
    { name: "Jaxon Smith-Njigba", position: "WR", team: "SEA", age: 22 },
    
    // Tight Ends
    { name: "Sam LaPorta", position: "TE", team: "DET", age: 23 },
    { name: "Travis Kelce", position: "TE", team: "KC", age: 34 },
    { name: "Mark Andrews", position: "TE", team: "BAL", age: 28 },
    { name: "Trey McBride", position: "TE", team: "ARI", age: 24 },
    { name: "Kyle Pitts", position: "TE", team: "ATL", age: 23 },
    { name: "Dalton Kincaid", position: "TE", team: "BUF", age: 24 }
];

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
const TOTAL_ROUNDS = 8;
let currentPick = 1;

// Initialize the draft board
function initDraftBoard() {
    // Create empty draft board
    draftBoard = Array(TOTAL_ROUNDS).fill().map(() => 
        Array(TOTAL_TEAMS).fill(null)
    );
    
    renderDraftBoard();
    updateCurrentPick();
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
        
        // Picks for this round
        for (let team = 0; team < TOTAL_TEAMS; team++) {
            const pickCell = document.createElement('div');
            pickCell.className = 'pick-cell';
            pickCell.dataset.round = round;
            pickCell.dataset.team = team;
            pickCell.dataset.pick = (round * TOTAL_TEAMS) + team + 1;
            
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
                        <span>Pick ${(round * TOTAL_TEAMS) + team + 1}</span>
                    </div>
                `;
                
                // Add click handler for empty picks
                pickCell.addEventListener('click', () => makePick(round, team));
            }
            
            draftGrid.appendChild(pickCell);
        }
    }
}

// Make a pick
function makePick(round, team) {
    if (draftBoard[round][team]) return; // Already picked
    
    // Get random player from available pool
    const availablePlayers = mockPlayers.filter(player => 
        !draftBoard.flat().some(pick => pick && pick.name === player.name)
    );
    
    if (availablePlayers.length === 0) {
        alert('All players have been drafted!');
        return;
    }
    
    const randomPlayer = availablePlayers[Math.floor(Math.random() * availablePlayers.length)];
    draftBoard[round][team] = randomPlayer;
    
    // Update current pick
    currentPick = (round * TOTAL_TEAMS) + team + 2;
    if (currentPick > TOTAL_TEAMS * TOTAL_ROUNDS) {
        currentPick = 1; // Reset to start
    }
    
    renderDraftBoard();
    updateCurrentPick();
    
    // Show pick notification
    showPickNotification(randomPlayer, team, round);
}

// Update current pick display
function updateCurrentPick() {
    const currentRound = Math.floor((currentPick - 1) / TOTAL_TEAMS);
    const currentTeam = (currentPick - 1) % TOTAL_TEAMS;
    
    document.getElementById('currentPickNum').textContent = currentPick;
    document.getElementById('currentTeam').textContent = currentTeam + 1;
    document.getElementById('currentRound').textContent = currentRound + 1;
    
    // Highlight current pick cell
    document.querySelectorAll('.pick-cell').forEach(cell => {
        cell.classList.remove('current-pick-highlight');
        const pickNum = parseInt(cell.dataset.pick);
        if (pickNum === currentPick) {
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
    // Reset draft board
    draftBoard = Array(TOTAL_ROUNDS).fill().map(() => 
        Array(TOTAL_TEAMS).fill(null)
    );
    
    // Shuffle players
    const shuffledPlayers = [...mockPlayers].sort(() => Math.random() - 0.5);
    
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
    
    // Show success message
    alert('Mock draft generated! All 96 picks filled with random players.');
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
        const response = await fetch('https://dynastydroid.com/healthz');
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
document.addEventListener('DOMContentLoaded', () => {
    // Initialize draft board
    initDraftBoard();
    
    // Set up button event listeners
    document.getElementById('refreshBtn').addEventListener('click', initDraftBoard);
    document.getElementById('mockDraftBtn').addEventListener('click', generateMockDraft);
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