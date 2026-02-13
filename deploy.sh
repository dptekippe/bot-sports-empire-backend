#!/bin/bash

# DynastyDroid Deployment Script
# Deploys frontend and backend for local testing

echo "🚀 Deploying DynastyDroid..."

# Create necessary directories
mkdir -p logs

# Check if Python and pip are installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip."
    exit 1
fi

# Install backend dependencies
echo "📦 Installing backend dependencies..."
cd backend
pip3 install -r requirements.txt

# Start backend server in background
echo "🔧 Starting backend server..."
python3 main.py > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > ../logs/backend.pid

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 3

# Check if backend is running
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend is running at http://localhost:8000"
    echo "📚 API Docs: http://localhost:8000/docs"
else
    echo "❌ Backend failed to start. Check logs/backend.log"
    exit 1
fi

# Start simple HTTP server for frontend
echo "🌐 Starting frontend server..."
cd ../frontend
python3 -m http.server 8080 > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../logs/frontend.pid

# Wait for frontend to start
sleep 2

echo "✅ Frontend is running at http://localhost:8080"
echo ""
echo "📋 Access Points:"
echo "   Landing Page: http://localhost:8080/dynastydroid-landing.html"
echo "   Onboarding:   http://localhost:8080/onboarding.html"
echo "   Dashboard:    http://localhost:8080/dashboard.html"
echo "   API:          http://localhost:8000"
echo "   API Docs:     http://localhost:8000/docs"
echo ""
echo "🛑 To stop servers, run: ./stop.sh"
echo ""
echo "🎉 Deployment complete! Open your browser to get started."

# Create stop script
cd ..
cat > stop.sh << 'EOF'
#!/bin/bash
echo "🛑 Stopping DynastyDroid servers..."
if [ -f logs/backend.pid ]; then
    kill $(cat logs/backend.pid) 2>/dev/null
    rm logs/backend.pid
    echo "✅ Backend stopped"
fi
if [ -f logs/frontend.pid ]; then
    kill $(cat logs/frontend.pid) 2>/dev/null
    rm logs/frontend.pid
    echo "✅ Frontend stopped"
fi
echo "🎯 All servers stopped"
EOF
chmod +x stop.sh