"""
ULTRA-SIMPLE FastAPI app for Render - NO dependencies except FastAPI!
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(
    title="Bot Sports Empire API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Mount static files for HTML draft board
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/")
async def root():
    return {
        "message": "🏈 Welcome to Bot Sports Empire API!",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/health",
        "healthz": "/healthz",
        "note": "MVP version - full platform coming soon!"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "bot-sports-empire"}

@app.get("/healthz")
async def health_check_z():
    return {"status": "healthy", "service": "bot-sports-empire", "endpoint": "healthz"}

@app.get("/draft-board")
async def draft_board():
    return {
        "message": "Draft board API is ready!",
        "teams": 12,
        "rounds": 8,
        "format": "dynasty_superflex",
        "status": "mock_data_available"
    }

@app.get("/draft")
async def draft_html():
    """Serve the HTML draft board."""
    return FileResponse("draft.html")

@app.get("/draft/")
async def draft_html_slash():
    """Serve the HTML draft board (with trailing slash)."""
    return FileResponse("draft.html")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)