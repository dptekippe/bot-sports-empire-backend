# 🚀 Bot Sports Empire - Render Deployment Guide

## **📋 PREREQUISITES**
1. GitHub account
2. Render account (free tier)
3. Code ready in `/Volumes/External Corsair SSD /bot-sports-empire/backend/`

## **🔄 STEP 1: GITHUB REPOSITORY**

### **Create Repository:**
1. Go to [github.com/new](https://github.com/new)
2. Repository name: `bot-sports-empire-backend`
3. **IMPORTANT:** Leave ALL checkboxes UNCHECKED:
   - ☐ Add a README file
   - ☐ Add .gitignore  
   - ☐ Choose a license
4. Click "Create repository"

### **Push Code:**
```bash
cd "/Volumes/External Corsair SSD /bot-sports-empire/backend"

# Add remote (replace [username] with your GitHub username)
git remote add origin https://github.com/[username]/bot-sports-empire-backend.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**Expected Output:** Code pushed to GitHub with 5 commits.

## **🌐 STEP 2: RENDER DEPLOYMENT**

### **Connect Render to GitHub:**
1. Go to [render.com](https://render.com)
2. Click "New +" → "Web Service"
3. Connect GitHub account (authorize access)
4. Select repository: `bot-sports-empire-backend`

### **Configure Service:**
- **Name:** `bot-sports-empire` (auto-filled from render.yaml)
- **Region:** Oregon (us-west) or closest to you
- **Branch:** `main`
- **Root Directory:** `.` (root)
- **Runtime:** **Docker** (auto-detected from Dockerfile)
- **Plan:** **Free** ($0/month)

### **Environment Variables:**
Render will auto-detect from `render.yaml`:
- `DATABASE_URL`: `sqlite:///./data/bot_sports.db`
- `CORS_ORIGINS`: `["https://bot-sports-empire.onrender.com", "http://localhost:3000"]`
- `PYTHONPATH`: `/opt/render/project/src`

### **Deploy:**
1. Click "Create Web Service"
2. Render will:
   - Build Docker image
   - Install dependencies from `requirements-deploy-final.txt`
   - Start server on port 10000
   - Wait for health check (`/health`)

## **✅ STEP 3: VERIFICATION**

### **Build Logs:**
Watch for:
```
✅ Building from Dockerfile
✅ Installing dependencies (fastapi 0.128.0, pydantic 2.12.5)
✅ Starting uvicorn server
✅ Health check passed
```

### **Test Deployment:**
```bash
# Get your Render URL (format: https://bot-sports-empire.onrender.com)
./test_render_deployment.sh https://bot-sports-empire.onrender.com
```

**Expected Results:**
1. ✅ `/health` → `{"status":"healthy"}`
2. ✅ `/docs` → FastAPI Swagger UI (200 OK)
3. ✅ `/api/v1/players/?limit=5` → 5 players
4. ✅ `/api/v1/drafts/` → JSON response

## **🔧 TECHNICAL DETAILS**

### **Docker Configuration:**
- **Base Image:** `python:3.14-slim`
- **Port:** `8002` (internal) → `$PORT` (Render)
- **Database:** SQLite at `/app/data/bot_sports.db`
- **Health Check:** `/health` every 30 seconds

### **Dependencies:**
**Proven working versions:**
- `fastapi==0.128.0`
- `pydantic==2.12.5` (pre-built wheels, no compilation)
- `uvicorn[standard]==0.40.0`
- `sqlalchemy==2.0.20`

### **Database:**
- **Size:** 4.5 MB (11,539 players)
- **Location:** Persistent disk (`/app/data/`)
- **Backup:** Included in git (for development)

## **🚨 TROUBLESHOOTING**

### **Build Fails:**
1. **pydantic-core wheel error:** Already fixed with 2.12.5
2. **Port conflict:** Render uses `$PORT` env variable
3. **Disk space:** Free tier has 512MB RAM, 1GB disk

### **Health Check Fails:**
1. Check logs: `render.com/dashboard` → service → logs
2. Test locally: `uvicorn app.main:app --host 0.0.0.0 --port 8002`
3. Verify imports: `python3 -c "from app.main import app"`

### **Database Issues:**
1. SQLite file copied to `/app/data/`
2. Permissions: Render runs as non-root user
3. Migration: Alembic ready but not required for SQLite

## **🎯 POST-DEPLOYMENT**

### **Test WebSocket:**
```bash
# Install wscat
npm install -g wscat

# Connect to draft room
wscat -c wss://bot-sports-empire.onrender.com/ws/drafts/test-draft
```

### **Create First Draft:**
```bash
curl -X POST https://bot-sports-empire.onrender.com/api/v1/drafts/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Draft","draft_type":"snake","rounds":3,"team_count":4}'
```

### **Test Bot AI:**
```bash
# Get draft_id from above, then:
curl "https://bot-sports-empire.onrender.com/api/v1/bot-ai/drafts/{draft_id}/ai-pick?team_id=1"
```

## **📊 MONITORING**

### **Render Dashboard:**
- **URL:** `https://dashboard.render.com`
- **Metrics:** CPU, memory, requests
- **Logs:** Real-time build and runtime logs
- **Deploys:** Manual/auto deploy history

### **Health Endpoints:**
- `GET /health` - Basic health check
- `GET /docs` - API documentation
- `GET /redoc` - Alternative docs

## **🚀 PRODUCTION READY FEATURES**

### **Included:**
1. ✅ 44 API endpoints
2. ✅ WebSocket draft room
3. ✅ Bot AI with real ADP data
4. ✅ 11,539 player database
5. ✅ Docker production configuration
6. ✅ Health checks
7. ✅ CORS configured

### **Ready for:**
1. Beta user testing
2. Frontend integration
3. Moltbook bot integration
4. Summer 2026 launch

---

**🎯 DEPLOYMENT TIMELINE: ~30 MINUTES**
1. GitHub repo: 5 min
2. Push code: 2 min  
3. Render setup: 5 min
4. Build/deploy: 10-15 min
5. Testing: 5 min

**Bot Sports Empire will be LIVE at: https://bot-sports-empire.onrender.com**