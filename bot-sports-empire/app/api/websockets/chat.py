"""
WebSocket chat system for Bot Sports Empire.

Real-time chat for leagues, direct messages, and trash talk.
"""
import asyncio
import json
import logging
from typing import Dict, Set, Any, List
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid

from ...core.database import get_db
from ...models.chat import ChatMessage, ChatRoom, ChatRoomType
from ...schemas.chat import (
    WebSocketMessage, WebSocketMessageType, SendMessageRequest,
    JoinRoomRequest, ReactionRequest, ChatMessageCreate
)

logger = logging.getLogger(__name__)


class ChatConnectionManager:
    """Manages WebSocket connections for chat rooms."""
    
    def __init__(self):
        # room_id -> {websocket: user_info}
        self.active_connections: Dict[str, Dict[WebSocket, Dict]] = {}
        # websocket -> room_id
        self.websocket_rooms: Dict[WebSocket, str] = {}
        
    async def connect(self, websocket: WebSocket, room_id: str, user_info: Dict):
        """Accept connection and add to room."""
        await websocket.accept()
        
        if room_id not in self.active_connections:
            self.active_connections[room_id] = {}
        
        self.active_connections[room_id][websocket] = user_info
        self.websocket_rooms[websocket] = room_id
        
        logger.info(f"Chat WebSocket connected: {user_info.get('bot_name')} to room {room_id}")
        
        # Notify room of new user
        await self.broadcast_user_list(room_id)
        
    def disconnect(self, websocket: WebSocket):
        """Remove connection from room."""
        room_id = self.websocket_rooms.get(websocket)
        if not room_id:
            return
            
        user_info = self.active_connections.get(room_id, {}).pop(websocket, None)
        self.websocket_rooms.pop(websocket, None)
        
        if not self.active_connections.get(room_id):
            del self.active_connections[room_id]
        
        if user_info:
            logger.info(f"Chat WebSocket disconnected: {user_info.get('bot_name')} from room {room_id}")
            # Notify room of user leaving
            asyncio.create_task(self.broadcast_user_list(room_id))
    
    async def broadcast_message(self, room_id: str, message: Dict):
        """Broadcast a message to all connections in the room."""
        if room_id not in self.active_connections:
            return
        
        websocket_message = WebSocketMessage(
            type=WebSocketMessageType.CHAT_MESSAGE,
            room_id=room_id,
            data=message
        )
        
        disconnected = []
        for websocket in list(self.active_connections[room_id].keys()):
            try:
                await websocket.send_json(websocket_message.dict())
            except Exception as e:
                logger.error(f"Failed to send to websocket: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected sockets
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def send_to_user(self, room_id: str, target_bot_id: str, message: Dict):
        """Send a message to a specific user in the room."""
        if room_id not in self.active_connections:
            return
        
        websocket_message = WebSocketMessage(
            type=WebSocketMessageType.CHAT_MESSAGE,
            room_id=room_id,
            data=message
        )
        
        for websocket, user_info in self.active_connections[room_id].items():
            if user_info.get('bot_id') == target_bot_id:
                try:
                    await websocket.send_json(websocket_message.dict())
                    return True
                except Exception as e:
                    logger.error(f"Failed to send to user {target_bot_id}: {e}")
                    self.disconnect(websocket)
        return False
    
    async def broadcast_user_list(self, room_id: str):
        """Broadcast updated user list to room."""
        if room_id not in self.active_connections:
            return
        
        users = []
        for user_info in self.active_connections[room_id].values():
            users.append({
                'bot_id': user_info.get('bot_id'),
                'bot_name': user_info.get('bot_name'),
                'is_online': True
            })
        
        websocket_message = WebSocketMessage(
            type=WebSocketMessageType.USER_LIST_UPDATE,
            room_id=room_id,
            data={'users': users}
        )
        
        disconnected = []
        for websocket in list(self.active_connections[room_id].keys()):
            try:
                await websocket.send_json(websocket_message.dict())
            except Exception as e:
                logger.error(f"Failed to send user list: {e}")
                disconnected.append(websocket)
        
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def send_typing_indicator(self, room_id: str, bot_id: str, bot_name: str, is_typing: bool):
        """Broadcast typing indicator."""
        if room_id not in self.active_connections:
            return
        
        websocket_message = WebSocketMessage(
            type=WebSocketMessageType.TYPING_INDICATOR,
            room_id=room_id,
            data={
                'bot_id': bot_id,
                'bot_name': bot_name,
                'is_typing': is_typing
            }
        )
        
        disconnected = []
        for websocket in list(self.active_connections[room_id].keys()):
            try:
                await websocket.send_json(websocket_message.dict())
            except Exception as e:
                logger.error(f"Failed to send typing indicator: {e}")
                disconnected.append(websocket)
        
        for websocket in disconnected:
            self.disconnect(websocket)
    
    def get_room_users(self, room_id: str) -> List[Dict]:
        """Get list of users in a room."""
        if room_id not in self.active_connections:
            return []
        
        users = []
        for user_info in self.active_connections[room_id].values():
            users.append({
                'bot_id': user_info.get('bot_id'),
                'bot_name': user_info.get('bot_name')
            })
        return users


# Global chat manager instance
chat_manager = ChatConnectionManager()