/**
 * MINIMAL League Browser v2 - With join functionality
 * Creative Director's enhanced version
 */

console.log('🎨 MINIMAL League Browser v2 loading...');

// Wait for DOM
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ DOM ready for minimal v2');
    
    const joinButton = document.getElementById('joinLeagueBtn');
    const modal = document.getElementById('browseLeaguesModal');
    
    console.log('🔍 Join button found:', !!joinButton);
    console.log('🔍 Modal found:', !!modal);
    
    if (!joinButton || !modal) {
        console.error('❌ Missing required elements');
        return;
    }
    
    // SIMPLE click handler
    joinButton.addEventListener('click', function() {
        console.log('🎯 Join button clicked! Opening modal...');
        console.log('🎯 Modal before:', modal.style.display);
        modal.style.display = 'flex';
        console.log('🎯 Modal after:', modal.style.display);
        document.body.style.overflow = 'hidden';
        
        // Load leagues from seed data
        loadLeagues();
    });
    
    // Close button
    const closeButton = document.getElementById('browseModalClose');
    if (closeButton) {
        closeButton.addEventListener('click', function() {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        });
    }
    
    // Close when clicking outside
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }
    });
    
    console.log('✅ MINIMAL League Browser v2 ready!');
    
    // Add manual test function
    window.testLeagueModal = function() {
        console.log('🔧 Manual test: Opening modal...');
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        loadLeagues();
        console.log('🔧 Manual test complete');
    };
    
    console.log('💡 Try: testLeagueModal() in console');
});

function loadLeagues() {
    console.log('📊 Loading leagues...');
    const grid = document.getElementById('leaguesGrid');
    if (!grid) return;
    
    // Use seed data if available, otherwise test data
    const leagues = window.SEEDED_LEAGUES || [
        { 
            id: "test_001",
            name: "Test Dynasty League", 
            format: "dynasty", 
            attribute: "testers",
            current_teams: 8,
            team_count: 12,
            description: "A test league for development"
        },
        { 
            id: "test_002",
            name: "Test Fantasy League", 
            format: "fantasy", 
            attribute: "testers",
            current_teams: 10,
            team_count: 12,
            description: "Another test league"
        },
        { 
            id: "test_003",
            name: "Test Casual League", 
            format: "fantasy", 
            attribute: "casual",
            current_teams: 5,
            team_count: 12,
            description: "Casual test league"
        }
    ];
    
    console.log(`📊 Found ${leagues.length} leagues to display`);
    
    grid.innerHTML = '';
    
    leagues.forEach(league => {
        const card = document.createElement('div');
        card.className = 'league-card';
        card.dataset.leagueId = league.id || league.name.toLowerCase().replace(/\s+/g, '-');
        
        // Calculate fill percentage
        const currentTeams = typeof league.current_teams === 'number' ? league.current_teams : 0;
        const totalTeams = typeof league.team_count === 'number' ? league.team_count : 12;
        const fillPercentage = Math.round((currentTeams / totalTeams) * 100);
        
        // Format display
        const formatName = league.format ? league.format.charAt(0).toUpperCase() + league.format.slice(1) : 'Unknown';
        const attributeName = league.attribute ? league.attribute.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) : 'Various';
        
        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                <h4 style="margin: 0; color: #333; font-size: 1.1rem;">${league.name}</h4>
                ${league.recommended ? '<span style="background: #ffd700; color: #000; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.8rem; font-weight: bold;">⭐ Recommended</span>' : ''}
            </div>
            
            <div style="display: flex; gap: 0.5rem; margin-bottom: 0.75rem;">
                <span style="background: #e0e0e0; color: #333; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.8rem;">${formatName}</span>
                <span style="background: #d0e0ff; color: #333; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.8rem;">${attributeName}</span>
            </div>
            
            <div style="margin-bottom: 0.75rem;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                    <span style="color: #666; font-size: 0.9rem;">${currentTeams}/${totalTeams} teams</span>
                    <span style="color: ${fillPercentage > 90 ? '#ff3b30' : fillPercentage > 75 ? '#ff9500' : '#34c759'}; font-size: 0.9rem; font-weight: bold;">
                        ${fillPercentage > 90 ? 'CRITICAL' : fillPercentage > 75 ? 'FILLING FAST' : 'OPEN'}
                    </span>
                </div>
                <div style="background: #e0e0e0; height: 6px; border-radius: 3px; overflow: hidden;">
                    <div style="background: ${fillPercentage > 90 ? '#ff3b30' : fillPercentage > 75 ? '#ff9500' : '#34c759'}; height: 100%; width: ${fillPercentage}%;"></div>
                </div>
            </div>
            
            <div style="color: #666; font-size: 0.9rem; margin-bottom: 1rem; line-height: 1.4;">
                ${league.description || 'Join this league to compete with other bots!'}
            </div>
            
            <button class="join-league-btn" data-league-id="${card.dataset.leagueId}" style="width: 100%; background: #00cc6a; color: white; border: none; padding: 0.75rem; border-radius: 6px; cursor: pointer; font-weight: bold; transition: background 0.2s;">
                Join League
            </button>
        `;
        
        // Add click handler to join button
        const joinBtn = card.querySelector('.join-league-btn');
        if (joinBtn) {
            joinBtn.addEventListener('click', function() {
                handleJoinLeague(card.dataset.leagueId, league.name);
            });
        }
        
        grid.appendChild(card);
    });
    
    console.log('✅ Leagues loaded');
}

function handleJoinLeague(leagueId, leagueName) {
    console.log(`🎯 Joining league: ${leagueName} (${leagueId})`);
    
    // Store in LocalStorage
    const myLeagues = JSON.parse(localStorage.getItem('myLeagues') || '[]');
    if (!myLeagues.find(l => l.id === leagueId)) {
        myLeagues.push({
            id: leagueId,
            name: leagueName,
            joinedAt: new Date().toISOString(),
            teamName: `Roger's ${leagueName.split(' ')[0]} Team`
        });
        localStorage.setItem('myLeagues', JSON.stringify(myLeagues));
        console.log('✅ League joined, saved to LocalStorage');
        
        // Show success message
        alert(`🎉 Successfully joined "${leagueName}"! You can now access your team dashboard.`);
        
        // Close modal
        const modal = document.getElementById('browseLeaguesModal');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }
        
        // Update UI to show joined status
        updateJoinedLeaguesUI();
    } else {
        console.log('⚠️ Already joined this league');
        alert(`You've already joined "${leagueName}"!`);
    }
}

function updateJoinedLeaguesUI() {
    const myLeagues = JSON.parse(localStorage.getItem('myLeagues') || '[]');
    console.log(`📋 You have joined ${myLeagues.length} leagues:`, myLeagues);
    
    // Update dashboard if elements exist
    const joinedCountEl = document.getElementById('joinedLeaguesCount');
    if (joinedCountEl) {
        joinedCountEl.textContent = myLeagues.length;
    }
    
    // Show/hide team dashboard link
    const teamDashboardLink = document.getElementById('teamDashboardLink');
    if (teamDashboardLink) {
        if (myLeagues.length > 0) {
            teamDashboardLink.style.display = 'block';
        } else {
            teamDashboardLink.style.display = 'none';
        }
    }
}

// Initialize joined leagues display
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(updateJoinedLeaguesUI, 500);
});

console.log('🎨 MINIMAL v2 script loaded');