#!/bin/bash
# Minimal setup - just get Python backend running

set -e

echo "🤖 MINIMAL BOT SPORTS EMPIRE SETUP"
echo "=================================="

cd backend

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv

# Activate and install minimal dependencies
source venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn sqlalchemy pydantic python-dotenv httpx

# Create SQLite database
echo "Creating SQLite database..."
cat > .env << 'EOF'
DATABASE_URL=sqlite:///./bot_sports.db
SECRET_KEY=dev-key-minimal-setup
API_V1_PREFIX=/api/v1
EOF

# Create database tables
python3 -c "
from app.core.database import Base, engine
Base.metadata.create_all(bind=engine)
print('✅ Database tables created')
"

# Test the app
echo "Testing FastAPI app..."
if python3 -c "from app.main import app; print('✅ FastAPI app loaded successfully')"; then
    echo ""
    echo "🎉 MINIMAL SETUP COMPLETE!"
    echo ""
    echo "To start the backend:"
    echo "  cd backend"
    echo "  source venv/bin/activate"
    echo "  python -m app.main"
    echo ""
    echo "Then visit: http://localhost:8000"
    echo "API docs: http://localhost:8000/docs"
    echo ""
    echo "📋 Your action items (when you have time):"
    echo "  1. Install Docker Desktop"
    echo "  2. Buy domain (suggest: botsports.gg)"
    echo "  3. Set up Railway/Supabase"
    echo "  4. Request Moltbook API access"
    echo ""
    echo "🏈 Roger will continue building while you work!"
else
    echo "❌ Setup failed"
    exit 1
fi