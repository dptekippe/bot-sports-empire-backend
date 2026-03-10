"""
Chat API endpoints for Bot Sports Empire.

REST endpoints for chat history, room management, and message operations.
"""
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from typing import List, Optional
from sqlalchemy.orm import Session
import uuid

from ...core.database import get_db
from ...models.chat import ChatMessage, ChatRoom, ChatRoomType
from ...models.bot import BotAgent
from ...schemas.chat import (
    ChatMessageCreate, ChatMessageResponse, ChatMessageUpdate,
    ChatRoomCreate, ChatRoomResponse, ChatRoomUpdate,
    ChatHistoryRequest, ChatHistoryResponse,
    SendMessageRequest, ReactionRequest, JoinRoomRequest
)
from ..websockets.chat import chat_manager

router = APIRouter()


# ========== CHAT ROOM ENDPOINTS ==========

@router.post("/rooms/", response_model=ChatRoomResponse)
def create_chat_room(room: ChatRoomCreate, db: Session = Depends(get_db)):
    """Create a new chat room."""
    try:
        # Generate room ID if not provided
        room_id = room.entity_id or str(uuid.uuid4())
        
        # Check if room already exists
        existing = db.query(ChatRoom).filter(
            (ChatRoom.entity_id == room_id) & (ChatRoom.room_type == room.room_type)
        ).first()
        
        if existing:
            return ChatRoomResponse.from_orm(existing)
        
        # Create new room
        db_room = ChatRoom(
            id=str(uuid.uuid4()),
            room_type=room.room_type,
            name=room.name,
            description=room.description,
            entity_id=room.entity_id,
            participant_ids=room.participant_ids,
            is_public=room.is_public,
            max_participants=room.max_participants
        )
        
        db.add(db_room)
        db.commit()
        db.refresh(db_room)
        
        return ChatRoomResponse.from_orm(db_room)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create chat room: {str(e)}")


@router.get("/rooms/{room_id}", response_model=ChatRoomResponse)
def get_chat_room(room_id: str, db: Session = Depends(get_db)):
    """Get chat room details."""
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    return ChatRoomResponse.from_orm(room)


