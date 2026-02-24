# ⚠️⚠️⚠️ CRITICAL Reminder ⚠️⚠️⚠️

**BEFORE BUILDING ANYTHING:**
- ✅ REVIEW fully what has already been built
- ❌ DO NOT overwrite past work without fully understanding why it was built
- ❌ DO NOT default to reinventing the wheel
- ❌ DO NOT create new files when existing files already exist
- ✅ CHECK existing repos, files, and memory BEFORE creating anything new
- ✅ ASK if unsure instead of guessing

---

# DYNASTYDROID DEPLOYMENT ARCHITECTURE

## 📋 Version Tracking (CRITICAL)

### Current Working Version
- Frontend: Commit e0fa68d
- Backend: Commit 7458736
- Last verified working: 2026-02-24

### Version Control Rules
1. **BEFORE making ANY change:** Check which repo, note current commit
2. **AFTER making a change:** Push to frontend → Copy to backend → Push to backend → Trigger deploy on BOTH
3. **If something breaks:** Check git log, revert if needed

---

# 🚀 PHASE 1 COMPLETE: DynastyDroid (2026-02-24)

## 1. Brand Identity & UI/UX Visual Language
- **Aesthetic:** 2026-era Tactical/Elite Dashboard
- **Core:** Dark Slate background (#0a0a0f), Glassmorphism (blur), Cyan neon (#00e5ff) highlights
- **Typography:** High-contrast (Bold/Thin) sans-serif (Inter) for headers
- **Key Assets:** Custom Hexagonal SVG Droid Logo, Tactical SVG Icons (Blueprint/Radar)

## 2. The Data Bridge (LocalStorage)
| Key | Purpose | Default |
|-----|---------|---------|
| dynasty_user | User's display name | COMMANDER |
| created_league | League object | {name, type, character, maxTeams: 12, currentTeams: 1} |

## 3. Functional Milestones
- ✅ Landing Page: Captures user data, bridges to Dashboard
- ✅ Dashboard: Interactive "Choose Your Path" cards
- ✅ League Architect (Create Modal): Functional with success Toast
- ✅ Tactical Scanner (Join Modal): Real-time list with Fill-Priority Algorithm

## 4. Core Philosophy
- **Hybrid Platform:** Equally functional for human "God-View" and Bot "API-Based" interaction
- **Character Variable:** Primary seed for AI personality generation (Stat Nerds, Trash Talkers, etc.)

---

## 📍 ALL LIVE URLS

| Page | URL | Repo |
|------|-----|------|
| Homepage/Registration | https://dynastydroid.com | frontend |
| Create/Join League | https://dynastydroid.com/dashboard.html | frontend |
| League Dashboard | https://bot-sports-empire.onrender.com/static/league-dashboard.html | backend |
| Draft Board | https://bot-sports-empire.onrender.com/draft | backend |
| API | https://bot-sports-empire.onrender.com/api/v1/ | backend |

---

## 📁 FILE LOCATIONS

### Frontend Repo (dynastydroid.com)
| File | Purpose |
|------|---------|
| index.html | Landing/Registration |
| dashboard.html | Create/Join League |
| assets/ | Images, CSS, JS |

### Backend Repo (bot-sports-empire.onrender.com)
| File | Purpose |
|------|---------|
| main.py | API server |
| static/dashboard.html | Create/Join (backup) |
| static/league-dashboard.html | League Dashboard |
| static/draft.html | Draft Board |

### Key Rule:
**dashboard.html exists in BOTH repos.** When editing:
1. Edit in frontend repo
2. Copy to backend repo
3. Commit both
4. Push both
5. Trigger deploy on BOTH Render services

---

## 🔄 HOW TO DEPLOY

### Frontend (dynastydroid.com)
1. Make changes in frontend/ repo
2. `npm run build`
3. Copy dist/index.html to repo root
4. Remove package.json (static deploy)
5. Push to frontend repo
6. Trigger manual deploy on dynastydroid-landing

### Backend (bot-sports-empire.onrender.com)
1. Make changes in main.py or static/ folder
2. Push to backend repo
3. Auto-deploys OR trigger manually

---

*Last updated: 2026-02-24 - Phase 1 Complete*
