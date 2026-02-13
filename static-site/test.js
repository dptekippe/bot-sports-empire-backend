// Test JavaScript syntax
 * Frontend Integration Code for Bot Sports Empire
 * Replace simulated API calls with real fetch() calls
 */

const API_BASE_URL = "https://bot-sports-empire.onrender.com"; // Backend URL
const API_VERSION = "v1";

 * Get API key from sessionStorage (compatible with existing login system)
 * @returns {string|null} API key or null if not found
 */
function getApiKey() {
    // Check both 'apiKey' (existing system) and 'bot_api_key' (new system)
    return sessionStorage.getItem('apiKey') || 
           sessionStorage.getItem('bot_api_key') || 
           localStorage.getItem('bot_api_key');
}

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

 * Clear API key from storage
 */
function clearApiKey() {
    sessionStorage.removeItem('apiKey');
    sessionStorage.removeItem('bot_api_key');
    localStorage.removeItem('bot_api_key');
}

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