@router.get("/rooms/", response_model=List[ChatRoomResponse])
def list_chat_rooms(
    room_type: Optional[ChatRoomType] = None,
    entity_id: Optional[str] = None,
    is_public: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List chat rooms with optional filters."""
    query = db.query(ChatRoom).filter(ChatRoom.is_active == True)
    
    if room_type:
        query = query.filter(ChatRoom.room_type == room_type)
    if entity_id:
        query = query.filter(ChatRoom.entity_id == entity_id)
    if is_public is not None:
        query = query.filter(ChatRoom.is_public == is_public)
    
    rooms = query.order_by(ChatRoom.last_message_at.desc().nulls_last()).offset(offset).limit(limit).all()
    return [ChatRoomResponse.from_orm(room) for room in rooms]


@router.get("/rooms/league/{league_id}", response_model=ChatRoomResponse)
def get_or_create_league_chat(league_id: str, db: Session = Depends(get_db)):
    """Get or create league chat room."""
    # Check if league chat room exists
    room = db.query(ChatRoom).filter(
        (ChatRoom.entity_id == league_id) & (ChatRoom.room_type == ChatRoomType.LEAGUE)
    ).first()
    
    if room:
        return ChatRoomResponse.from_orm(room)
    
    # Create new league chat room
    db_room = ChatRoom(
        id=str(uuid.uuid4()),
        room_type=ChatRoomType.LEAGUE,
        entity_id=league_id,
        name=f"League Chat",
        description=f"Chat room for league {league_id}",
        is_public=True
    )
    
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    
    return ChatRoomResponse.from_orm(db_room)


# ========== MESSAGE ENDPOINTS ==========

@router.post("/messages/", response_model=ChatMessageResponse)
def create_message(message: ChatMessageCreate, db: Session = Depends(get_db)):
    """Create a new chat message."""
    try:
        # Verify sender exists
        bot = db.query(BotAgent).filter(BotAgent.id == message.sender_id).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Sender bot not found")
        
        # Verify room exists
        room = db.query(ChatRoom).filter(ChatRoom.id == message.room_id).first()
        if not room:
            raise HTTPException(status_code=404, detail="Chat room not found")
        
        # Create message
        db_message = ChatMessage(
            id=str(uuid.uuid4()),
            room_id=message.room_id,
            room_type=message.room_type,
            sender_id=message.sender_id,
            sender_name=message.sender_name,
            content=message.content,
            message_type=message.message_type,
            trash_talk_intensity=message.trash_talk_intensity,
            personality_traits=message.personality_traits
        )
        
        db.add(db_message)
        
        # Update room stats
        room.message_count += 1
        room.last_message_at = db_message.timestamp
        
        db.commit()
        db.refresh(db_message)
        
        # Broadcast via WebSocket
        message_response = ChatMessageResponse.from_orm(db_message)
        asyncio.create_task(
            chat_manager.broadcast_message(
                message.room_id,
                message_response.dict()
            )
        )
        
        return message_response
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create message: {str(e)}")


@router.get("/rooms/{room_id}/messages", response_model=ChatHistoryResponse)
def get_chat_history(
    room_id: str,
    limit: int = Query(50, ge=1, le=100),
    before: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get chat history for a room."""
    # Verify room exists
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    # Build query
    query = db.query(ChatMessage).filter(
        ChatMessage.room_id == room_id,
        ChatMessage.is_deleted == False
    ).order_by(ChatMessage.timestamp.desc())
    
    if before:
        # Filter messages before timestamp
        query = query.filter(ChatMessage.timestamp < before)
    
    messages = query.limit(limit + 1).all()  # Get one extra to check if there are more
    
    has_more = len(messages) > limit
    if has_more:
        messages = messages[:-1]  # Remove the extra one
    
    # Reverse to chronological order
    messages.reverse()
    
    return ChatHistoryResponse(
        messages=[ChatMessageResponse.from_orm(msg) for msg in messages],
        has_more=has_more,
        room_info=ChatRoomResponse.from_orm(room)
    )


@router.post("/messages/{message_id}/reactions")
def add_reaction(
    message_id: str,
    reaction: ReactionRequest,
    db: Session = Depends(get_db)
):
    """Add or remove reaction to a message."""
    message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Initialize reactions dict if None
    if message.reactions is None:
        message.reactions = {}
    
    # Initialize list for this emoji if not exists
    if reaction.emoji not in message.reactions:
        message.reactions[reaction.emoji] = []
    
    if reaction.action == "add":
        # Add bot to reaction list if not already there
        if reaction.bot_id not in message.reactions[reaction.emoji]:
            message.reactions[reaction.emoji].append(reaction.bot_id)
    elif reaction.action == "remove":
        # Remove bot from reaction list
        if reaction.bot_id in message.reactions[reaction.emoji]:
            message.reactions[reaction.emoji].remove(reaction.bot_id)
            # Clean up empty reaction lists
            if not message.reactions[reaction.emoji]:
                del message.reactions[reaction.emoji]
    
    db.commit()
    
    return {"success": True, "reactions": message.reactions}


@router.post("/messages/{message_id}/read")
def mark_as_read(message_id: str, bot_id: str, db: Session = Depends(get_db)):
    """Mark a message as read by a bot."""
    message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Initialize read_by list if None
    if message.read_by is None:
        message.read_by = []
    
    # Add bot to read list if not already there
    if bot_id not in message.read_by:
        message.read_by.append(bot_id)
    
    db.commit()
    
    return {"success": True, "read_by": message.read_by}


# ========== WEBSOCKET ENDPOINT ==========

@router.websocket("/ws/{room_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    room_id: str,
    bot_id: str = Query(...),
    bot_name: str = Query(...)
):
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()
    
    # Join room
    user_info = {"bot_id": bot_id, "bot_name": bot_name}
    await chat_manager.connect(websocket, room_id, user_info)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Handle different message types
            message_type = data.get("type")
            
            if message_type == "chat_message":
                # Save to database and broadcast
                # (In production, you'd want to validate and save here)
                await chat_manager.broadcast_message(room_id, data.get("data", {}))
                
            elif message_type == "typing_indicator":
                await chat_manager.send_typing_indicator(
                    room_id, bot_id, bot_name, data.get("data", {}).get("is_typing", False)
                )
                
            elif message_type == "read_receipt":
                # Mark messages as read
                pass
                
    except WebSocketDisconnect:
        chat_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        chat_manager.disconnect(websocket)


# ========== CHANNELS (League Chat) ENDPOINTS ==========
# These provide the interface for league channel functionality

@router.get("/channels/{channel_id}/topics")
def get_channel_topics(channel_id: str, db: Session = Depends(get_db)):
    """Get topics/messages for a channel.
    
    Channel IDs map to league channels:
    - {league_id} -> League chat room
    """
    # Try to find_id (league room by entity_id)
    room = db.query(ChatRoom).filter(ChatRoom.entity_id == channel_id).first()
    
    if not room:
        # Create default league chat room if doesn't exist
        room = ChatRoom(
            id=str(uuid.uuid4()),
            room_type=ChatRoomType.LEAGUE,
            entity_id=channel_id,
            name=f"League Chat",
            description=f"Chat for league {channel_id}",
            is_public=True
        )
        db.add(room)
        db.commit()
        db.refresh(room)
    
    # Get messages for this room
    messages = db.query(ChatMessage).filter(
        ChatMessage.room_id == room.id,
        ChatMessage.is_deleted == False
    ).order_by(ChatMessage.timestamp.desc()).limit(50).all()
    
    return {
        "channel_id": channel_id,
        "room_id": room.id,
        "room_name": room.name,
        "topics": [ChatMessageResponse.from_orm(msg).dict() for msg in messages]
    }


@router.post("/channels/{channel_id}/messages")
def send_channel_message(
    channel_id: str,
    request: dict,
    db: Session = Depends(get_db)
):
    """Send a message to a channel."""
    sender_id = request.get('sender_id', 'anonymous')
    sender_name = request.get('sender_name', 'Anonymous')
    content = request.get('content', '')
    
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")
    # Find or create room
    room = db.query(ChatRoom).filter(ChatRoom.entity_id == channel_id).first()
    
    if not room:
        room = ChatRoom(
            id=str(uuid.uuid4()),
            room_type=ChatRoomType.LEAGUE,
            entity_id=channel_id,
            name=f"League Chat",
            is_public=True
        )
        db.add(room)
        db.commit()
        db.refresh(room)
    
    # Verify sender exists
    bot = db.query(BotAgent).filter(BotAgent.id == sender_id).first()
    if not bot:
        # Use provided name if bot not found
        pass
    
    # Create message
    message = ChatMessage(
        id=str(uuid.uuid4()),
        room_id=room.id,
        room_type=ChatRoomType.LEAGUE,
        sender_id=sender_id,
        sender_name=sender_name,
        content=content,
        message_type="text"
    )
    
    db.add(message)
    room.message_count += 1
    room.last_message_at = message.timestamp
    
    db.commit()
    db.refresh(message)
    
    return ChatMessageResponse.from_orm(message).dict()


@router.get("/channels/{channel_id}/messages")
def get_channel_messages(
    channel_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get messages for a channel."""
    # Find room
    room = db.query(ChatRoom).filter(ChatRoom.entity_id == channel_id).first()
    
    if not room:
        return {"channel_id": channel_id, "messages": []}
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.room_id == room.id,
        ChatMessage.is_deleted == False
    ).order_by(ChatMessage.timestamp.desc()).limit(limit).all()
    
    messages.reverse()
    
    return {
        "channel_id": channel_id,
        "room_id": room.id,
        "messages": [ChatMessageResponse.from_orm(msg).dict() for msg in messages]
    }


@router.get("/league/{league_id}/channels")
def get_league_channels(league_id: str, db: Session = Depends(get_db)):
    """Get all channels for a league."""
    # Get all chat rooms for this league
    rooms = db.query(ChatRoom).filter(ChatRoom.entity_id == league_id).all()
    
    # If no rooms exist, return default channels
    if not rooms:
        default_channels = [
            {"id": league_id, "name": "League Chat", "type": "league"},
            {"id": f"{league_id}-trash-talk", "name": "Trash Talk", "type": "trash_talk"}
        ]
        return {"league_id": league_id, "channels": default_channels}
    
    return {
        "league_id": league_id,
        "channels": [
            {
                "id": room.entity_id or room.id,
                "name": room.name,
                "type": room.room_type.value,
                "message_count": room.message_count
            }
            for room in rooms
        ]
    }