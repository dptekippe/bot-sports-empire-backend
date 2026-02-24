# ⚠️⚠️⚠️ CRITICAL Reminder ⚠️⚠️⚠️

**BEFORE BUILDING ANYTHING:**
- ✅ REVIEW fully what has already been built
- ❌ DO NOT overwrite past work without fully understanding why it was built
- ❌ DO NOT default to reinventing the wheel
- ❌ DO NOT create new files when existing files already exist
- ✅ CHECK existing repos, files, and memory BEFORE creating anything new
- ✅ ASK if unsure instead of guessing

---

# DYNASTYDROID DEPLOYMENT ARCHITECTURE - COMPLETE GUIDE

## 📝 LESSONS LEARNED (2026-02-24)

### What We Learned Today:
1. **TWO REPOS = TWO RENDER SERVICES** - Don't mix them up
2. **Frontend deploy fails without package.json** - Remove it, use pre-built static files
3. **CORS middleware must be AFTER app creation** - Or it crashes
4. **Frontend = Static, Backend = Python** - Keep them separate
5. **Check git remote before pushing** - Always verify destination

---

## 🔴 CRITICAL: TWO SEPARATE REPOSITORIES

There are TWO GitHub repositories:

### 1. **bot-sports-empire-frontend** (React App)
- **URL:** https://github.com/dptekippe/bot-sports-empire-frontend
- **Deployed to:** dynastydroid-landing.onrender.com → dynastydroid.com (custom domain)
- **Contains:** React frontend (dynastydroid.com landing page + registration)
- **Files in repo root:**
  - index.html (React entry point)
  - assets/ (bundled JS/CSS)
  - frontend/src/components/HomePage.jsx (source code)

### 2. **bot-sports-empire-backend** (Python API)
- **URL:** https://github.com/dptekippe/bot-sports-empire-backend
- **Deployed to:** bot-sports-empire.onrender.com
- **Contains:** FastAPI backend + static HTML pages
- **Files:**
  - main.py (API server)
  - static/ (league-dashboard.html, draft.html, dashboard.html, style.css)
  - assets/ (images)

---

## 📍 LIVE URLS

| Service | URL | Repo |
|---------|-----|------|
| **DynastyDroid (Frontend)** | https://dynastydroid.com | bot-sports-empire-frontend |
| **Landing (alt)** | https://dynastydroid-landing.onrender.com | bot-sports-empire-frontend |
| **Backend API** | https://bot-sports-empire.onrender.com | bot-sports-empire-backend |
| **League Dashboard** | https://bot-sports-empire.onrender.com/static/league-dashboard.html | bot-sports-empire-backend |
| **Draft Board** | https://bot-sports-empire.onrender.com/draft | bot-sports-empire-backend |

---

## 🚀 HOW TO DEPLOY

### Deploying Frontend (dynastydroid.com)

**Render Settings (CRITICAL):**
- Build Command: **BLANK** (no npm build)
- Publish Directory: **.** (dot)
- Auto-deploy: ON
- **NO package.json** in repo root (causes build failure)

**Why this works:** Render serves pre-built static files directly from repo root instead of trying to build.

**Step 1:** Make changes in frontend/src/components/
```bash
# Edit the React source
cd /Users/danieltekippe/.openclaw/workspace/frontend
npm run build
```

**Step 2:** Copy to repo root
```bash
cp frontend/dist/index.html .
cp -r frontend/dist/assets/* ./assets/
```

**Step 3:** Commit and push to bot-sports-empire-frontend REPO
```bash
# Add remote if not exists
git remote add frontend https://github.com/dptekippe/bot-sports-empire-frontend.git

# Or if frontend remote already exists
git push frontend main
```

### Deploying Backend (bot-sports-empire.onrender.com)

**Step 1:** Make changes in main.py or static/ folder

**Step 2:** Commit and push to bot-sports-empire-backend REPO
```bash
git push origin main
```

---

## ⚠️ CRITICAL RULES

1. **ALWAYS check which repo you're pushing to**
   - Frontend changes → bot-sports-empire-frontend
   - Backend changes → bot-sports-empire-backend

2. **Do NOT mix up the repos**
   - dynasticyt.com = frontend repo
   - bot-sports-empire.onrender.com = backend repo

3. **Before ANY deploy, ask:**
   - "Which repo does this change belong to?"
   - "Which Render service does this URL use?"

4. **If unsure, check this document first**

---

## 🔄 REGISTRATION FLOW (Current - Working)

1. User visits **dynastydroid.com**
2. User enters **bot name only** (Moltbook API key is optional/dev mode)
3. Frontend calls: `POST https://bot-sports-empire.onrender.com/api/v1/bots/register`
4. Backend stores bot, returns api_key
5. Frontend stores api_key in localStorage (persists across sessions)
6. Redirect to Create/Join League page (https://bot-sports-empire.onrender.com/)

### CORS Setup (Required!)
In main.py, MUST add CORS after app creation:
```python
app = FastAPI(...)

# Add CORS for frontend (must be AFTER app creation)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dynastydroid.com", "https://www.dynastydroid.com", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📝 CURRENT STATUS (Working as of 2026-02-24)

- [x] Frontend registration (dynastydroid.com)
- [x] Backend API (bot-sports-empire.onrender.com)
- [x] CORS enabled
- [x] League Dashboard (static)
- [x] Bot registration works
- [ ] Auto-deploy on frontend (requires manual trigger)

---

## 🛠️ QUICK COMMANDS

```bash
# Check what repo you're in
git remote -v

# Push to frontend (dynastydroid.com)
git push frontend main

# Push to backend (API)
git push origin main
```

---

*Last updated: 2026-02-24*
