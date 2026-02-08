"""
Simple main file to test the backend without complex dependencies.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .core.config_simple import settings
from .core.database import engine, Base

# Create tables FIRST (before importing models with relationships)
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "Welcome to Bot Sports Empire API",
        "version": settings.PROJECT_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "bot-sports-api"}


@app.get("/test-bot-claim")
async def test_bot_claim():
    """Test endpoint for bot claiming (simplified)."""
    return {
        "message": "Bot claiming API is ready!",
        "personalities": ["stat_nerd", "trash_talker", "risk_taker", "strategist", "emotional", "balanced"],
        "note": "Full API will be available once models are properly loaded.",
    }


if __name__ == "__main__":
    print(f"🚀 Starting {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}")
    print(f"📚 API docs: http://localhost:8000/docs")
    print(f"🏈 Database: {settings.DATABASE_URL}")
    uvicorn.run(
        "app.main_simple:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )