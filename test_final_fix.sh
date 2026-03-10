#!/bin/bash
echo "=== FINAL ENUM FIX TEST ==="
echo ""

# Test GET /leagues/ - should now work!
echo "1. Testing GET /api/v1/leagues/ (list all leagues):"
curl -s "http://localhost:8001/api/v1/leagues/" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'✓ SUCCESS! Found {len(data)} leagues')
    if data:
        print(f'  First league: {data[0][\"name\"]}')
        print(f'  Status: {data[0][\"status\"]}')
        print(f'  League Type: {data[0][\"league_type\"]}')
        print('  All leagues returned successfully!')
    else:
        print('  No leagues found (database empty)')
except Exception as e:
    print(f'✗ ERROR: {e}')
"

echo ""
echo "---"

# Test creating a new league
echo "2. Testing POST /api/v1/leagues/ (create new league):"
CREATE_RESPONSE=$(curl -s -X POST "http://localhost:8001/api/v1/leagues/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Final Test League Enum Fix",
    "description": "Testing the final enum fix",
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
    print(f'✓ Created league: {data[\"name\"]}')
    print(f'  ID: {data[\"id\"]}')
    print(f'  Status: {data[\"status\"]}')
    print(f'  League Type: {data[\"league_type\"]}')
except Exception as e:
    print(f'✗ Error: {e}')
"

echo ""
echo "---"

# Test GET all leagues again (should now have at least one)
echo "3. Testing GET /api/v1/leagues/ again (should show new league):"
curl -s "http://localhost:8001/api/v1/leagues/" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'✓ Found {len(data)} total leagues')
    for i, league in enumerate(data[:3]):  # Show first 3
        print(f'  {i+1}. {league[\"name\"]} - {league[\"status\"]}')
except Exception as e:
    print(f'✗ Error: {e}')
"

echo ""
echo "=== TEST COMPLETE ==="
echo "If all tests pass, the Bot Sports Empire league system is 100% complete! 🏈"
