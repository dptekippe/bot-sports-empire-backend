#!/bin/bash
echo "=== TESTING MODEL ENUM FIX ==="
echo ""

echo "1. Testing GET /api/v1/leagues/ (should now work!):"
curl -s "http://localhost:8001/api/v1/leagues/" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'✅ SUCCESS! Found {len(data)} leagues')
    if data:
        print(f'  First league: {data[0][\"name\"]}')
        print(f'  Status: {data[0][\"status\"]}')
        print(f'  League Type: {data[0][\"league_type\"]}')
        print('  ✓ All leagues returned successfully!')
    else:
        print('  ℹ️ No leagues found (database might be empty)')
except Exception as e:
    print(f'❌ ERROR: {e}')
    print('  This means the model enum fix did not work.')
"

echo ""
echo "---"

echo "2. Creating a test league to verify:"
CREATE_RESPONSE=$(curl -s -X POST "http://localhost:8001/api/v1/leagues/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Model Enum Fix Test League",
    "description": "Testing the model enum _missing_ method fix",
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
    print(f'✅ Created league: {data[\"name\"]}')
    print(f'  ID: {data[\"id\"]}')
    print(f'  Status: {data[\"status\"]} (should be \"forming\")')
    print(f'  League Type: {data[\"league_type\"]} (should be \"dynasty\")')
except Exception as e:
    print(f'❌ Error creating league: {e}')
"

echo ""
echo "---"

echo "3. Testing GET all leagues again:"
curl -s "http://localhost:8001/api/v1/leagues/" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'✅ Found {len(data)} total leagues')
    for i, league in enumerate(data):
        print(f'  {i+1}. {league[\"name\"]} - Status: {league[\"status\"]}')
    if len(data) > 0:
        print('  ✓ GET /leagues/ endpoint is WORKING!')
except Exception as e:
    print(f'❌ Error: {e}')
"

echo ""
echo "=== TEST COMPLETE ==="
echo "If all tests pass, the ROOT CAUSE enum issue is FIXED! 🎉"
