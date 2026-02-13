from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

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
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
# app.include_router(players.router, prefix=settings.API_V1_PREFIX)
# app.include_router(bots.router, prefix=settings.API_V1_PREFIX)
app.include_router(leagues.router, prefix=f"{settings.API_V1_PREFIX}/leagues", tags=["leagues"])
app.include_router(drafts.router, prefix=f"{settings.API_V1_PREFIX}/drafts", tags=["drafts"])
app.include_router(players.router, prefix=f"{settings.API_V1_PREFIX}/players", tags=["players"])
app.include_router(bot_ai.router, prefix=f"{settings.API_V1_PREFIX}/bot-ai", tags=["bot-ai"])
app.include_router(internal_adp.router, prefix=f"{settings.API_V1_PREFIX}", tags=["internal-adp"])
app.include_router(draft_analytics.router, prefix=f"{settings.API_V1_PREFIX}/draft-analytics", tags=["draft-analytics"])
# app.include_router(matchups.router, prefix=settings.API_V1_PREFIX)
app.include_router(bot_claim.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)
app.include_router(mood_events.router, prefix=settings.API_V1_PREFIX)
app.include_router(bots.router, prefix=f"{settings.API_V1_PREFIX}/bots", tags=["bots"])
app.include_router(chat.router, prefix=f"{settings.API_V1_PREFIX}/chat", tags=["chat"])


@app.get("/")
async def root():
    return {
        "message": "Welcome to Bot Sports Empire API",
        "version": settings.PROJECT_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
@app.post("/api/v1/import-sample-players")
async def import_sample_players():
    """Temporary endpoint to import sample players for testing."""
    from app.core.database import SessionLocal
    from app.models.player import Player
    
    sample_players = [
        {"player_id": "QB1", "first_name": "Patrick", "last_name": "Mahomes", "full_name": "Patrick Mahomes", "position": "QB", "team": "KC", "external_adp": 1.5},
        {"player_id": "RB1", "first_name": "Christian", "last_name": "McCaffrey", "full_name": "Christian McCaffrey", "position": "RB", "team": "SF", "external_adp": 1.1},
        {"player_id": "WR1", "first_name": "Justin", "last_name": "Jefferson", "full_name": "Justin Jefferson", "position": "WR", "team": "MIN", "external_adp": 1.8},
        {"player_id": "TE1", "first_name": "Travis", "last_name": "Kelce", "full_name": "Travis Kelce", "position": "TE", "team": "KC", "external_adp": 2.8},
    ]
    
    db = SessionLocal()
    try:
        # Clear existing players first
        db.query(Player).delete()
        
        # Add sample players
        for player_data in sample_players:
            player = Player(**player_data)
            db.add(player)
        
        db.commit()
        
        # Count players
        player_count = db.query(Player).count()
        
        return {
            "success": True,
            "message": f"Imported {len(sample_players)} sample players",
            "total_players": player_count,
            "players": [
                {"full_name": p["full_name"], "position": p["position"], "team": p["team"]}
                for p in sample_players
            ]
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
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
