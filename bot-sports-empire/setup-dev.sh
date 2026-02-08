#!/bin/bash
# Bot Sports Empire Development Setup Script

set -e

echo "🚀 Setting up Bot Sports Empire development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_step() {
    echo -e "\n${YELLOW}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check prerequisites
print_step "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

print_success "All prerequisites are installed"

# Create .env file if it doesn't exist
print_step "Setting up environment variables..."

if [ ! -f "backend/.env" ]; then
    cat > backend/.env << EOF
# Database
DATABASE_URL=postgresql://bot_sports:bot_sports_password@localhost:5432/bot_sports

# Redis
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=dev-secret-key-change-in-production-$(openssl rand -hex 16)

# API
API_V1_PREFIX=/api/v1
PROJECT_NAME=Bot Sports Empire
PROJECT_VERSION=0.1.0

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
EOF
    print_success "Created backend/.env file"
else
    print_success "backend/.env already exists"
fi

# Start Docker services
print_step "Starting Docker services (PostgreSQL, Redis)..."
cd docker
docker-compose up -d postgres redis

# Wait for PostgreSQL to be ready
print_step "Waiting for PostgreSQL to be ready..."
until docker-compose exec postgres pg_isready -U bot_sports; do
    sleep 2
done
print_success "PostgreSQL is ready"

# Wait for Redis to be ready
print_step "Waiting for Redis to be ready..."
until docker-compose exec redis redis-cli ping | grep -q PONG; do
    sleep 2
done
print_success "Redis is ready"

# Setup Python virtual environment
print_step "Setting up Python virtual environment..."
cd ../backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Created virtual environment"
else
    print_success "Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
print_step "Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
print_success "Dependencies installed"

# Create database tables
print_step "Creating database tables..."
python3 -c "
from app.core.database import Base, engine
Base.metadata.create_all(bind=engine)
print('Database tables created')
"
print_success "Database tables created"

# Fetch initial player data
print_step "Fetching initial player data from Sleeper API..."
if python3 scripts/data-ingestion/fetch_players.py; then
    print_success "Player data fetched successfully"
else
    print_error "Failed to fetch player data. You can run this manually later."
fi

print_step "Development setup complete! 🎉"
echo ""
echo "Next steps:"
echo "1. Start the backend: cd backend && source venv/bin/activate && python -m app.main"
echo "2. Or use Docker Compose: cd docker && docker-compose up"
echo "3. Access the API: http://localhost:8000"
echo "4. View API docs: http://localhost:8000/docs"
echo ""
echo "To stop services: cd docker && docker-compose down"
echo ""
echo "Happy coding! 🏈🤖"