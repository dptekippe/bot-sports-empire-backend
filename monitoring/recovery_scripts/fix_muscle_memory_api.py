#!/usr/bin/env python3
"""
Recovery Script: Fix Muscle Memory API Key Issue
Diagnoses and attempts to fix the invalid API key problem.
"""

import os
import json
import subprocess
from pathlib import Path

def check_muscle_memory_status():
    """Check current muscle memory status."""
    print("🔍 Checking Muscle Memory status...")
    
    # Check log file
    log_path = Path("/Users/danieltekippe/.openclaw/muscle-memory/processor.log")
    if not log_path.exists():
        print("❌ Muscle memory log file not found")
        return False
    
    # Read last few lines of log
    try:
        with open(log_path, 'r') as f:
            lines = f.readlines()[-10:]  # Last 10 lines
        
        print(f"📄 Last log entries:")
        for line in lines:
            print(f"  {line.strip()}")
        
        # Check for API errors
        api_errors = [line for line in lines if "401" in line or "Unauthorized" in line or "invalid api key" in line]
        if api_errors:
            print(f"❌ Found API errors: {len(api_errors)}")
            return False
        
        print("✅ No API errors found in recent logs")
        return True
        
    except Exception as e:
        print(f"❌ Error reading log: {e}")
        return False

def test_api_key():
    """Test if the current API key works."""
    print("\n🔑 Testing API key...")
    
    # Read current API key from config
    script_path = Path("/Users/danieltekippe/.openclaw/muscle-memory/processor.py")
    
    try:
        with open(script_path, 'r') as f:
            content = f.read()
        
        # Look for API key in script
        import re
        api_key_match = re.search(r'"minimax_api_key":\s*"([^"]+)"', content)
        
        if api_key_match:
            api_key = api_key_match.group(1)
            masked_key = api_key[:10] + "..." + api_key[-10:] if len(api_key) > 20 else "***"
            print(f"📋 Current API key: {masked_key}")
            
            # Test API key with curl
            test_command = [
                "curl", "-s",
                "-H", "Authorization: Bearer " + api_key,
                "-H", "Content-Type: application/json",
                "-d", '{"model":"abab5.5-chat","messages":[{"role":"user","content":"test"}],"stream":false,"temperature":0.7}',
                "https://api.minimax.io/v1/chat/completions"
            ]
            
            try:
                result = subprocess.run(test_command, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    response = json.loads(result.stdout)
                    if "error" in response:
                        print(f"❌ API key invalid: {response['error'].get('message', 'Unknown error')}")
                        return False
                    else:
                        print("✅ API key appears valid")
                        return True
                else:
                    print(f"❌ API test failed with code {result.returncode}")
                    print(f"   Error: {result.stderr}")
                    return False
                    
            except subprocess.TimeoutExpired:
                print("❌ API test timed out")
                return False
            except json.JSONDecodeError:
                print("❌ Invalid JSON response from API")
                return False
        else:
            print("❌ Could not find API key in script")
            return False
            
    except Exception as e:
        print(f"❌ Error testing API key: {e}")
        return False

def get_new_api_key_from_config():
    """Try to get a valid API key from OpenClaw config."""
    print("\n🔍 Looking for valid API key in OpenClaw config...")
    
    config_path = Path("/Users/danieltekippe/.openclaw/openclaw.json")
    
    if not config_path.exists():
        print("❌ OpenClaw config not found")
        return None
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Look for Minimax API key in auth profiles
        auth_profiles = config.get("auth", {}).get("profiles", {})
        
        for profile_name, profile in auth_profiles.items():
            if profile.get("provider") == "minimax-portal":
                print(f"✅ Found Minimax profile: {profile_name}")
                # Note: API keys might be stored elsewhere or need re-auth
                return "NEEDS_REAUTH"  # Placeholder
        
        print("❌ No Minimax API key found in config")
        return None
        
    except Exception as e:
        print(f"❌ Error reading config: {e}")
        return None

def update_muscle_memory_script(new_api_key):
    """Update the muscle memory script with new API key."""
    print(f"\n✏️ Updating muscle memory script...")
    
    script_path = Path("/Users/danieltekippe/.openclaw/muscle-memory/processor.py")
    
    try:
        with open(script_path, 'r') as f:
            content = f.read()
        
        # Replace API key
        import re
        new_content = re.sub(
            r'"minimax_api_key":\s*"[^"]+"',
            f'"minimax_api_key": "{new_api_key}"',
            content
        )
        
        with open(script_path, 'w') as f:
            f.write(new_content)
        
        print("✅ Script updated")
        return True
        
    except Exception as e:
        print(f"❌ Error updating script: {e}")
        return False

def test_fixed_script():
    """Test if the fixed script works."""
    print("\n🧪 Testing fixed script...")
    
    try:
        # Run muscle memory script in test mode
        test_command = [
            "cd", "/Users/danieltekippe/.openclaw/muscle-memory",
            "&&", "python3", "processor.py"
        ]
        
        result = subprocess.run(
            " ".join(test_command),
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"📋 Test output (last 5 lines):")
        for line in result.stdout.split('\n')[-5:]:
            if line.strip():
                print(f"  {line}")
        
        if result.returncode == 0:
            print("✅ Script runs successfully")
            return True
        else:
            print(f"❌ Script failed with code {result.returncode}")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}...")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Script test timed out")
        return False
    except Exception as e:
        print(f"❌ Error testing script: {e}")
        return False

def create_manual_fix_instructions():
    """Create instructions for manual fix if automated fails."""
    print("\n📋 Manual Fix Instructions:")
    print("=" * 50)
    print("1. Check OpenClaw config for valid Minimax API key:")
    print("   cat ~/.openclaw/openclaw.json | grep -A5 -B5 minimax")
    print()
    print("2. If no valid key, authenticate with:")
    print("   openclaw auth login --provider minimax-portal")
    print()
    print("3. Update muscle memory script:")
    print("   Edit: ~/.openclaw/muscle-memory/processor.py")
    print("   Find: 'minimax_api_key'")
    print("   Replace with valid key")
    print()
    print("4. Test fix:")
    print("   cd ~/.openclaw/muscle-memory && python3 processor.py")
    print("=" * 50)

def main():
    """Main recovery function."""
    print("🛠️ Muscle Memory API Key Recovery")
    print("=" * 50)
    
    # Step 1: Check current status
    status_ok = check_muscle_memory_status()
    
    # Step 2: Test current API key
    api_key_ok = test_api_key()
    
    if api_key_ok and status_ok:
        print("\n✅ Muscle memory appears to be working correctly")
        return 0
    
    # Step 3: Try to get new API key
    print("\n🔄 Attempting to fix API key issue...")
    new_key = get_new_api_key_from_config()
    
    if new_key == "NEEDS_REAUTH":
        print("\n⚠️ API key needs re-authentication")
        print("   Run: openclaw auth login --provider minimax-portal")
        create_manual_fix_instructions()
        return 1
    elif new_key:
        # Step 4: Update script with new key
        if update_muscle_memory_script(new_key):
            # Step 5: Test fixed script
            if test_fixed_script():
                print("\n🎉 Successfully fixed muscle memory API issue!")
                return 0
            else:
                print("\n❌ Script still failing after update")
                create_manual_fix_instructions()
                return 1
        else:
            print("\n❌ Failed to update script")
            create_manual_fix_instructions()
            return 1
    else:
        print("\n❌ Could not find valid API key")
        create_manual_fix_instructions()
        return 1

if __name__ == "__main__":
    exit(main())