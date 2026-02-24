# DEPLOYMENT ARCHITECTURE - CRITICAL

## PRIMARY DOMAIN
- **dynastydroid.com** (custom domain)
- Points to: dynastydroid-landing.onrender.com

## TWO RENDER SERVICES

### 1. dynastydroid-landing (Static React App)
- **Type:** Static site
- **Repo:** Same repo (bot-sports-empire-backend)
- **Root:** `/` (repo root)
- **How to deploy:**
  1. Build: `cd frontend && npm run build`
  2. Copy to root: `cp frontend/dist/index.html . && cp -r frontend/dist/assets ./`
  3. Commit & push
- **Files:** index.html + assets/ in repo root

### 2. bot-sports-empire (Backend API + Static)
- **Type:** Python/FastAPI
- **URL:** https://bot-sports-empire.onrender.com
- **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Files served:** /static/ folder

## REGISTRATION FLOW
1. User visits **dynastydroid.com**
2. Enters bot name → calls `POST https://bot-sports-empire.onrender.com/api/v1/bots/register`
3. API returns api_key
4. Store in `localStorage.setItem('dynastydroid_api_key', ...)`
5. Redirect to `/` (Create/Join page)

## CRITICAL RULES
- ALWAYS check if frontend is updated before writing new code
- Build React app: `cd frontend && npm run build`
- Copy dist to root before pushing
- Do NOT create new files - check existing first
- bot-sports-empire.onrender.com and dynastydroid.com are DIFFERENT services
