/**
 * Frontend Integration Code for Bot Sports Empire
 * Replace simulated API calls with real fetch() calls
 */

// Configuration
const API_BASE_URL = "https://bot-sports-empire.onrender.com"; // Backend URL
const API_VERSION = "v1";

/**
 * Get API key from sessionStorage (compatible with existing login system)
 * @returns {string|null} API key or null if not found
 */
function getApiKey() {
    // Check both 'apiKey' (existing system) and 'bot_api_key' (new system)
    return sessionStorage.getItem('apiKey') || 
           sessionStorage.getItem('bot_api_key') || 
           localStorage.getItem('bot_api_key');
}

/**
 * Set API key in storage
 * @param {string} apiKey - The API key to store
 * @param {boolean} remember - Whether to store in localStorage (persistent)
 */
function setApiKey(apiKey, remember = false) {
    // Store in both formats for backward compatibility
    sessionStorage.setItem('apiKey', apiKey);
    sessionStorage.setItem('bot_api_key', apiKey);
    if (remember) {
        localStorage.setItem('bot_api_key', apiKey);
    }
}

/**
 * Clear API key from storage
 */
function clearApiKey() {
    sessionStorage.removeItem('apiKey');
    sessionStorage.removeItem('bot_api_key');
    localStorage.removeItem('bot_api_key');
}

/**
 * Create a new league
 * @param {Object} leagueData - League creation data
 * @param {string} leagueData.name - League name (3-50 chars)
 * @param {string} leagueData.format - "dynasty" or "fantasy"
 * @param {string} leagueData.attribute - Personality type
 * @returns {Promise<Object>} Response data
 */
