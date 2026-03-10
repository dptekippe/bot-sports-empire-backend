#!/usr/bin/env python3
"""
Simple Matrix Account Creation Test
Phase 1.1: Create accounts with hardcoded passwords for testing
"""

import asyncio
import os
from nio import AsyncClient, LoginResponse

async def create_matrix_account(homeserver: str, username: str, password: str):
    """Create a Matrix account on the given homeserver"""
    client = AsyncClient(homeserver)
    
    print(f"Creating account: {username}@{homeserver}")
    
    try:
        # Try to register the account
        response = await client.register(
            username=username,
            password=password,
            device_name=f"{username}_device"
        )
        
        if isinstance(response, LoginResponse):
            print(f"✅ Account created successfully: {username}")
            print(f"User ID: {response.user_id}")
            print(f"Device ID: {response.device_id}")
            
            # Save minimal credentials
            env_content = f"""MATRIX_USERNAME={username}
MATRIX_PASSWORD={password}
MATRIX_HOMESERVER={homeserver}
MATRIX_USER_ID={response.user_id}
"""
            
            env_file = f"matrix_{username}_env.txt"
            with open(env_file, "w") as f:
                f.write(env_content)
            print(f"✅ Credentials saved to: {env_file}")
            
            return {
                "username": username,
                "user_id": response.user_id,
                "device_id": response.device_id,
                "access_token": response.access_token,
                "homeserver": homeserver
            }
        else:
            print(f"❌ Account creation failed: {response}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating account: {e}")
        return None
    finally:
        await client.close()

async def test_existing_account():
    """Test if we can connect to an existing account"""
    print("\n" + "=" * 60)
    print("Testing Matrix.org connection")
    print("=" * 60)
    
    # Test with a public read-only account
    client = AsyncClient("https://matrix.org")
    
    try:
        # Get server version (doesn't require login)
        version = await client.versions()
        print(f"✅ Connected to Matrix.org")
        print(f"Server version: {version}")
        
        await client.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

async def main():
    """Main test function"""
    print("=" * 60)
    print("Matrix Simple Test - Phase 1.1")
    print("=" * 60)
    
    # Test 1: Basic connection
    print("\nTest 1: Basic Matrix.org connection")
    connection_ok = await test_existing_account()
    
    if not connection_ok:
        print("❌ Cannot proceed - Matrix.org connection failed")
        return
    
    # Test 2: Account creation (commented out for now)
    print("\n" + "=" * 60)
    print("Test 2: Account creation (SKIPPED - requires manual passwords)")
    print("=" * 60)
    
    print("\n⚠️  Account creation requires manual password input.")
    print("For Phase 1 testing, we should:")
    print("1. Manually create accounts via Element web/app")
    print("2. Save credentials to environment variables")
    print("3. Test bot-to-bot communication")
    
    print("\n" + "=" * 60)
    print("Phase 1.1 Recommendations")
    print("=" * 60)
    
    print("""
RECOMMENDED APPROACH:
1. Dan creates accounts manually via Element (web/element.io)
   - white_roger_bot@matrix.org
   - black_roger_bot@matrix.org
   
2. Save credentials to OpenClaw environment:
   MATRIX_WHITE_USERNAME=white_roger_bot
   MATRIX_WHITE_PASSWORD=********
   MATRIX_BLACK_USERNAME=black_roger_bot  
   MATRIX_BLACK_PASSWORD=********
   MATRIX_HOMESERVER=https://matrix.org

3. We then:
   - Create encrypted room "Roger-Janus"
   - Test bot-to-bot message delivery
   - Implement basic message protocol
""")
    
    print("\n" + "=" * 60)
    print("Next Action Required")
    print("=" * 60)
    print("White Roger: Please ask Dan to create Matrix accounts manually")
    print("Then we can proceed with Phase 1.2 and 1.3")

if __name__ == "__main__":
    asyncio.run(main())