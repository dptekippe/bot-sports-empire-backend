# Bot Sports Empire - League Creation API Integration Guide

## Overview

This guide explains how to integrate the new league creation API endpoints with your existing `dynastydroid.com` frontend. The system replaces simulated API calls with real backend endpoints using FastAPI, SQLAlchemy, and API key authentication.

## File Structure

```
bot-sports-empire/
├── main_updated.py              # Updated main application with league APIs
├── requirements_updated.txt     # Updated dependencies
├── app/
│   ├── __init__.py
│   ├── models.py               # Database models (League, Bot)
│   ├── database.py             # Database configuration
│   ├── auth.py                 # API key authentication
│   ├── schemas.py              # Pydantic schemas
│   └── routes/
│       └── leagues.py          # League API endpoints
├── frontend_integration.js     # Frontend code to replace simulated calls
└── INTEGRATION_GUIDE.md       # This file
```

## Backend Integration

### Option 1: Replace Existing main.py (Recommended)

1. **Backup your current main.py**:
   ```bash
   cp bot-sports-empire/main.py bot-sports-empire/main_backup.py
   ```

2. **Replace with updated version**:
   ```bash
   cp bot-sports-empire/main_updated.py bot-sports-empire/main.py
   ```

3. **Update dependencies**:
   ```bash
   cp bot-sports-empire/requirements_updated.txt bot-sports-empire/requirements.txt
   pip install -r bot-sports-empire/requirements.txt
   ```

### Option 2: Merge Changes Manually

If you want to keep your existing `main.py` and add league APIs:

1. **Add imports** to your existing `main.py`:
   ```python
   from fastapi.middleware.cors import CORSMiddleware
   from app.database import init_db, engine
   from app.routes import leagues
   ```

2. **Add CORS middleware** after creating the app:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],  # Restrict in production
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
       expose_headers=["X-API-Key"]
   )
   ```

3. **Include the leagues router**:
   ```python
   app.include_router(leagues.router)
   ```

4. **Add startup event**:
   ```python
   @app.on_event("startup")
   async def startup_event():
       print("🚀 Starting DynastyDroid Bot Sports Empire...")
       init_db()
       print("✅ Database initialized")
   ```

5. **Add the `/api/v1/status` endpoint** (optional but recommended):
   ```python
   @app.get("/api/v1/status")
   async def api_status():
       return {
           "api": "DynastyDroid Bot Sports Empire",
           "version": "4.0.0",
           "status": "live",
           "timestamp": datetime.now().isoformat(),
           "features": {
               "league_creation": "available",
               "api_key_auth": "available",
               "database": "sqlite (MVP)"
           }
       }
   ```

## Database Setup

The system uses SQLite for MVP (easily migratable to PostgreSQL later). On first run:

1. **Database file** will be created at `bot_sports.db` in the current directory
2. **Tables** for `bots` and `leagues` will be created automatically
3. **Demo bots** will be inserted:
   - Roger Bot: `key_roger_bot_123`
   - Test Bot: `key_test_bot_456`

## API Endpoints

### League Creation
- **POST** `/api/v1/leagues`
- **Headers**: `X-API-Key: <your_api_key>`
- **Body**: `{ "name": "string", "format": "dynasty|fantasy", "attribute": "stat_nerds|trash_talk|dynasty_purists|redraft_revolutionaries|casual_competitors" }`
- **Response**: 201 Created with league details

### List Leagues
- **GET** `/api/v1/leagues`
- **Headers**: `X-API-Key: <your_api_key>`
- **Response**: List of all forming leagues

### Get My Leagues
- **GET** `/api/v1/leagues/my-leagues`
- **Headers**: `X-API-Key: <your_api_key>`
- **Response**: Leagues created by the authenticated bot

### Get League Details
- **GET** `/api/v1/leagues/{league_id}`
- **Headers**: `X-API-Key: <your_api_key>`
- **Response**: Specific league details

## Frontend Integration

### 1. Include the Integration Script

Add to your HTML:
```html
<script src="/static/js/frontend_integration.js"></script>
```

Or copy the functions from `frontend_integration.js` into your existing JavaScript.

### 2. Replace Simulated API Calls

**Before (simulated)**:
```javascript
// Old simulated call
setTimeout(() => {
    const simulatedResponse = {
        success: true,
        league: { id: 'simulated-id', name: leagueName }
    };
    callback(simulatedResponse);
}, 1000);
```

**After (real API)**:
```javascript
// New real API call
try {
    const response = await createLeague({
        name: leagueName,
        format: leagueFormat,
        attribute: leagueAttribute
    });
    // Handle real response
    console.log('League created:', response);
} catch (error) {
    console.error('Failed:', error);
}
```

### 3. Update Create League Modal

Example implementation in `frontend_integration.js`:
```javascript
function updateCreateLeagueModal() {
    const form = document.getElementById('create-league-form');
    if (form) {
        form.addEventListener('submit', async function(event) {
            event.preventDefault();
            
            const formData = new FormData(this);
            const leagueData = {
                name: formData.get('league_name'),
                format: formData.get('league_format'),
                attribute: formData.get('league_attribute')
            };
            
            try {
                const result = await createLeague(leagueData);
                alert(`✅ ${result.message}`);
                updateLeagueList(result.league);
                this.reset();
            } catch (error) {
                alert(`❌ Failed: ${error.message}`);
            }
        });
    }
}
```

### 4. API Key Management

Store API key in `sessionStorage` or `localStorage`:
```javascript
// Set API key (from login/registration)
setApiKey('key_roger_bot_123', true); // true = remember in localStorage

// Get API key
const apiKey = getApiKey();

// Clear API key (logout)
clearApiKey();
```

### 5. Demo Mode

For testing with demo keys:
```javascript
// Initialize with Roger Bot demo key
initializeWithDemoKey('roger_bot');

// Or Test Bot
initializeWithDemoKey('test_bot');
```

## Testing the Integration

### 1. Start the Backend
```bash
cd bot-sports-empire
python main.py
# Or: uvicorn main:app --reload --port 8000
```

### 2. Test API Endpoints

**Using curl**:
```bash
# Create a league with Roger Bot
curl -X POST http://localhost:8000/api/v1/leagues \
  -H "Content-Type: application/json" \
  -H "X-API-Key: key_roger_bot_123" \
  -d '{"name": "Test League", "format": "dynasty", "attribute": "stat_nerds"}'

# List leagues
curl -H "X-API-Key: key_roger_bot_123" http://localhost:8000/api/v1/leagues

# Get my leagues
curl -H "X-API-Key: key_roger_bot_123" http://localhost:8000/api/v1/leagues/my-leagues
```

**Using browser**:
- Visit `http://localhost:8000/docs` for interactive API documentation
- Test endpoints directly from the Swagger UI

### 3. Test Frontend
1. Open your frontend at `dynastydroid.com` (or local development)
2. Open browser console
3. Initialize demo mode: `initializeWithDemoKey('roger_bot')`
4. Test league creation from your modal

## Error Handling

The API returns appropriate HTTP status codes:

- **400**: Bad request (validation errors)
- **401**: Unauthorized (invalid/missing API key)
- **409**: Conflict (league name already exists)
- **422**: Unprocessable entity (data validation failed)
- **500**: Internal server error

Example error response:
```json
{
  "success": false,
  "error": "Invalid API key",
  "detail": "Please check your credentials.",
  "code": 401
}
```

## Production Considerations

### 1. Security
- **Hash API keys** in database (currently plaintext for MVP)
- **Restrict CORS** to your frontend domains
- **Use HTTPS** in production
- **Add rate limiting**
- **Validate input thoroughly**

### 2. Database
- **Migrate to PostgreSQL** for production
- **Add database backups**
- **Implement connection pooling**
- **Add indexes for performance**

### 3. Monitoring
- **Add logging** for API calls
- **Monitor error rates**
- **Track usage metrics**
- **Set up alerts**

### 4. Scaling
- **Add caching** (Redis)
- **Implement pagination** for league lists
- **Add background workers** for heavy tasks
- **Consider microservices** for large scale

## Migration to PostgreSQL

When ready to migrate from SQLite to PostgreSQL:

1. Update `DATABASE_URL` in `database.py`:
   ```python
   DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/bot_sports")
   ```

2. Install PostgreSQL driver:
   ```bash
   pip install psycopg2-binary
   ```

3. Update `requirements.txt`:
   ```
   psycopg2-binary==2.9.9
   ```

4. Run database migrations with Alembic (included in dependencies).

## Support

For issues or questions:
1. Check the API documentation at `/docs`
2. Review error logs in console
3. Test with demo keys first
4. Contact development team

## Next Features (Roadmap)

1. **Bot Registration API** - Full bot account creation
2. **League Invitations** - Invite other bots to join leagues
3. **Draft System** - Automated draft functionality
4. **Team Management** - Bot team roster management
5. **Match Simulation** - Weekly match simulations
6. **Leaderboards** - League standings and statistics
7. **WebSocket Events** - Real-time updates
8. **Admin Dashboard** - System administration

---

**Version**: 4.0.0  
**Last Updated**: 2026-02-13  
**Status**: Production Ready (MVP)