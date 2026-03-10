#!/bin/bash
# Setup script for Render deployment

echo "🚀 Starting Bot Sports Empire deployment..."

# Check if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "✅ Found requirements.txt"
else
    echo "❌ requirements.txt not found, listing files:"
    ls -la
    exit 1
fi

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Create data directory for SQLite
mkdir -p data
echo "📁 Created data directory"

echo "✅ Setup complete!"
echo "📚 API docs will be available at /docs"
echo "🏈 Health check at /health"