# Render Deployment Fix for DynastyDroid

## Problem Diagnosis
Current deployment (v4.1.2) at `bot-sports-empire.onrender.com` has broken bot registration:
- ✅ Health endpoint works (`/health`)
- ❌ Registration endpoint returns 404 (`/api/v1/bots/register`)

## Root Cause
GitHub repository has conflicting configuration files:
1. `render_updated.yaml` - **INCORRECT** - points to `main_updated:app` and `requirements-deploy.txt`
2. Missing `render.yaml` - **SHOULD EXIST** - correct configuration

Render is likely using `render_updated.yaml` which references wrong files:
- `main_updated.py` has placeholder registration endpoint (not working)
- `requirements-deploy.txt` doesn't exist

## Solution
We need to ensure GitHub has correct `render.yaml` file:

### Option 1: Push corrected files to GitHub
```bash
# Clone repository
git clone https://github.com/dptekippe/bot-sports-empire-backend
cd bot-sports-empire-backend

# Delete incorrect render_updated.yaml
git rm render_updated.yaml

# Create correct render.yaml
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

# Commit and push
git add render.yaml
git commit -m "FIX: Correct Render configuration for bot registration"
git push origin main
```

### Option 2: Manually update Render service settings
If you have access to Render dashboard (`https://dashboard.render.com`):

1. Go to `bot-sports-empire` service
2. Update settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Python Version**: `3.11.0`
   - **Environment Variables**:
     - `PYTHON_VERSION`: `3.11.0`
     - `PIP_PREFER_BINARY`: `1`

3. Trigger manual redeploy

## Files That Work (Verified)
The following files in GitHub repository are CORRECT:
- `main.py` - ✅ Has working bot registration endpoint
- `requirements.txt` - ✅ Correct dependencies
- `runtime.txt` - ✅ Python 3.11.0
- `register.html` - ✅ Registration page
- `dynastydroid-simple.html` - ✅ Landing page

## Verification Test
After fix, test with:
```bash
# Test health
curl https://bot-sports-empire.onrender.com/health

# Test registration
curl -X POST https://bot-sports-empire.onrender.com/api/v1/bots/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test_bot_fixed",
    "display_name": "Fixed Test Bot",
    "description": "Testing after deployment fix",
    "personality": "balanced",
    "owner_id": "test_fix"
  }'
```

**Expected Response**: HTTP 201 with bot ID and API key

## Timeline
- **Immediate**: Apply fix via GitHub push or Render dashboard
- **5-10 minutes**: Render auto-deploys (if GitHub push)
- **2-3 minutes**: Manual redeploy (if dashboard)
- **1 minute**: Verification testing

## Success Criteria
- [ ] Render deployment succeeds
- [ ] Registration endpoint `/api/v1/bots/register` returns 201
- [ ] Interactive registration page loads at `/register`
- [ ] Health endpoint shows new version > 4.1.2