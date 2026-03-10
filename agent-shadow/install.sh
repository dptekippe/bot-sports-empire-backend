#!/bin/bash
# Agent Shadow - Install Script

echo "🌓 Agent Shadow - Installation"
echo "=============================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "✗ Python 3 not found"
    exit 1
fi

echo "✓ Python found: $(python3 --version)"

# Check for requests library
python3 -c "import requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing requests library..."
    pip3 install requests
fi

echo "✓ requests library ready"

# Check Ollama
curl -s http://localhost:11434/ > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "✗ Ollama is not running"
    echo "  Start Ollama with: ollama serve"
    exit 1
fi

echo "✓ Ollama is running"

# Check for Qwen models
echo "Checking for Qwen models..."
curl -s http://localhost:11434/api/tags | grep -q "qwen3.5:4b"
if [ $? -ne 0 ]; then
    echo "  Pulling qwen3.5:4b..."
    ollama pull qwen3.5:4b
fi

curl -s http://localhost:11434/api/tags | grep -q "qwen3.5:9b"
if [ $? -ne 0 ]; then
    echo "  Pulling qwen3.5:9b..."
    ollama pull qwen3.5:9b
fi

echo "✓ Qwen models ready"

# Create directories
mkdir -p src/queue src/queue_deep src/output config

echo ""
echo "==============================
echo "Installation complete!"
echo ""
echo "To start Agent Shadow:"
echo "  cd agent-shadow/src"
echo "  python3 run_production.py"
echo ""
echo "To check status:"
echo "  python3 status.py"
echo ""
echo "Dashboard: http://localhost:18787"
