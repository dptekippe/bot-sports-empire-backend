"""
SUPER SIMPLE FastAPI app for Render - NO SQLAlchemy!
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(
    title="Bot Sports Empire API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "🏈 Welcome to Bot Sports Empire API!",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/health",
        "note": "MVP version - database coming soon"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "bot-sports-empire",
        "python_version": os.sys.version,
        "environment": os.getenv("RENDER", "local"),
    }

@app.get("/draft-board")
async def draft_board():
    """Simple draft board endpoint."""
    return {
        "message": "Draft board API is ready!",
        "features": ["12-team display", "8-round mock drafts", "Live updates"],
        "status": "coming_soon",
        "mock_data": {
            "teams": 12,
            "rounds": 8,
            "players": ["Patrick Mahomes", "Justin Jefferson", "Christian McCaffrey"],
            "format": "dynasty_superflex"
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)