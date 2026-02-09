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
with open("dynastydroid-landing.html", "r") as f:
    LANDING_PAGE_HTML = f.read()

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content=LANDING_PAGE_HTML, status_code=200)

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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)