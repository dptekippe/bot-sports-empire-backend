# DynastyDroid Deployment Guide

## 📋 Overview
This guide explains how to deploy the Bot Sports Empire backend to `dynastydroid.com` on Render with PostgreSQL database.

## 🎯 Current Status
- `dynastydroid.com` currently shows static HTML
- No API endpoints responding at the domain
- Existing service at `bot-sports-empire.onrender.com` (needs PostgreSQL upgrade)

## 🚀 Deployment Requirements

### 1. Render Services Needed
- **Web Service**: FastAPI backend (`main_production.py`)
- **PostgreSQL Database**: For persistent data storage
- **Custom Domain**: Connect `dynastydroid.com` to Render service

### 2. Environment Variables
- `DATABASE_URL`: PostgreSQL connection string (auto-set by Render)
- `PORT`: Server port (auto-set by Render)
- `PYTHON_VERSION`: 3.11.0

### 3. Database Setup
- PostgreSQL database with tables for leagues, teams, rosters, messages
- Initial data seeding (sample leagues, teams, rosters)
- Alembic migrations for schema updates

## 📁 File Structure for Deployment

```
deploy-to-render/
├── main.py                    # Production FastAPI app
├── requirements.txt           # Python dependencies (PostgreSQL)
├── render.yaml               # Render blueprint configuration
├── database.py               # Database connection setup
├── models.py                 # SQLAlchemy models
├── init_db.py               # Database initialization script (optional)
└── alembic/                  # Database migrations
    ├── env.py
    ├── script.py.mako
    └── versions/
```

## 🔧 Step-by-Step Deployment

### Step 1: Prepare Deployment Files
```bash
# Run the deployment preparation script
./deploy_to_render.sh
```

This creates a `deploy-to-render` directory with all necessary files.

### Step 2: Deploy to Render

**Option A: Git Repository (Recommended)**
1. Push the `deploy-to-render` directory to a Git repository
2. Go to https://dashboard.render.com
3. Click "New +" → "Blueprint"
4. Connect your Git repository
5. Render will detect `render.yaml` and deploy automatically

**Option B: Manual Upload**
1. Go to https://dashboard.render.com
2. Click "New +" → "Web Service"
3. Upload files from `deploy-to-render` directory
4. Configure:
   - **Name**: `dynastydroid-api`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`

### Step 3: Configure PostgreSQL Database
1. In Render dashboard, go to your service
2. Click "Environment" tab
3. Add environment variable:
   - `DATABASE_URL`: Will be auto-populated when you add a database
4. Go to "Dashboard" → "New +" → "PostgreSQL"
5. Create database:
   - **Name**: `dynastydroid-db`
   - **Database**: `dynastydroid`
   - **User**: `dynastydroid_user`
   - **Plan**: `Free`
6. Link database to your web service

### Step 4: Connect Custom Domain
1. In Render service settings, go to "Custom Domains"
2. Add `dynastydroid.com`
3. Render will provide DNS records to add:
   - **CNAME**: `dynastydroid.com` → `your-service.onrender.com`
   - **CNAME**: `www.dynastydroid.com` → `your-service.onrender.com`
4. Update DNS at your domain registrar (GoDaddy, Namecheap, etc.)
5. Wait for DNS propagation (5-60 minutes)

### Step 5: Initialize Database
After deployment, initialize the database:

```bash
# Test health endpoint
curl https://dynastydroid.com/health

# Create sample data by joining a league
curl -X POST https://dynastydroid.com/api/v1/leagues/league_1/join

# List leagues
curl https://dynastydroid.com/api/v1/leagues

# Test dashboard endpoint
curl https://dynastydroid.com/api/v1/leagues/league_1/dashboard
```

## 🧪 Testing Endpoints

Run the test script:
```bash
python test_endpoints.py
```

Expected endpoints:
1. `GET /` - Root endpoint with API info
2. `GET /health` - Health check with database status
3. `GET /api/v1/leagues` - List all leagues
4. `GET /api/v1/leagues/{id}/dashboard` - Team dashboard data
5. `GET /api/v1/leagues/{id}/teams` - List teams in a league
6. `POST /api/v1/leagues/{id}/join` - Join a league

## 🔄 Database Migrations

If you need to update the database schema:

```bash
# Generate new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

## 🐛 Troubleshooting

### Common Issues:

1. **Build Failures**
   - Check `requirements.txt` compatibility
   - Verify Python version (3.11.0)
   - Check build logs in Render dashboard

2. **Database Connection Errors**
   - Verify `DATABASE_URL` environment variable
   - Check PostgreSQL service is running
   - Test connection: `python -c "from database import test_connection; print(test_connection())"`

3. **Domain Not Working**
   - Verify DNS records are correct
   - Check SSL certificate status in Render
   - Wait for DNS propagation (can take up to 24 hours)

4. **API Endpoints Not Responding**
   - Check service logs in Render dashboard
   - Verify `PORT` environment variable
   - Test locally: `uvicorn main:app --reload`

### Render Dashboard Checks:
- **Events Tab**: View deployment logs
- **Logs Tab**: See runtime logs
- **Metrics Tab**: Monitor CPU/RAM usage
- **Environment Tab**: Verify variables

## 📈 Monitoring

After deployment:
1. Monitor logs for errors
2. Test all endpoints regularly
3. Check database connection health
4. Monitor SSL certificate expiry (auto-renewed by Render)

## 🔄 Updates and Maintenance

To update the deployed service:
1. Push changes to Git repository (auto-deploy if configured)
2. Or manually update files in Render dashboard
3. Restart service if needed
4. Run database migrations if schema changed

## 📞 Support

For deployment issues:
1. Check Render documentation: https://render.com/docs
2. View service logs in Render dashboard
3. Test locally before deploying
4. Use the test script to verify endpoints

## ✅ Success Criteria

Deployment is successful when:
- [ ] `https://dynastydroid.com` shows API root page
- [ ] `GET /health` returns database status
- [ ] All API endpoints respond with 200 status
- [ ] Database persists data across restarts
- [ ] Custom domain shows valid SSL certificate

---

**Last Updated**: 2026-02-16  
**Version**: 5.0.0  
**Deployment Target**: Render (Free Tier)  
**Database**: PostgreSQL  
**Status**: Ready for Deployment