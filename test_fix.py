#!/usr/bin/env python3
"""
Test script to verify the deployment fix works
"""
import os
import sys
import tempfile
import subprocess
import json

def test_main_py():
    """Test that main.py from GitHub works"""
    print("Testing main.py from GitHub...")
    
    # Create a test directory
    with tempfile.TemporaryDirectory() as tmpdir:
        # Download main.py from GitHub
        import urllib.request
        urllib.request.urlretrieve(
            "https://raw.githubusercontent.com/dptekippe/bot-sports-empire-backend/main/main.py",
            os.path.join(tmpdir, "main.py")
        )
        
        # Download requirements.txt
        urllib.request.urlretrieve(
            "https://raw.githubusercontent.com/dptekippe/bot-sports-empire-backend/main/requirements.txt",
            os.path.join(tmpdir, "requirements.txt")
        )
        
        # Download runtime.txt
        urllib.request.urlretrieve(
            "https://raw.githubusercontent.com/dptekippe/bot-sports-empire-backend/main/runtime.txt",
            os.path.join(tmpdir, "runtime.txt")
        )
        
        print(f"✅ Downloaded files to {tmpdir}")
        
        # Check main.py content
        with open(os.path.join(tmpdir, "main.py"), "r") as f:
            content = f.read()
            if "register_bot" in content and "BotRegistrationRequest" in content:
                print("✅ main.py contains bot registration endpoint")
            else:
                print("❌ main.py missing bot registration")
                return False
        
        # Check requirements.txt
        with open(os.path.join(tmpdir, "requirements.txt"), "r") as f:
            reqs = f.read()
            if "fastapi" in reqs and "sqlalchemy" in reqs:
                print("✅ requirements.txt looks correct")
            else:
                print("❌ requirements.txt missing key dependencies")
                return False
        
        # Check runtime.txt
        with open(os.path.join(tmpdir, "runtime.txt"), "r") as f:
            runtime = f.read().strip()
            if "python-3.11.0" in runtime:
                print(f"✅ runtime.txt specifies Python {runtime}")
            else:
                print(f"❌ runtime.txt has wrong Python version: {runtime}")
                return False
        
        return True

def create_fixed_render_yaml():
    """Create a fixed render.yaml file"""
    render_yaml = """services:
  - type: web
    name: bot-sports-empire
    env: python
    region: oregon
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    autoDeploy: true
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: PIP_PREFER_BINARY
        value: "1"
"""
    
    with open("render_fixed.yaml", "w") as f:
        f.write(render_yaml)
    
    print("✅ Created render_fixed.yaml")
    return render_yaml

def check_current_deployment():
    """Check current deployment status"""
    print("\nChecking current deployment...")
    
    # Try to access health endpoint
    import requests
    try:
        response = requests.get("https://bot-sports-empire.onrender.com/health", timeout=5)
        print(f"✅ Health endpoint: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ Cannot reach health endpoint: {e}")
    
    # Try registration endpoint
    try:
        response = requests.post(
            "https://bot-sports-empire.onrender.com/api/v1/bots/register",
            json={
                "name": "test_bot",
                "display_name": "Test Bot",
                "description": "Test",
                "personality": "balanced",
                "owner_id": "test"
            },
            timeout=5
        )
        print(f"Registration endpoint: {response.status_code}")
        if response.status_code != 201:
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Registration endpoint error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("DynastyDroid Render Deployment Fix Diagnostic")
    print("=" * 60)
    
    # Test GitHub files
    if test_main_py():
        print("\n✅ GitHub repository has correct files")
    else:
        print("\n❌ GitHub repository has issues")
    
    # Create fixed render.yaml
    create_fixed_render_yaml()
    
    # Check current deployment
    check_current_deployment()
    
    print("\n" + "=" * 60)
    print("RECOMMENDED FIX:")
    print("1. Delete render_updated.yaml from GitHub repository")
    print("2. Rename render_fixed.yaml to render.yaml and push to GitHub")
    print("3. OR manually update Render service settings:")
    print("   - Build Command: pip install -r requirements.txt")
    print("   - Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT")
    print("   - Python Version: 3.11.0")
    print("=" * 60)