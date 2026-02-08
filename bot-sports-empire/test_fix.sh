#!/bin/bash
echo "=== Testing Fixed Leagues API ==="
echo ""
echo "1. Starting server in background..."
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001 &
SERVER_PID=$!
sleep 3

echo ""
echo "2. Testing debug endpoint..."
curl -s "http://localhost:8001/api/v1/leagues/debug/test" | python3 -m json.tool

echo ""
echo "3. Testing POST league creation..."
curl -X POST "http://localhost:8001/api/v1/leagues/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Dynasty League Fixed",
    "description": "Test league with fixed schema",
    "league_type": "dynasty",
    "max_teams": 12,
    "min_teams": 4,
    "is_public": true,
    "season_year": 2025,
    "scoring_type": "PPR"
  }' \
  --max-time 10

echo ""
echo ""
echo "4. Testing GET leagues..."
curl -s "http://localhost:8001/api/v1/leagues/" | python3 -m json.tool

echo ""
echo "5. Stopping server..."
kill $SERVER_PID 2>/dev/null
echo "Test complete!"
