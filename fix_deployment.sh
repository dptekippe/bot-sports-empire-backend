#!/bin/bash
# Fix Render Deployment for DynastyDroid
# This script creates all necessary files to fix the deployment

set -e

echo "========================================="
echo "DynastyDroid Render Deployment Fix"
echo "========================================="

# Create directory for fix files
FIX_DIR="dynastydroid-fix-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$FIX_DIR"
cd "$FIX_DIR"

echo "📁 Created fix directory: $FIX_DIR"

# 1. Create correct render.yaml
echo "📝 Creating render.yaml..."
cat > render.yaml << 'EOF'
services:
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
EOF

# 2. Download the correct main.py from GitHub
echo "⬇️  Downloading main.py from GitHub..."
curl -s -o main.py https://raw.githubusercontent.com/dptekippe/bot-sports-empire-backend/main/main.py

# 3. Download requirements.txt
echo "⬇️  Downloading requirements.txt..."
curl -s -o requirements.txt https://raw.githubusercontent.com/dptekippe/bot-sports-empire-backend/main/requirements.txt

# 4. Download runtime.txt
echo "⬇️  Downloading runtime.txt..."
curl -s -o runtime.txt https://raw.githubusercontent.com/dptekippe/bot-sports-empire-backend/main/runtime.txt

# 5. Download HTML files
echo "⬇️  Downloading HTML files..."
curl -s -o register.html https://raw.githubusercontent.com/dptekippe/bot-sports-empire-backend/main/register.html
curl -s -o dynastydroid-simple.html https://raw.githubusercontent.com/dptekippe/bot-sports-empire-backend/main/dynastydroid-simple.html

# 6. Create verification script
echo "📝 Creating verification script..."
cat > verify_fix.py << 'EOF'
#!/usr/bin/env python3
"""
Verify the deployment fix works
"""
import sys
import os

def verify_files():
    print("Verifying fix files...")
    
    required_files = [
        ('render.yaml', 'services:'),
        ('main.py', 'register_bot'),
        ('requirements.txt', 'fastapi'),
        ('runtime.txt', 'python-3.11.0'),
        ('register.html', '<html'),
        ('dynastydroid-simple.html', '<html')
    ]
    
    all_good = True
    for filename, contains in required_files:
        if not os.path.exists(filename):
            print(f"❌ Missing: {filename}")
            all_good = False
            continue
            
        with open(filename, 'r') as f:
            content = f.read()
            if contains in content:
                print(f"✅ {filename} - OK")
            else:
                print(f"⚠️  {filename} - missing expected content '{contains}'")
    
    return all_good

def check_main_py():
    print("\nChecking main.py...")
    try:
        # Try to import main.py to verify it works
        import importlib.util
        spec = importlib.util.spec_from_file_location("main", "main.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, 'app'):
            app = module.app
            print(f"✅ App loaded: {app.title}")
            
            # Check for registration endpoint
            registration_found = False
            for route in app.routes:
                if hasattr(route, 'path') and '/api/v1/bots/register' in route.path:
                    registration_found = True
                    print(f"✅ Registration endpoint found: {route.path}")
                    break
            
            if not registration_found:
                print("❌ Registration endpoint not found in routes")
                return False
                
            return True
        else:
            print("❌ No app object in main.py")
            return False
            
    except Exception as e:
        print(f"❌ Error loading main.py: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("DynastyDroid Deployment Fix Verification")
    print("=" * 50)
    
    files_ok = verify_files()
    if not files_ok:
        print("\n❌ Missing or incorrect files")
        sys.exit(1)
    
    main_ok = check_main_py()
    
    print("\n" + "=" * 50)
    if files_ok and main_ok:
        print("✅ ALL CHECKS PASSED!")
        print("\nNext steps:")
        print("1. Push these files to GitHub:")
        print("   git add render.yaml")
        print("   git commit -m 'FIX: Correct Render configuration'")
        print("   git push origin main")
        print("\n2. Delete incorrect file:")
        print("   git rm render_updated.yaml")
        print("   git commit -m 'REMOVE: Incorrect render configuration'")
        print("   git push origin main")
        print("\n3. Render will auto-deploy within 5-10 minutes")
    else:
        print("❌ Fix verification failed")
        sys.exit(1)
EOF

chmod +x verify_fix.py

# 7. Create README with instructions
echo "📝 Creating README..."
cat > README.md << 'EOF'
# DynastyDroid Render Deployment Fix

## Problem
Current deployment (v4.1.2) has broken bot registration:
- Registration endpoint `/api/v1/bots/register` returns 404
- Render is using incorrect `render_updated.yaml` configuration

## Root Cause
GitHub repository missing `render.yaml` file. Render uses `render_updated.yaml` which:
- References `main_updated:app` (wrong file)
- References `requirements-deploy.txt` (doesn't exist)

## Solution Files
This directory contains all corrected files:

1. **`render.yaml`** - Correct Render configuration
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Python: `3.11.0`

2. **`main.py`** - Working bot registration (from GitHub)
3. **`requirements.txt`** - Correct dependencies
4. **`runtime.txt`** - Python 3.11.0
5. **HTML files** - Registration and landing pages

## How to Apply Fix

### Option A: Push to GitHub (Recommended)
```bash
# Clone repository
git clone https://github.com/dptekippe/bot-sports-empire-backend
cd bot-sports-empire-backend

# Remove incorrect file
git rm render_updated.yaml

# Add correct render.yaml (copy from this directory)
cp ../render.yaml .

# Commit and push
git add render.yaml
git commit -m "FIX: Correct Render configuration for bot registration"
git push origin main
```

### Option B: Manual Render Dashboard Update
1. Go to https://dashboard.render.com
2. Select `bot-sports-empire` service
3. Update settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Python Version**: `3.11.0`
4. Add environment variable:
   - Key: `PIP_PREFER_BINARY`, Value: `1`
5. Trigger manual redeploy

## Verification
After fix, test with:
```bash
# Test health
curl https://bot-sports-empire.onrender.com/health

# Test registration
curl -X POST https://bot-sports-empire.onrender.com/api/v1/bots/register \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "test_bot_fixed",
    "display_name": "Fixed Test Bot",
    "description": "Testing after deployment fix",
    "personality": "balanced",
    "owner_id": "test"
  }'
```

**Expected**: HTTP 201 with bot ID and API key

## Timeline
- **GitHub push**: 5-10 minutes for auto-deploy
- **Manual update**: 2-3 minutes for redeploy
- **Verification**: 1 minute

## Support
If issues persist, check Render deployment logs for errors.
EOF

echo "✅ All fix files created in: $FIX_DIR"
echo ""
echo "📋 To apply fix:"
echo "   1. Review files in $FIX_DIR"
echo "   2. Run: ./verify_fix.py"
echo "   3. Follow instructions in README.md"
echo ""
echo "🚀 The fix will restore bot registration functionality!"