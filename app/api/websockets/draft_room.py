"""
WebSocket draft room for Bot Sports Empire.

Live updates for draft boards, pick notifications, and chat.
"""
import asyncio
import json
import logging
from typing import Dict, Set, Any
from fastapi import WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models.draft import Draft, DraftPick
from ...schemas.draft import DraftPickResponse

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for draft rooms."""
    
    def __init__(self):
        # draft_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, draft_id: str):
        """Accept connection and add to room."""
        await websocket.accept()
        
        if draft_id not in self.active_connections:
            self.active_connections[draft_id] = set()
        
        self.active_connections[draft_id].add(websocket)
        logger.info(f"WebSocket connected to draft {draft_id}. Total: {len(self.active_connections[draft_id])}")
        
    def disconnect(self, websocket: WebSocket, draft_id: str):
        """Remove connection from room."""
        if draft_id in self.active_connections:
            self.active_connections[draft_id].discard(websocket)
            if not self.active_connections[draft_id]:
                del self.active_connections[draft_id]
            logger.info(f"WebSocket disconnected from draft {draft_id}")
    
    async def broadcast_pick(self, draft_id: str, pick: DraftPickResponse):
        """Broadcast a new pick to all connections in the draft room."""
        if draft_id not in self.active_connections:
            return
        
        message = {
            "type": "pick_made",
            "draft_id": draft_id,
            "pick": pick.dict(),
            "timestamp": pick.pick_end_time.isoformat() if pick.pick_end_time else None
        }
        
        dead_connections = set()
        for connection in self.active_connections[draft_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                dead_connections.add(connection)
        
        # Clean up dead connections
        for connection in dead_connections:
            self.disconnect(connection, draft_id)
    
    async def broadcast_draft_update(self, draft_id: str, update_type: str, data: Dict[str, Any]):
        """Broadcast general draft updates (status changes, timer, etc.)."""
        if draft_id not in self.active_connections:
            return
        
        message = {
            "type": update_type,
            "draft_id": draft_id,
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        dead_connections = set()
        for connection in self.active_connections[draft_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                dead_connections.add(connection)
        
        # Clean up dead connections
        for connection in dead_connections:
            self.disconnect(connection, draft_id)
    
    async def send_personal_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send a message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")


# Global connection manager
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, draft_id: str, db: Session = Depends(get_db)):
    """
    WebSocket endpoint for draft room.
    
    Connects to: /ws/drafts/{draft_id}
    
    Messages:
    - Client can send: {"type": "subscribe"}
    - Server sends: {"type": "pick_made", "pick": {...}}
    - Server sends: {"type": "draft_update", "data": {...}}
    - Server sends: {"type": "chat_message", "user": "...", "text": "..."}
    """
    # Verify draft exists
    draft = db.query(Draft).filter(Draft.id == draft_id).first()
    if not draft:
        await websocket.close(code=1008, reason="Draft not found")
        return
    
    await manager.connect(websocket, draft_id)
    
    try:
        # Send welcome message with current draft state
        welcome_message = {
            "type": "welcome",
            "draft_id": draft_id,
            "draft_name": draft.name,
            "status": draft.status,
            "current_pick": draft.current_pick,
            "current_round": draft.current_round,
            "message": f"Connected to draft: {draft.name}"
        }
        await manager.send_personal_message(websocket, welcome_message)
        
        # Send recent picks if any
        recent_picks = db.query(DraftPick).filter(
            DraftPick.draft_id == draft_id,
            DraftPick.player_id.isnot(None)
        ).order_by(
            DraftPick.pick_end_time.desc()
        ).limit(10).all()
        
        if recent_picks:
            picks_message = {
                "type": "recent_picks",
                "picks": [DraftPickResponse.from_orm(pick).dict() for pick in recent_picks]
            }
            await manager.send_personal_message(websocket, picks_message)
        
        # Keep connection alive and listen for messages
        while True:
            try:
                # Wait for message from client (with timeout)
                data = await asyncio.wait_for(websocket.receive_json(), timeout=300.0)
                
                message_type = data.get("type")
                
                if message_type == "ping":
                    # Respond to ping
                    await manager.send_personal_message(websocket, {"type": "pong"})
                
                elif message_type == "chat":
                    # Broadcast chat message
                    chat_message = {
                        "type": "chat_message",
                        "user": data.get("user", "anonymous"),
                        "text": data.get("text", ""),
                        "timestamp": asyncio.get_event_loop().time()
                    }
                    await manager.broadcast_draft_update(draft_id, "chat_message", chat_message)
                
                elif message_type == "get_state":
                    # Send current draft state
                    state_message = {
                        "type": "draft_state",
                        "draft_id": draft_id,
                        "status": draft.status,
                        "current_pick": draft.current_pick,
                        "current_round": draft.current_round,
                        "time_remaining": draft.time_remaining_seconds,
                        "completed_picks": len(draft.completed_picks),
                        "total_picks": draft.rounds * draft.team_count
                    }
                    await manager.send_personal_message(websocket, state_message)
                
                else:
                    logger.warning(f"Unknown message type from client: {message_type}")
                    
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await manager.send_personal_message(websocket, {"type": "ping"})
                except:
                    break  # Connection is dead
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                break
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket, draft_id)


# Function to broadcast pick (called from pick assignment endpoint)
async def broadcast_pick_made(draft_id: str, pick_response: DraftPickResponse):
    """Broadcast a pick to all connected clients."""
    await manager.broadcast_pick(draft_id, pick_response)


# Function to broadcast draft status change
async def broadcast_draft_status(draft_id: str, new_status: str):
    """Broadcast draft status change."""
    await manager.broadcast_draft_update(draft_id, "status_change", {"status": new_status})


# Function to broadcast timer update
async def broadcast_timer_update(draft_id: str, time_remaining: int):
    """Broadcast timer update."""
    await manager.broadcast_draft_update(draft_id, "timer_update", {"time_remaining": time_remaining})