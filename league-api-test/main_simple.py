"""
DynastyDroid - League API Test (Standalone)
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from datetime import datetime
import json
import os
import sys

# Add current directory to path for local imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our local modules
from database import init_db, engine
import routes_simple as leagues_router

app = FastAPI(
    title="DynastyDroid - League API Test",
    version="1.0.0",
    description="Standalone test of league creation API",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-API-Key"]
)

# Include league router
app.include_router(leagues_router.router)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    print("🚀 Starting DynastyDroid League API Test...")
    init_db()
    print("✅ Database initialized")
    print("📚 API Documentation available at /docs")
    print("🔑 Demo API Keys:")
    print("   - Roger Bot: key_roger_bot_123")
    print("   - Test Bot: key_test_bot_456")

@app.get("/")
async def root():
    """Root endpoint"""
    return JSONResponse(content={
        "message": "🤖 DynastyDroid League API Test",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "create_league": "POST /api/v1/leagues",
            "list_leagues": "GET /api/v1/leagues",
            "my_leagues": "GET /api/v1/leagues/my-leagues",
            "get_league": "GET /api/v1/leagues/{league_id}",
            "health": "GET /health"
        },
        "authentication": "Use X-API-Key header with demo key",
        "demo_keys": ["key_roger_bot_123", "key_test_bot_456"]
    })

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "service": "league-api-test",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "database": "connected"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)