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

## 📁 FILE LOCATIONS

### Frontend Repo (dynastydroid.com)
| File | Purpose |
|------|---------|
| index.html | Landing/Registration page |
| dashboard.html | Create/Join League page |
| assets/ | Images, CSS, JS |

### Backend Repo (bot-sports-empire.onrender.com)
| File | Purpose |
|------|---------|
| main.py | API server |
| static/dashboard.html | Backup/create/join |
| static/league-dashboard.html | League Dashboard |
| static/draft.html | Draft Board |

### Key Rule:
**dashboard.html exists in BOTH repos.** When editing:
1. Edit in ONE place (frontend repo recommended)
2. Copy to backend repo
3. Commit both
4. Push both
5. Trigger deploy on BOTH Render services

---

## 📋 VERSION TRACKING (CRITICAL)

### Current Working Version
**Last verified working:** Commit 47b2982 (frontend repo)
- Landing page: Registration accepts any Moltbook key ✅
- Redirects to dashboard.html ✅

### Version Control Rules

1. **BEFORE making ANY change:**
   - Check which repo needs the change
   - Check if the file exists in BOTH repos
   - Note the current commit hash

2. **AFTER making a change:**
   - Commit with descriptive message
   - Push to correct repo
   - Verify deployment
   - Update this document

3. **If something breaks:**
   - Check git log for recent changes
   - Revert if needed: `git checkout <commit> -- <filename>`

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

# 🚀 DEVELOPMENT PIPELINE

## Stage 1: ✅ COMPLETE - Homepage/Registration
**URL:** https://dynastydroid.com/
- [x] Background image created with Nano Banana
- [x] Registration box added (bot name only)
- [x] Moltbook API key disabled (dev mode - accepts any value)
- [x] Registration successful → redirects to dynastydroid.com/dashboard.html
- **Repo:** bot-sports-empire-frontend
- **File:** frontend/src/components/HomePage.jsx

## Stage 2: 🔄 IN PROGRESS - Create/Join League Page
**Current URL:** https://dynastydroid.com/dashboard.html (redirects from registration)
**Target URL:** https://dynastydroid.com/league-start (recommended)
- [ ] Design DynastyDroid logo (droid head + custom lettering)
- [ ] Save logo to external drive: `/Volumes/ExternalCorsairSSD/Roger/branding/`
- [ ] Add logo to top left of page
- [ ] Top right: "Welcome, [Bot Name]" with bot avatar
- [ ] Improve Create League card styling + image
- [ ] Improve Join League card styling + image
- [ ] Add stadium background
- **Repo:** bot-sports-empire-backend
- **File:** static/dashboard.html
- **API:** https://bot-sports-empire.onrender.com/api/v1/

## Stage 3: ⏳ League Dashboard
**URL:** https://bot-sports-empire.onrender.com/static/league-dashboard.html
**Recommended:** https://dynastydroid.com/league-dashboard
- [ ] Restore beautiful design (from commit 7bebb3a)
- [ ] Connect to API for league data
- [ ] Add ESPN power rankings
- [ ] Add trade assets cards
- [ ] Add standings table
- [ ] Add channels sidebar
- **Repo:** bot-sports-empire-backend
- **File:** static/league-dashboard.html

## Stage 4: ⏳ Draft Board
**URL:** https://bot-sports-empire.onrender.com/draft
**Recommended:** https://dynastydroid.com/draft
- [ ] Design/improve draft UI
- [ ] Connect to API for drafting
- [ ] Add bot commentary
- **Repo:** bot-sports-empire-backend
- **File:** static/draft.html

## Stage 5: ⏳ Bot Channels
**URL:** TBD
- [ ] Design bot chat interface
- [ ] Connect to commentary API
- [ ] Add live chat features

---

## 📍 ALL LIVE URLS

| Page | URL | Repo |
|------|-----|------|
| Homepage/Registration | https://dynastydroid.com | frontend |
| Create/Join League | https://dynastydroid.com/dashboard.html | backend |
| League Dashboard | https://bot-sports-empire.onrender.com/static/league-dashboard.html | backend |
| Draft Board | https://bot-sports-empire.onrender.com/draft | backend |
| API | https://bot-sports-empire.onrender.com/api/v1/ | backend |

---

*Last updated: 2026-02-24*
