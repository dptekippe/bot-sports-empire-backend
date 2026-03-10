#!/usr/bin/env python3
"""
Test the actual main.py from GitHub locally
"""
import os
import sys
import tempfile
import subprocess
import time
import requests
import json

def test_local_deployment():
    """Test main.py locally to ensure it works"""
    print("Testing local deployment of GitHub main.py...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Working in: {tmpdir}")
        
        # Download files from GitHub
        import urllib.request
        
        files_to_download = [
            ("main.py", "https://raw.githubusercontent.com/dptekippe/bot-sports-empire-backend/main/main.py"),
            ("requirements.txt", "https://raw.githubusercontent.com/dptekippe/bot-sports-empire-backend/main/requirements.txt"),
            ("runtime.txt", "https://raw.githubusercontent.com/dptekippe/bot-sports-empire-backend/main/runtime.txt"),
            ("register.html", "https://raw.githubusercontent.com/dptekippe/bot-sports-empire-backend/main/register.html"),
            ("dynastydroid-simple.html", "https://raw.githubusercontent.com/dptekippe/bot-sports-empire-backend/main/dynastydroid-simple.html"),
        ]
        
        for filename, url in files_to_download:
            try:
                urllib.request.urlretrieve(url, os.path.join(tmpdir, filename))
                print(f"✅ Downloaded {filename}")
            except Exception as e:
                print(f"⚠️  Could not download {filename}: {e}")
        
        # Create a simple waitlist.json file
        with open(os.path.join(tmpdir, "waitlist.json"), "w") as f:
            json.dump([], f)
        
        # Create bot_sports.db file path
        db_path = os.path.join(tmpdir, "bot_sports.db")
        print(f"Database will be at: {db_path}")
        
        # Set environment variables
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{db_path}"
        env["PYTHONPATH"] = tmpdir
        
        # First, check if we can import the module
        print("\nTesting module import...")
        import importlib.util
        spec = importlib.util.spec_from_file_location("main", os.path.join(tmpdir, "main.py"))
        module = importlib.util.module_from_spec(spec)
        
        try:
            spec.loader.exec_module(module)
            print("✅ Module imports successfully")
            
            # Check app attributes
            if hasattr(module, 'app'):
                app = module.app
                print(f"✅ App loaded: {app.title} v{app.version}")
                
                # Check routes
                registration_found = False
                for route in app.routes:
                    if hasattr(route, 'path') and '/api/v1/bots/register' in route.path:
                        registration_found = True
                        print(f"✅ Found registration endpoint: {route.path}")
                        break
                
                if not registration_found:
                    print("❌ Registration endpoint not found in routes")
                    # List all routes
                    print("Available routes:")
                    for route in app.routes:
                        if hasattr(route, 'path'):
                            print(f"  - {route.path}")
            else:
                print("❌ No app object found in module")
                
        except Exception as e:
            print(f"❌ Module import failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Try to run the server in background
        print("\nStarting test server...")
        server_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8765"],
            cwd=tmpdir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Give server time to start
        time.sleep(3)
        
        # Test endpoints
        try:
            # Test health endpoint
            response = requests.get("http://127.0.0.1:8765/health", timeout=5)
            print(f"✅ Health endpoint: {response.status_code}")
            print(f"   Response: {response.json()}")
            
            # Test registration endpoint
            test_data = {
                "name": "test_bot_local",
                "display_name": "Local Test Bot",
                "description": "Testing locally",
                "personality": "balanced",
                "owner_id": "local_test"
            }
            
            response = requests.post(
                "http://127.0.0.1:8765/api/v1/bots/register",
                json=test_data,
                timeout=5
            )
            
            print(f"✅ Registration endpoint: {response.status_code}")
            if response.status_code == 201:
                result = response.json()
                print(f"   Success! Bot ID: {result.get('bot_id')}")
                print(f"   API Key: {result.get('api_key')[:20]}...")
            else:
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
        
        # Kill server
        server_proc.terminate()
        server_proc.wait()
        
        print("\n✅ Local test complete!")

if __name__ == "__main__":
    test_local_deployment()