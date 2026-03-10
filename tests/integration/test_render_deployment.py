#!/usr/bin/env python3
"""
Test script to verify the app works for Render deployment.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main_simple import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Bot Sports Empire" in data["message"]
    print("✅ Root endpoint works")

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("✅ Health endpoint works")

def test_docs():
    response = client.get("/docs")
    assert response.status_code == 200
    print("✅ Docs endpoint works")

if __name__ == "__main__":
    print("🧪 Testing Render deployment configuration...")
    try:
        test_root()
        test_health()
        test_docs()
        print("\n🎉 All tests passed! Ready for Render deployment.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)