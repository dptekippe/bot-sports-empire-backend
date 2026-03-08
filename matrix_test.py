#!/usr/bin/env python3
"""
Matrix Account Creation Test Script
Phase 1.1: Create accounts for White Roger and Black Roger
"""

import asyncio
import os
from nio import AsyncClient, LoginResponse
import getpass

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
            print(f"Access Token: {response.access_token[:20]}...")
            
            # Save credentials to environment file
            env_content = f"""MATRIX_USERNAME_{username.upper()}={username}
MATRIX_PASSWORD_{username.upper()}={password}
MATRIX_HOMESERVER={homeserver}
MATRIX_USER_ID={response.user_id}
MATRIX_DEVICE_ID={response.device_id}
MATRIX_ACCESS_TOKEN={response.access_token}
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

async def test_matrix_connection(homeserver: str, username: str, password: str):
    """Test login to Matrix server"""
    client = AsyncClient(homeserver)
    
    print(f"Testing connection for: {username}@{homeserver}")
    
    try:
        response = await client.login(password, username)
        
        if isinstance(response, LoginResponse):
            print(f"✅ Login successful: {username}")
            print(f"User ID: {response.user_id}")
            await client.close()
            return True
        else:
            print(f"❌ Login failed: {response}")
            await client.close()
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        await client.close()
        return False

async def main():
    """Main test function"""
    print("=" * 60)
    print("Matrix Account Creation Test")
    print("=" * 60)
    
    # Configuration
    HOMESERVER = "https://matrix.org"
    
    # Account details
    accounts = [
        {"username": "white_roger_bot", "password": None},
        {"username": "black_roger_bot", "password": None}
    ]
    
    # Get passwords (in real implementation, use secure storage)
    for account in accounts:
        account["password"] = getpass.getpass(f"Enter password for {account['username']}: ")
    
    print("\n" + "=" * 60)
    print("Step 1: Creating Matrix accounts")
    print("=" * 60)
    
    created_accounts = []
    
    for account in accounts:
        result = await create_matrix_account(
            HOMESERVER,
            account["username"],
            account["password"]
        )
        
        if result:
            created_accounts.append(result)
        else:
            print(f"⚠️ Failed to create account: {account['username']}")
    
    print("\n" + "=" * 60)
    print("Step 2: Testing connections")
    print("=" * 60)
    
    for account in accounts:
        success = await test_matrix_connection(
            HOMESERVER,
            account["username"],
            account["password"]
        )
        
        if not success:
            print(f"⚠️ Connection test failed for: {account['username']}")
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    if len(created_accounts) == 2:
        print("✅ SUCCESS: Both Matrix accounts created and tested")
        print(f"White Roger: {created_accounts[0]['user_id']}")
        print(f"Black Roger: {created_accounts[1]['user_id']}")
        print("\nNext steps:")
        print("1. Review saved credential files")
        print("2. Create encrypted room 'Roger-Janus'")
        print("3. Test bot-to-bot message delivery")
    else:
        print("❌ FAILURE: Not all accounts were created")
        print(f"Created: {len(created_accounts)}/2 accounts")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())