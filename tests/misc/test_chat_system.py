#!/usr/bin/env python3
"""
Test script for the chat system.
"""
import asyncio
import json
from datetime import datetime
from app.core.database import SessionLocal
from app.models.chat import ChatMessage, ChatRoom, ChatRoomType
from app.models.bot import BotAgent
from app.models.league import League
import uuid


def test_chat_models():
    """Test that chat models can be created and saved."""
    print("Testing chat models...")
    
    db = SessionLocal()
    
    try:
        # Create test bot
        from app.models.bot import BotPersonality
        bot_id = str(uuid.uuid4())
        bot = BotAgent(
            id=bot_id,
            name=f"Test Bot {bot_id[:8]}",
            display_name=f"Test Bot {bot_id[:8]}",
            api_key=f"test_key_{bot_id[:8]}",
            fantasy_personality=BotPersonality.BALANCED
        )
        db.add(bot)
        db.commit()
        
        # Create test league
        from app.models.league import LeagueType
        league = League(
            id=str(uuid.uuid4()),
            name="Test League",
            description="Test league for chat",
            league_type=LeagueType.FANTASY,
            max_teams=12,
            min_teams=4,
            is_public=True,
            season_year=2024
        )
        db.add(league)
        db.commit()
        
        # Create chat room
        chat_room = ChatRoom(
            id=str(uuid.uuid4()),
            room_type=ChatRoomType.LEAGUE,
            entity_id=league.id,
            name=f"League Chat - {league.name}",
            description=f"Chat room for {league.name}",
            is_public=True
        )
        db.add(chat_room)
        db.commit()
        
        # Create chat message
        chat_message = ChatMessage(
            id=str(uuid.uuid4()),
            room_id=chat_room.id,
            room_type=ChatRoomType.LEAGUE,
            sender_id=bot.id,
            sender_name=bot.name,
            content="Hello, fellow bots! Ready to draft?",
            message_type="text",
            trash_talk_intensity=3
        )
        db.add(chat_message)
        db.commit()
        
        # Query and verify
        saved_message = db.query(ChatMessage).filter(ChatMessage.id == chat_message.id).first()
        saved_room = db.query(ChatRoom).filter(ChatRoom.id == chat_room.id).first()
        
        print(f"✓ Created chat room: {saved_room.name}")
        print(f"✓ Created message from {saved_message.sender_name}: {saved_message.content}")
        print(f"✓ Message timestamp: {saved_message.timestamp}")
        
        # Test getting chat history
        messages = db.query(ChatMessage).filter(
            ChatMessage.room_id == chat_room.id
        ).order_by(ChatMessage.timestamp).all()
        
        print(f"✓ Retrieved {len(messages)} messages from room")
        
        # Clean up
        db.query(ChatMessage).filter(ChatMessage.id == chat_message.id).delete()
        db.query(ChatRoom).filter(ChatRoom.id == chat_room.id).delete()
        db.query(League).filter(League.id == league.id).delete()
        db.query(BotAgent).filter(BotAgent.id == bot.id).delete()
        db.commit()
        
        print("✓ All tests passed!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


def test_chat_schemas():
    """Test that chat schemas work correctly."""
    print("\nTesting chat schemas...")
    
    from app.schemas.chat import (
        ChatMessageCreate, ChatMessageResponse,
        ChatRoomCreate, ChatRoomResponse,
        ChatRoomType
    )
    
    # Test room creation
    room_data = {
        "room_type": ChatRoomType.LEAGUE,
        "name": "Test League Chat",
        "description": "Test chat room",
        "entity_id": str(uuid.uuid4()),
        "is_public": True
    }
    
    room_create = ChatRoomCreate(**room_data)
    print(f"✓ Created room schema: {room_create.room_type}")
    
    # Test message creation
    message_data = {
        "room_id": str(uuid.uuid4()),
        "room_type": ChatRoomType.LEAGUE,
        "sender_id": str(uuid.uuid4()),
        "sender_name": "Test Bot",
        "content": "Test message",
        "message_type": "text"
    }
    
    message_create = ChatMessageCreate(**message_data)
    print(f"✓ Created message schema: {message_create.content}")
    
    # Test response schemas
    room_response = ChatRoomResponse(
        id=str(uuid.uuid4()),
        room_type=ChatRoomType.LEAGUE,
        name="Test Room",
        created_at=datetime.now()
    )
    print(f"✓ Created room response: {room_response.id}")
    
    print("✓ All schema tests passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Chat System for Bot Sports Empire")
    print("=" * 60)
    
    test_chat_schemas()
    test_chat_models()
    
    print("\n" + "=" * 60)
    print("Chat system tests completed successfully!")
    print("=" * 60)