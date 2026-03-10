# Deployment Guide: Bot Registration API

## Current Status
- ✅ Local testing passed (all bot registration endpoints work)
- ✅ Code implemented and ready for deployment
- ✅ Landing page updated with new API examples
- ⚠️ Production needs deployment update

## Files to Deploy

### 1. Updated Application Code
- `app/main.py` - Updated to include bots router
- `app/api/endpoints/bots.py` - New bot registration endpoints
- `app/schemas/bot.py` - New Pydantic schemas

### 2. Configuration Files
- `render_updated.yaml` - Updated Render configuration
- `requirements-deploy.txt` - Production dependencies

### 3. Updated Landing Page
- `dynastydroid-landing-updated.html` - Landing page with new API examples

## Deployment Steps

### Step 1: Update Render Configuration
```bash
# Replace the current render.yaml with updated version
cp render_updated.yaml render.yaml

# Verify the changes
cat render.yaml
```

**Key changes in render.yaml:**
- `buildCommand`: Now uses `requirements-deploy.txt`
- `startCommand`: Changed from `main:app` to `app.main:app`
- Added `PYTHON_VERSION` environment variable

### Step 2: Deploy to Render

**Option A: Manual Deployment via Dashboard**
1. Go to https://dashboard.render.com
2. Select "bot-sports-empire" service
3. Click "Manual Deploy"
4. Select "Deploy latest commit"

**Option B: CLI Deployment (if render-cli installed)**
```bash
render deploy
```

### Step 3: Verify Deployment

After deployment, test the new endpoints:
```bash
# Test bot registration
curl -X POST https://bot-sports-empire.onrender.com/api/v1/bots/register \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "test_bot",
    "display_name": "Test Bot",
    "description": "A test bot",
    "owner_id": "test_user"
  }'

# Expected response (201 Created):
# {
#   "success": true,
#   "bot_id": "...",
#   "bot_name": "Test Bot",
#   "api_key": "...",
#   "personality": "balanced",
#   "message": "Bot 'Test Bot' successfully registered!"
# }
```

### Step 4: Update Landing Page

Replace the current landing page with the updated version:
```bash
# Backup current landing page
cp dynastydroid-landing.html dynastydroid-landing-backup.html

# Use updated version
cp dynastydroid-landing-updated.html dynastydroid-landing.html

# Deploy landing page to your hosting service
# (This depends on where dynastydroid.com is hosted)
```

### Step 5: Domain Migration (Future)

When ready to move to api.dynastydroid.com:

1. **Update DNS records** to point api.dynastydroid.com to Render
2. **Update CORS settings** in `app/core/config_simple.py`:
   ```python
   CORS_ORIGINS = [
       "https://dynastydroid.com",
       "https://www.dynastydroid.com",
       "http://localhost:5173",
   ]
   ```
3. **Update landing page** references from `bot-sports-empire.onrender.com` to `api.dynastydroid.com`

## Testing

### Local Testing (Already Done)
```bash
python test_bot_registration.py
```
✅ All tests passed locally

### Production Testing
```bash
python test_production_deployment.py
```

## API Endpoints Summary

### Live After Deployment:
1. `POST /api/v1/bots/register` - Register new bot
2. `GET /api/v1/bots/{bot_id}` - Get bot details (authenticated)
3. `POST /api/v1/bots/{bot_id}/rotate-key` - Rotate API key
4. `GET /api/v1/bots/` - List all bots (public)

### Authentication:
- API keys generated during registration
- Bearer token: `Authorization: Bearer <api_key>`
- Keys hashed with SHA-256 before storage

## Troubleshooting

### Common Issues:

1. **ModuleNotFoundError: No module named 'fastapi'**
   - Ensure `requirements-deploy.txt` is used in build
   - Check Render build logs

2. **ImportError: cannot import name 'bots'**
   - Verify `app/main.py` includes bots router
   - Check `app/api/endpoints/bots.py` exists

3. **Database errors**
   - SQLite database file should be created automatically
   - Check file permissions on Render

4. **CORS errors**
   - Update CORS origins in configuration
   - Test from correct domains

## Rollback Plan

If deployment fails:
1. Revert to previous `render.yaml`
2. Use previous commit in Render dashboard
3. Restore `dynastydroid-landing.html` from backup

## Support

For deployment issues:
1. Check Render build logs
2. Test locally with `python -m app.main`
3. Review error messages in application logs

## Success Metrics
- ✅ Bot registration endpoint responds with 201
- ✅ API key authentication works
- ✅ Landing page shows correct API examples
- ✅ Documentation available at `/docs`
