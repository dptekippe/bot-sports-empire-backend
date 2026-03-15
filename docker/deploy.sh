#!/bin/bash
# Render Deploy Script for Roger Stack

set -e

echo "🐳 Building Roger Stack Docker Image..."

# Build Docker image
docker build -t roger-stack:latest -f docker/Dockerfile .

echo "✅ Docker image built"

# Run docker-compose
echo "🚀 Starting services..."
cd docker
cp .env.example .env
# Edit .env with your actual values before running
docker-compose up -d

echo "✅ Roger Stack deployed!"
echo ""
echo "Services:"
echo "  - Roger API: http://localhost:3000"
echo "  - PostgreSQL: localhost:5432"
echo ""
echo "To deploy to Render:"
echo "  1. Copy .env.example to .env and fill in values"
echo "  2. render-blueprint deploy render.yaml"
