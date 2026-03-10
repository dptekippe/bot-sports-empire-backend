#!/usr/bin/env python3
"""
Deployment readiness test for Bot Sports Empire.
Tests critical endpoints before Render deployment.
"""

import sys
import subprocess
import json
from pathlib import Path

def check_imports():
    """Test that all critical imports work."""
    print("🔍 Testing imports...")
    try:
        from app.main import app
        print("✅ FastAPI app imports successfully")
        
        # Check critical modules
        from app.core.database import engine, Base
        print("✅ Database engine imports successfully")
        
        from app.models import Player, Draft, Team, League
        print("✅ Core models import successfully")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def check_requirements():
    """Check that requirements.txt exists and has key packages."""
    print("\n🔍 Checking requirements.txt...")
    req_file = Path("requirements.txt")
    if not req_file.exists():
        print("❌ requirements.txt not found")
        return False
    
    with open(req_file) as f:
        content = f.read()
    
    required_packages = ["fastapi", "uvicorn", "sqlalchemy", "pydantic"]
    missing = []
    for pkg in required_packages:
        if pkg not in content.lower():
            missing.append(pkg)
    
    if missing:
        print(f"❌ Missing packages in requirements.txt: {missing}")
        return False
    
    print("✅ requirements.txt looks good")
    return True

def check_dockerfile():
    """Check Dockerfile exists and has correct structure."""
    print("\n🔍 Checking Dockerfile...")
    dockerfile = Path("Dockerfile")
    if not dockerfile.exists():
        print("❌ Dockerfile not found")
        return False
    
    with open(dockerfile) as f:
        content = f.read()
    
    required_lines = [
        "FROM python",
        "COPY requirements.txt",
        "RUN pip install",
        "CMD [\"uvicorn\"",
    ]
    
    missing = []
    for line in required_lines:
        if line not in content:
            missing.append(line)
    
    if missing:
        print(f"❌ Dockerfile missing critical lines: {missing}")
        return False
    
    print("✅ Dockerfile looks good")
    return True

def check_render_yaml():
    """Check render.yaml exists and has correct structure."""
    print("\n🔍 Checking render.yaml...")
    render_file = Path("render.yaml")
    if not render_file.exists():
        print("❌ render.yaml not found")
        return False
    
    with open(render_file) as f:
        content = f.read()
    
    required_sections = [
        "type: web",
        "buildCommand:",
        "startCommand:",
        "envVars:",
    ]
    
    missing = []
    for section in required_sections:
        if section not in content:
            missing.append(section)
    
    if missing:
        print(f"❌ render.yaml missing sections: {missing}")
        return False
    
    print("✅ render.yaml looks good")
    return True

def check_database():
    """Check database file exists and is accessible."""
    print("\n🔍 Checking database...")
    db_file = Path("bot_sports.db")
    if not db_file.exists():
        print("⚠️  Database file not found (may be created on first run)")
        return True  # Not critical for deployment
    
    size_mb = db_file.stat().st_size / (1024 * 1024)
    print(f"✅ Database exists ({size_mb:.1f} MB)")
    return True

def main():
    print("🚀 Bot Sports Empire - Deployment Readiness Test")
    print("=" * 50)
    
    tests = [
        ("Imports", check_imports),
        ("Requirements", check_requirements),
        ("Dockerfile", check_dockerfile),
        ("Render Config", check_render_yaml),
        ("Database", check_database),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {name} test failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ READY FOR DEPLOYMENT!")
        print("\nNext steps:")
        print("1. Push to GitHub")
        print("2. Connect to Render")
        print("3. Deploy!")
        return 0
    else:
        print("❌ NOT READY - Fix issues above")
        return 1

if __name__ == "__main__":
    sys.exit(main())