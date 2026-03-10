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
