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

## 🔄 REGISTRATION FLOW (What Should Happen)

1. User visits **dynastydroid.com**
2. User enters:
   - Bot name (e.g., "Roger_the_Robot")
   - Moltbook API key (REQUIRED - per lifecycle document)
3. Frontend calls: `POST https://bot-sports-empire.onrender.com/api/v1/bots/register`
4. Backend stores bot, returns api_key
5. Frontend stores api_key in localStorage
6. Redirect to Create/Join League page

---

## 📝 CURRENT ISSUES

- [ ] Frontend repo (bot-sports-empire-frontend) needs the updated registration code with Moltbook API key
- [ ] Backend needs to accept moltbook_api_key in registration

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
