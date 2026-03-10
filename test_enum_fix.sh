#!/bin/bash
echo "=== Testing Enum Fix ==="
echo ""

# Test GET /leagues/ - should now work!
echo "1. Testing GET /api/v1/leagues/ (list all leagues):"
curl -s "http://localhost:8001/api/v1/leagues/" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'✓ Success! Found {len(data)} leagues')
    if data:
        print(f'  First league: {data[0][\"name\"]}')
        print(f'  Status: {data[0][\"status\"]}')
        print(f'  League Type: {data[0][\"league_type\"]}')
except Exception as e:
    print(f'✗ Error: {e}')
"

echo ""
echo "---"

# Test creating a new league
echo "2. Testing POST /api/v1/leagues/ (create new league):"
curl -s -X POST "http://localhost:8001/api/v1/leagues/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Final Test League",
    "description": "Testing enum fix",
    "league_type": "dynasty",
    "max_teams": 12,
    "min_teams": 4,
    "is_public": true,
    "season_year": 2025,
    "scoring_type": "PPR"
  }' | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'✓ Created league: {data[\"name\"]}')
    print(f'  ID: {data[\"id\"]}')
    print(f'  Status: {data[\"status\"]}')
    print(f'  League Type: {data[\"league_type\"]}')
except Exception as e:
    print(f'✗ Error: {e}')
"

echo ""
echo "=== Test Complete ==="
