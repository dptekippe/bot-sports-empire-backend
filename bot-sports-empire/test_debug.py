import sys
sys.path.append('.')

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import uvicorn

from app.core.database import get_db, engine, Base
from app.models.league import League

# Create test app
app = FastAPI()

@app.get("/test-db")
async def test_db(db: Session = Depends(get_db)):
    try:
        # Simple query to test DB connection
        count = db.query(League).count()
        return {"status": "success", "league_count": count}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/test-simple")
async def test_simple():
    return {"status": "success", "message": "Simple POST works"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
