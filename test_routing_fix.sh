#!/bin/bash
echo "=== Testing Routing Fix ==="
echo ""
echo "Expected endpoint: POST /api/v1/leagues/"
echo ""

# Test command
echo "Test command:"
cat << 'TESTCMD'
curl -X POST "http://localhost:8001/api/v1/leagues/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test League Routing Fix",
    "description": "Testing the routing fix",
    "league_type": "dynasty",
    "max_teams": 12,
    "min_teams": 4,
    "is_public": true,
    "season_year": 2025,
    "scoring_type": "PPR"
  }' \
  --max-time 10
TESTCMD

echo ""
echo "=== Server Status ==="
echo "Check if server is running on port 8001:"
if lsof -ti:8001 > /dev/null 2>&1; then
    echo "✅ Server is running on port 8001"
    echo ""
    echo "=== Quick Test ==="
    curl -s "http://localhost:8001/health" 2>/dev/null || echo "Health endpoint not responding"
else
    echo "❌ Server NOT running on port 8001"
    echo ""
    echo "To start server:"
    echo "cd \"/Volumes/External Corsair SSD /bot-sports-empire/backend\""
    echo "python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001"
fi
