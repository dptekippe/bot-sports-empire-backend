#!/usr/bin/env python3
"""
Matrix Room Creation Script
Phase 1.2: Create encrypted room "Roger-Janus" for bot-to-bot communication
"""

import asyncio
import os
from nio import AsyncClient, RoomCreateError, RoomCreateResponse

async def create_encrypted_room(client: AsyncClient, room_name: str, user_ids: list):
    """
    Create an encrypted Matrix room and invite specified users
    
    Args:
        client: Authenticated AsyncClient
        room_name: Name of the room to create
        user_ids: List of Matrix user IDs to invite
    
    Returns:
        Room ID if successful, None otherwise
    """
    print(f"Creating encrypted room: '{room_name}'")
    print(f"Inviting users: {user_ids}")
    
    try:
        # Create room with encryption enabled
        response = await client.room_create(
            name=room_name,
            invite=user_ids,
            is_direct=False,
            preset="private_chat",  # Private, invite-only
            initial_state=[
                {
                    "type": "m.room.encryption",
                    "state_key": "",
                    "content": {
                        "algorithm": "m.megolm.v1.aes-sha2"
                    }
                },
                {
                    "type": "m.room.history_visibility",
                    "state_key": "",
                    "content": {
                        "history_visibility": "shared"  # Visible to all members
                    }
                }
            ]
        )
        
        if isinstance(response, RoomCreateResponse):
            room_id = response.room_id
            print(f"✅ Room created successfully: {room_id}")
            
            # Send welcome message
            welcome_text = f"Roger-Janus collaboration room created. Members: {', '.join(user_ids)}"
            await client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": welcome_text
                }
            )
            print(f"✅ Welcome message sent")
            
            return room_id
        else:
            print(f"❌ Room creation failed: {response}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating room: {e}")
        return None

async def test_room_functionality(client: AsyncClient, room_id: str):
    """
    Test basic room functionality
    
    Args:
        client: Authenticated AsyncClient
        room_id: Room ID to test
    """
    print(f"\nTesting room functionality: {room_id}")
    
    try:
        # Get room info
        room_info = await client.room_get_state(room_id)
        print(f"✅ Room state retrieved")
        
        # Check encryption status
        encryption_events = [e for e in room_info.events if e.get('type') == 'm.room.encryption']
        if encryption_events:
            print(f"✅ Room is encrypted: {encryption_events[0].get('content', {})}")
        else:
            print("⚠️  Room may not be encrypted")
        
        # Send test message
        test_msg = "Test message from room creator"
        await client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content={
                "msgtype": "m.text",
                "body": test_msg
            }
        )
        print(f"✅ Test message sent: '{test_msg}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Room test failed: {e}")
        return False

async def main():
    """
    Main function to create Roger-Janus room
    """
    print("=" * 60)
    print("Matrix Room Creator - Phase 1.2")
    print("=" * 60)
    
    # Configuration (will be replaced with environment variables)
    config = {
        "homeserver": "https://matrix.org",
        "username": "white_roger_bot",  # Will be set via env
        "password": "TestPass123!",     # Will be set via env
        "room_name": "Roger-Janus",
        "user_ids": [
            "@white_roger_bot:matrix.org",
            "@black_roger_bot:matrix.org"
        ]
    }
    
    print(f"Homeserver: {config['homeserver']}")
    print(f"Username: {config['username']}")
    print(f"Room name: {config['room_name']}")
    print(f"User IDs: {config['user_ids']}")
    
    print("\n" + "=" * 60)
    print("Note: This script requires Matrix credentials")
    print("Will be executed when Dan provides credentials")
    print("=" * 60)
    
    # Example workflow (commented out until credentials available)
    """
    # Create client and login
    client = AsyncClient(config['homeserver'])
    await client.login(config['password'], config['username'])
    
    # Create room
    room_id = await create_encrypted_room(
        client, 
        config['room_name'], 
        config['user_ids']
    )
    
    if room_id:
        # Test room functionality
        await test_room_functionality(client, room_id)
    
    await client.close()
    """
    
    print("\n" + "=" * 60)
    print("Ready for execution when credentials available")
    print("=" * 60)
    
    print("""
Execution steps when credentials ready:
1. Set environment variables:
   export MATRIX_USERNAME=white_roger_bot
   export MATRIX_PASSWORD=********
   export MATRIX_HOMESERVER=https://matrix.org

2. Update user_ids in script with actual Matrix IDs

3. Run: python3 matrix_room_creator.py
""")

if __name__ == "__main__":
    asyncio.run(main())