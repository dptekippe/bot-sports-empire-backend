#!/bin/bash
echo "=== Testing All League Endpoints ==="
echo ""

# Base URL
BASE_URL="http://localhost:8001/api/v1/leagues"

# 1. Test GET /leagues/ (list all)
echo "1. Testing GET /leagues/ (list all):"
curl -s "$BASE_URL/" || echo "Failed"

echo ""
echo "---"

# 2. Test POST /leagues/ (create)
echo "2. Testing POST /leagues/ (create):"
CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test League Complete",
    "description": "Testing all endpoints",
    "league_type": "dynasty",
    "max_teams": 12,
    "min_teams": 4,
    "is_public": true,
    "season_year": 2025,
    "scoring_type": "PPR"
  }')

echo "$CREATE_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'Created league ID: {data.get(\"id\", \"unknown\")}')
    print(f'League name: {data.get(\"name\", \"unknown\")}')
except:
    print('Failed to parse response or create league')
"

echo ""
echo "---"

# 3. Extract league ID for further tests
LEAGUE_ID=$(echo "$CREATE_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('id', ''))
except:
    print('')
" 2>/dev/null)

if [ -n "$LEAGUE_ID" ]; then
    echo "3. Testing GET /leagues/{id}:"
    curl -s "$BASE_URL/$LEAGUE_ID" || echo "Failed"
    
    echo ""
    echo "---"
    
    echo "4. Testing POST /leagues/{id}/teams:"
    curl -s -X POST "$BASE_URL/$LEAGUE_ID/teams" \
      -H "Content-Type: application/json" \
      -d '{
        "name": "Test Team",
        "abbreviation": "TEST",
        "bot_id": "test-bot-123"
      }' || echo "Failed"
    
    echo ""
    echo "---"
    
    echo "5. Testing GET /leagues/{id}/teams:"
    curl -s "$BASE_URL/$LEAGUE_ID/teams" || echo "Failed"
    
    echo ""
    echo "---"
    
    echo "6. Testing debug endpoint:"
    curl -s "$BASE_URL/debug/test" || echo "Failed"
else
    echo "Could not extract league ID, skipping further tests"
fi

echo ""
echo "=== Test Complete ==="
