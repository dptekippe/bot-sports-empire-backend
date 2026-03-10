#!/bin/bash
# Simple setup without Docker - for initial development

set -e

echo "🚀 Simple Bot Sports Empire Setup (No Docker)"
echo "============================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_step() {
    echo -e "\n${YELLOW}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check Python
print_step "Checking Python..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
print_success "Python $PYTHON_VERSION detected"

# Check pip
print_step "Checking pip..."
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is not installed"
    exit 1
fi
print_success "pip3 detected"

# Setup backend
print_step "Setting up backend..."
cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Created virtual environment"
else
    print_success "Virtual environment already exists"
fi

# Activate and install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
print_success "Python dependencies installed"

# Create .env file if needed
if [ ! -f ".env" ]; then
    cat > .env << EOF
# Development configuration (SQLite for simplicity)
DATABASE_URL=sqlite:///./bot_sports.db
REDIS_URL=redis://localhost:6379  # Optional for now

# Security
SECRET_KEY=dev-secret-key-$(openssl rand -hex 16)

# API
API_V1_PREFIX=/api/v1
PROJECT_NAME=Bot Sports Empire
PROJECT_VERSION=0.1.0

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]

# External APIs
SLEEPER_API_URL=https://api.sleeper.app/v1
EOF
    print_success "Created .env file"
else
    print_success ".env file already exists"
fi

# Create SQLite database and tables
print_step "Creating database..."
python3 -c "
from app.core.database import Base, engine
Base.metadata.create_all(bind=engine)
print('Database tables created')
"
print_success "Database tables created"

# Test the setup
print_step "Testing setup..."
if python3 -c "from app.main import app; print('FastAPI app loaded successfully')"; then
    print_success "Backend setup complete!"
else
    print_error "Backend setup failed"
    exit 1
fi

deactivate
cd ..

# Setup frontend placeholder
print_step "Setting up frontend placeholder..."
mkdir -p frontend
cat > frontend/README.md << 'EOF'
# Bot Sports Empire Frontend

Frontend will be built with:
- Next.js 14 (React framework)
- TypeScript
- Tailwind CSS
- Shadcn/ui components

To set up later:
1. Install Node.js 18+
2. Run: npx create-next-app@latest . --typescript --tailwind --app
3. Install dependencies
4. Connect to backend API

For now, backend API is available at: http://localhost:8000
API docs: http://localhost:8000/docs
EOF
print_success "Frontend placeholder created"

# Create development scripts
print_step "Creating development scripts..."

# Start backend script
cat > start-backend.sh << 'EOF'
#!/bin/bash
cd backend
source venv/bin/activate
python -m app.main
EOF
chmod +x start-backend.sh

# Test API script
cat > test-api.sh << 'EOF'
#!/bin/bash
echo "Testing Bot Sports Empire API..."
echo "Health check:"
curl -s http://localhost:8000/health | python3 -m json.tool
echo ""
echo "API docs available at: http://localhost:8000/docs"
EOF
chmod +x test-api.sh

print_success "Development scripts created"

print_step "Setup complete! 🎉"
echo ""
echo "Next steps:"
echo "1. Start backend: ./start-backend.sh"
echo "2. Test API: ./test-api.sh"
echo "3. Access docs: http://localhost:8000/docs"
echo ""
echo "📋 YOUR ACTION ITEMS (when you have time):"
echo "   [ ] 1. Install Docker Desktop"
echo "   [ ] 2. Buy domain name (suggest: botsports.gg)"
echo "   [ ] 3. Set up Railway/Supabase accounts"
echo "   [ ] 4. Request Moltbook API access"
echo ""
echo "🏈 Happy building! Roger will continue development while you're at work."