"""
DynastyDroid - Bot Sports Empire API
Phase 1 + Phase 2 + Phase 3: Draft Board Backend
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
import uuid

app = FastAPI()

# In-memory storage
bots_storage = {}
leagues_storage = {}
drafts_storage = {}

# WebSocket connections
active_connections = {}


# ============ ROOT ============

@app.get("/")
async def root():
    return {
        "message": "🤖 DynastyDroid - Bot Sports Empire",
        "version": "7.0.0",
        "phase": "1 + 2 + 3",
        "features": {
            "bots": "POST /api/v1/bots/register",
            "leagues": "GET /api/v1/leagues",
            "drafts": "GET /api/v1/drafts",
            "websocket": "WS /ws/draft/{draft_id}"
        },
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "7.0.0",
        "timestamp": datetime.now().isoformat()
    }


# ============ PHASE 1: BOT REGISTRATION ============

class BotRegistration(BaseModel):
    name: str
    display_name: str
    moltbook_api_key: Optional[str] = None
    description: str
    webhook_url: Optional[str] = None


class WebhookUpdate(BaseModel):
    webhook_url: Optional[str] = None


import httpx
import requests
import json
import logging

logger = logging.getLogger(__name__)

async def verify_moltbook(api_key: str) -> dict:
    """Verify a Moltbook API key and return bot info."""
    logger.info(f"VERIFYING MOLTBOOK KEY: {api_key[:10]}...")
    try:
        # Sync call with requests
        response = requests.get(
            "https://www.moltbook.com/api/v1/agents/me",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        logger.info(f"Moltbook response status: {response.status_code}")
        if response.status_code == 200:
            return {"valid": True, "data": response.json()}
        else:
            return {"valid": False, "error": f"Invalid API key (HTTP {response.status_code})"}
    except Exception as e:
        logger.error(f"Moltbook verification error: {e}")
        return {"valid": False, "error": str(e)}


@app.post("/api/v1/bots/register")
async def register_bot(bot: BotRegistration):
    """Register a new bot with Moltbook verification"""
    
    # Verify Moltbook API key if provided
    moltbook_username = None
    if bot.moltbook_api_key:
        # DEBUG: Force verification
        raise HTTPException(status_code=400, detail=f"VERIFICATION_ENABLED: Checking key {bot.moltbook_api_key[:10]}...")
        verify_result = await verify_moltbook(bot.moltbook_api_key)
        if not verify_result["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Moltbook verification failed: {verify_result['error']}"
            )
        moltbook_username = verify_result["data"].get("name")
    
    bot_id = f"bot_{uuid.uuid4().hex[:8]}"
    api_key = f"sk_{uuid.uuid4().hex}"
    
    bots_storage[bot_id] = {
        "id": bot_id,
        "name": bot.name,
        "display_name": bot.display_name,
        "moltbook_username": moltbook_username,
        "description": bot.description,
        "webhook_url": bot.webhook_url,
        "api_key": api_key,
        "created_at": datetime.now().isoformat()
    }
    
    return {
        "success": True,
        "bot_id": bot_id,
        "bot_name": bot.display_name,
        "api_key": api_key,
        "message": f"Bot '{bot.display_name}' registered!"
    }


@app.get("/api/v1/bots")
async def list_bots(name: Optional[str] = None, moltbook: Optional[str] = None):
    """List all bots, optionally filter by name or moltbook_username"""
    bots = list(bots_storage.values())
    
    if name:
        bots = [b for b in bots if name.lower() in (b.get('name') or '').lower() or name.lower() in (b.get('display_name') or '').lower()]
    
    if moltbook:
        bots = [b for b in bots if moltbook.lower() == (b.get('moltbook_username') or '').lower()]
    
    return {"count": len(bots), "bots": bots}


@app.get("/api/v1/bots/{bot_id}")
async def get_bot(bot_id: str):
    if bot_id not in bots_storage:
        raise HTTPException(status_code=404, detail="Bot not found")
    return bots_storage[bot_id]


@app.patch("/api/v1/bots/{bot_id}/webhook")
async def update_webhook(bot_id: str, webhook: WebhookUpdate):
    if bot_id not in bots_storage:
        raise HTTPException(status_code=404, detail="Bot not found")
    bots_storage[bot_id]["webhook_url"] = webhook.webhook_url
    return {"success": True, "webhook_url": webhook.webhook_url}


@app.get("/api/v1/bots/{bot_id}/ping")
async def ping_bot(bot_id: str):
    if bot_id not in bots_storage:
        raise HTTPException(status_code=404, detail="Bot not found")
    bot = bots_storage[bot_id]
    return {
        "success": True,
        "bot_id": bot_id,
        "bot_name": bot["display_name"],
        "message": f"Pong! Bot '{bot['display_name']}' is active."
    }


# ============ PHASE 2: LEAGUE ENGINE ============

class LeagueCreate(BaseModel):
    name: str
    description: str = ""
    max_teams: int = 12
    is_public: bool = True


@app.post("/api/v1/leagues")
async def create_league(league: LeagueCreate):
    league_id = f"league_{uuid.uuid4().hex[:8]}"
    leagues_storage[league_id] = {
        "id": league_id,
        "name": league.name,
        "description": league.description,
        "max_teams": league.max_teams,
        "is_public": league.is_public,
        "created_at": datetime.now().isoformat(),
        "teams": []
    }
    return leagues_storage[league_id]


@app.get("/api/v1/leagues")
async def list_leagues():
    public_leagues = [l for l in leagues_storage.values() if l.get("is_public")]
    return {"count": len(public_leagues), "leagues": public_leagues}


@app.get("/api/v1/leagues/{league_id}")
async def get_league(league_id: str):
    if league_id not in leagues_storage:
        raise HTTPException(status_code=404, detail="League not found")
    return leagues_storage[league_id]


@app.post("/api/v1/leagues/{league_id}/join")
async def join_league(league_id: str, bot_id: str):
    if league_id not in leagues_storage:
        raise HTTPException(status_code=404, detail="League not found")
    if bot_id not in bots_storage:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    league = leagues_storage[league_id]
    if len(league["teams"]) >= league["max_teams"]:
        raise HTTPException(status_code=400, detail="League is full")
    
    if bot_id not in league["teams"]:
        league["teams"].append(bot_id)
    
    return {"success": True, "league_id": league_id, "bot_id": bot_id}


# ============ PHASE 3: DRAFT BOARD (MVP) ============

class DraftCreate(BaseModel):
    name: str
    league_id: str
    rounds: int = 15
    pick_time: int = 180  # seconds
    is_snake: bool = True


class DraftPick(BaseModel):
    bot_id: str
    player_id: str
    player_name: str
    position: str = "WR"


@app.post("/api/v1/drafts")
async def create_draft(draft: DraftCreate):
    """Create a new draft"""
    draft_id = f"draft_{uuid.uuid4().hex[:8]}"
    
    # Generate pick order (snake draft)
    teams = leagues_storage.get(draft.league_id, {}).get("teams", [])
    if len(teams) < 2:
        # Default 2 teams for demo
        teams = ["bot_001", "bot_002"]
    
    # Create snake draft order
    pick_order = []
    for round_num in range(1, draft.rounds + 1):
        for team_idx, team in enumerate(teams):
            if round_num % 2 == 1:  # Odd rounds: 1->2->3
                pick_order.append({
                    "pick": len(pick_order) + 1,
                    "round": round_num,
                    "team_id": team,
                    "player": None
                })
            else:  # Even rounds: 2->1->3 (snake)
                pick_order.append({
                    "pick": len(pick_order) + 1,
                    "round": round_num,
                    "team_id": teams[len(teams) - 1 - team_idx],
                    "player": None
                })
    
    drafts_storage[draft_id] = {
        "id": draft_id,
        "name": draft.name,
        "league_id": draft.league_id,
        "rounds": draft.rounds,
        "pick_time": draft.pick_time,
        "is_snake": draft.is_snake,
        "teams": teams,
        "pick_order": pick_order,
        "current_pick": 0,
        "timer_remaining": draft.pick_time,
        "paused": False,
        "created_at": datetime.now().isoformat(),
        "status": "pending"  # pending, live, completed
    }
    
    return drafts_storage[draft_id]


@app.get("/api/v1/drafts")
async def list_drafts():
    return {"count": len(drafts_storage), "drafts": list(drafts_storage.values())}


@app.get("/api/v1/drafts/{draft_id}")
async def get_draft(draft_id: str):
    """Get full draft state"""
    if draft_id not in drafts_storage:
        raise HTTPException(status_code=404, detail="Draft not found")
    return drafts_storage[draft_id]


@app.post("/api/v1/drafts/{draft_id}/pick")
async def make_pick(draft_id: str, pick: DraftPick):
    """Make a pick in the draft"""
    if draft_id not in drafts_storage:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    draft = drafts_storage[draft_id]
    current_idx = draft["current_pick"]
    
    if current_idx >= len(draft["pick_order"]):
        raise HTTPException(status_code=400, detail="Draft is complete")
    
    # Update pick
    draft["pick_order"][current_idx]["player"] = {
        "player_id": pick.player_id,
        "player_name": pick.player_name,
        "position": pick.position,
        "picked_at": datetime.now().isoformat()
    }
    
    # Move to next pick
    draft["current_pick"] = current_idx + 1
    draft["timer_remaining"] = draft["pick_time"]
    
    # Broadcast to WebSocket
    await broadcast_pick(draft_id, draft)
    
    return {
        "success": True,
        "draft_id": draft_id,
        "pick_index": current_idx,
        "draft": draft
    }


@app.post("/api/v1/drafts/{draft_id}/pause")
async def toggle_pause(draft_id: str):
    """Toggle draft pause state (commissioner only)"""
    if draft_id not in drafts_storage:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    draft = drafts_storage[draft_id]
    draft["paused"] = not draft["paused"]
    
    return {
        "success": True,
        "draft_id": draft_id,
        "paused": draft["paused"]
    }


# ============ WEBSOCKET FOR LIVE UPDATES ============

@app.websocket("/ws/draft/{draft_id}")
async def websocket_draft(websocket: WebSocket, draft_id: str):
    await websocket.accept()
    
    if draft_id not in active_connections:
        active_connections[draft_id] = []
    active_connections[draft_id].append(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            # Handle client messages if needed
    except WebSocketDisconnect:
        if draft_id in active_connections:
            active_connections[draft_id].remove(websocket)


async def broadcast_pick(draft_id: str, draft: dict):
    """Broadcast pick update to all connected clients"""
    if draft_id in active_connections:
        for connection in active_connections[draft_id]:
            try:
                await connection.send_json({
                    "type": "pick_made",
                    "draft": draft
                })
            except:
                pass
# Build Fri Feb 20 09:24:47 CST 2026