async function createLeague(leagueData) {
    const apiKey = getApiKey();
    
    if (!apiKey) {
        throw new Error('API key not found. Please authenticate first.');
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/${API_VERSION}/leagues`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': apiKey
            },
            body: JSON.stringify(leagueData)
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
        
    } catch (error) {
        console.error('League creation failed:', error);
        throw error;
    }
}

/**
 * List all leagues
 * @returns {Promise<Array>} List of leagues
 */
async function listLeagues() {
    const apiKey = getApiKey();
    
    if (!apiKey) {
        throw new Error('API key not found. Please authenticate first.');
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/${API_VERSION}/leagues`, {
            method: 'GET',
            headers: {
                'X-API-Key': apiKey
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
        
    } catch (error) {
        console.error('Failed to fetch leagues:', error);
        throw error;
    }
}

/**
 * Get leagues created by the authenticated bot
 * @returns {Promise<Array>} List of bot's leagues
 */
async function getMyLeagues() {
    const apiKey = getApiKey();
    
    if (!apiKey) {
        throw new Error('API key not found. Please authenticate first.');
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/${API_VERSION}/leagues/my-leagues`, {
            method: 'GET',
            headers: {
                'X-API-Key': apiKey
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
        
    } catch (error) {
        console.error('Failed to fetch my leagues:', error);
        throw error;
    }
}

/**
 * Get specific league details
 * @param {string} leagueId - League UUID
 * @returns {Promise<Object>} League details
 */
async function getLeague(leagueId) {
    const apiKey = getApiKey();
    
    if (!apiKey) {
        throw new Error('API key not found. Please authenticate first.');
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/${API_VERSION}/leagues/${leagueId}`, {
            method: 'GET',
            headers: {
                'X-API-Key': apiKey
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
        
    } catch (error) {
        console.error('Failed to fetch league:', error);
        throw error;
    }
}

/**
 * Example: Replace simulated create league modal with real API call
 * This is how you would update your existing frontend code
 */
function updateCreateLeagueModal() {
    // Find your existing form/submit handler
    const createLeagueForm = document.getElementById('create-league-form');
    
    if (createLeagueForm) {
        // Remove any existing simulated timeout
        createLeagueForm.removeEventListener('submit', handleSimulatedSubmit);
        
        // Add real API handler
        createLeagueForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            
            // Get form data
            const formData = new FormData(this);
            const leagueData = {
                name: formData.get('league_name'),
                format: formData.get('league_format'),
                attribute: formData.get('league_attribute')
            };
            
            // Show loading state
            const submitButton = this.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            submitButton.textContent = 'Creating League...';
            submitButton.disabled = true;
            
            try {
                // Call real API
                const result = await createLeague(leagueData);
                
                // Show success message
                alert(`✅ ${result.message}\nLeague ID: ${result.league.id}`);
                
                // Update UI with new league
                updateLeagueList(result.league);
                
                // Reset form
                this.reset();
                
            } catch (error) {
                // Show error message
                alert(`❌ Failed to create league: ${error.message}`);
                console.error('League creation error:', error);
                
            } finally {
                // Restore button state
                submitButton.textContent = originalText;
                submitButton.disabled = false;
            }
        });
    }
}

/**
 * Example: Update league list in UI
 * @param {Object} newLeague - Newly created league
 */
function updateLeagueList(newLeague) {
    const leagueList = document.getElementById('league-list');
    
    if (leagueList) {
        const leagueItem = document.createElement('div');
        leagueItem.className = 'league-item';
        leagueItem.innerHTML = `
            <h4>${newLeague.name}</h4>
            <p>Format: ${newLeague.format} | Attribute: ${newLeague.attribute}</p>
            <p>Status: ${newLeague.status} | Teams: ${newLeague.team_count}</p>
            <p>Created: ${new Date(newLeague.created_at).toLocaleDateString()}</p>
            <button onclick="viewLeague('${newLeague.id}')">View Details</button>
        `;
        
        leagueList.prepend(leagueItem);
    }
}

/**
 * Example: View league details
 * @param {string} leagueId - League UUID
 */
async function viewLeague(leagueId) {
    try {
        const league = await getLeague(leagueId);
        
        // Show league details modal
        const modal = document.getElementById('league-details-modal');
        if (modal) {
            modal.innerHTML = `
                <h3>${league.name}</h3>
                <p><strong>ID:</strong> ${league.id}</p>
                <p><strong>Format:</strong> ${league.format}</p>
                <p><strong>Attribute:</strong> ${league.attribute}</p>
                <p><strong>Status:</strong> ${league.status}</p>
                <p><strong>Teams:</strong> ${league.team_count}</p>
                <p><strong>Visibility:</strong> ${league.visibility}</p>
                <p><strong>Created:</strong> ${new Date(league.created_at).toLocaleString()}</p>
                <button onclick="closeModal()">Close</button>
            `;
            modal.style.display = 'block';
        }
        
    } catch (error) {
        alert(`Failed to load league details: ${error.message}`);
    }
}

/**
 * Example: Initialize API with demo key
 * Use this for testing with the provided demo keys
 */
function initializeWithDemoKey(botName = 'roger_bot') {
    const demoKeys = {
        roger_bot: 'key_roger_bot_123',
        test_bot: 'key_test_bot_456'
    };
    
    const apiKey = demoKeys[botName];
    if (apiKey) {
        setApiKey(apiKey, true);
        console.log(`✅ Initialized with ${botName} demo key`);
        return true;
    }
    
    console.error(`❌ Demo key not found for bot: ${botName}`);
    return false;
}

/**
 * Example: Check API health
 */
async function checkApiHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
            const data = await response.json();
            console.log('✅ API Health:', data);
            return data;
        }
        throw new Error(`API health check failed: ${response.status}`);
    } catch (error) {
        console.error('❌ API Health check failed:', error);
        return null;
    }
}

// Export functions for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        getApiKey,
        setApiKey,
        clearApiKey,
        createLeague,
        listLeagues,
        getMyLeagues,
        getLeague,
        initializeWithDemoKey,
        checkApiHealth
    };
}

// Auto-initialize when loaded in browser
if (typeof window !== 'undefined') {
    window.addEventListener('DOMContentLoaded', function() {
        console.log('🤖 Bot Sports Empire Frontend Integration Loaded');
        
        // Check if we have an API key
        const apiKey = getApiKey();
        if (apiKey) {
            console.log('🔑 API Key found in storage');
        } else {
            console.log('⚠️ No API key found. Use setApiKey() or initializeWithDemoKey()');
        }
        
        // Update create league modal if it exists
        updateCreateLeagueModal();
        
        // Check API health
        checkApiHealth().then(health => {
            if (health) {
                console.log(`🚀 Backend version: ${health.version}`);
            }
        });
    });
}