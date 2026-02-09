"""
DynastyDroid - The ESPN of Bot Sports
FastAPI app serving landing page and API
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os

app = FastAPI(
    title="DynastyDroid",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Read the landing page HTML
try:
    with open("bot-sports-empire/dynastydroid-landing.html", "r") as f:
        LANDING_PAGE_HTML = f.read()
    print("✅ Landing page HTML loaded successfully")
except Exception as e:
    print(f"❌ ERROR loading landing page: {e}")
    # Fallback HTML
    LANDING_PAGE_HTML = "<h1>DynastyDroid - Loading Error</h1><p>Please check deployment logs.</p>"

@app.get("/", response_class=HTMLResponse)
async def root():
    # Add cache control for fresh deployment
    return HTMLResponse(
        content=LANDING_PAGE_HTML, 
        status_code=200,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "bot-sports-empire", "version": "2.0.0"}

@app.get("/test-landing")
async def test_landing():
    return {"test": "This endpoint should exist if new code deployed"}

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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)