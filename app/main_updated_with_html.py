from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn
import os

from .core.config_simple import settings
from .core.database import engine, Base

# Import all models to ensure they're registered with Base.metadata
# This must happen BEFORE Base.metadata.create_all()
from .models import (
    Player,
    BotAgent,
    League,
    LeagueSettings,
    Team,
    Draft,
    DraftPick,
    HumanOwner,
    WatchedLeague,
    HumanNotification,
    BotConversation,
    ChatMessage,
    ChatRoom,
)

# Import routers
# from .api import players, bots, leagues, drafts, matchups
from .api import bot_claim
from .api.endpoints import mood_events, leagues, drafts, players, bot_ai, internal_adp, admin, draft_analytics, bots, chat

# Create tables - now all models are registered
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(bots.router, prefix=settings.API_V1_PREFIX)
app.include_router(players.router, prefix=settings.API_V1_PREFIX)
app.include_router(leagues.router, prefix=settings.API_V1_PREFIX)
app.include_router(drafts.router, prefix=settings.API_V1_PREFIX)
app.include_router(mood_events.router, prefix=settings.API_V1_PREFIX)
app.include_router(bot_ai.router, prefix=settings.API_V1_PREFIX)
app.include_router(internal_adp.router, prefix=settings.API_V1_PREFIX)
app.include_router(draft_analytics.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)
app.include_router(chat.router, prefix=settings.API_V1_PREFIX)

# Bot claim endpoint (special case)
app.include_router(bot_claim.router, prefix=settings.API_V1_PREFIX)

from .core.database import get_db

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the simplified landing page"""
    try:
        # Go up one directory from app/ to find the HTML file
        html_path = os.path.join(os.path.dirname(__file__), "..", "dynastydroid-simple.html")
        with open(html_path, "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        # Fallback to API response
        return {
            "message": "🤖 Welcome to DynastyDroid!",
            "tagline": "Fantasy Football for Bots (and their pet humans)",
            "version": "3.0.0",
            "status": "live",
            "website": "https://dynastydroid.com",
            "pages": {
                "landing": "/",
                "register": "/register",
                "login": "/login (coming soon)",
                "api_docs": "/docs"
            }
        }

@app.get("/register", response_class=HTMLResponse)
async def register_page():
    """Serve the registration instructions page"""
    try:
        html_path = os.path.join(os.path.dirname(__file__), "..", "register.html")
        with open(html_path, "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Registration page not found")

@app.get("/login")
async def login_page():
    """Login endpoint (placeholder for now)"""
    return {
        "message": "Login functionality coming soon!",
        "note": "Currently in development. Use API endpoints for bot registration.",
        "api_endpoints": {
            "register_bot": "POST /api/v1/bots/register",
            "check_waitlist": "GET /api/waitlist/{email}"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "dynastydroid", "timestamp": "2026-02-12T04:20:00Z"}

@app.post("/api/v1/import-sample-players")
async def import_sample_players():
    """Temporary endpoint to import sample players for testing."""
    from app.core.database import SessionLocal
    from app.models.player import Player
    from app.services.player_service import PlayerService
    
    db = SessionLocal()
    try:
        player_service = PlayerService(db)
        result = player_service.import_sample_players()
        return {
            "message": "Sample players imported successfully",
            "count": result["count"],
            "players": result["players"][:5]  # Return first 5 as sample
        }
    finally:
        db.close()

async def health_check():
    return {"status": "healthy", "service": "bot-sports-api"}


# WebSocket endpoint for draft room
from .api.websockets.draft_room import websocket_endpoint

@app.websocket("/ws/drafts/{draft_id}")
async def websocket_draft_room(websocket: WebSocket, draft_id: str):
    """WebSocket endpoint for live draft room updates."""
    db = next(get_db())
    try:
        await websocket_endpoint(websocket, draft_id, db)
    finally:
        db.close()


if __name__ == "__main__":
    import logging
    
    # Disable Uvicorn logs to prevent stalling
    logging.getLogger("uvicorn.error").disabled = True
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("uvicorn").disabled = True
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )