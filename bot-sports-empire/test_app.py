#!/usr/bin/env python3
"""
Test if the FastAPI app can start without errors.
"""
import sys
import os
import subprocess

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

print("🧪 Testing FastAPI app startup...")
print(f"Project directory: {project_dir}")
print(f"Python version: {sys.version}")

try:
    # Try to import the app
    from app.main_simple import app
    print("✅ Successfully imported app")
    
    # Try to create a test client
    from fastapi.testclient import TestClient
    client = TestClient(app)
    print("✅ Created TestClient")
    
    # Test root endpoint
    response = client.get("/")
    print(f"✅ Root endpoint: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Test health endpoint
    response = client.get("/health")
    print(f"✅ Health endpoint: {response.status_code}")
    print(f"Response: {response.json()}")
    
    print("\n🎉 App appears to be working correctly!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Trying to install missing dependencies...")
    
    # Try to install requirements
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True, text=True)
        print("✅ Installed dependencies")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        print(f"stderr: {e.stderr}")
        
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()