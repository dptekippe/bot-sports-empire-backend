#!/usr/bin/env python3
"""
Debug enum validation
"""
import sys
sys.path.append('.')

from app.schemas.league import LeagueResponse
from app.models.league import LeagueStatus

# Test 1: Test validator with string
print("=== Test 1: Validator with string 'forming' ===")
try:
    # Simulate what database might return
    test_data = {
        'id': 'test-id',
        'name': 'Test League',
        'description': 'Test',
        'league_type': 'dynasty',
        'max_teams': 12,
        'min_teams': 4,
        'is_public': True,
        'season_year': 2025,
        'scoring_type': 'PPR',
        'status': 'forming',  # String from database
        'current_teams': 0,
        'current_week': 1,
        'created_at': '2025-02-01T12:00:00',
        'updated_at': None
    }
    result = LeagueResponse(**test_data)
    print(f"✓ Success! Status: {result.status}")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n=== Test 2: Validator with enum instance ===")
try:
    test_data = {
        'id': 'test-id',
        'name': 'Test League',
        'description': 'Test',
        'league_type': 'dynasty',
        'max_teams': 12,
        'min_teams': 4,
        'is_public': True,
        'season_year': 2025,
        'scoring_type': 'PPR',
        'status': LeagueStatus.FORMING,  # Enum instance
        'current_teams': 0,
        'current_week': 1,
        'created_at': '2025-02-01T12:00:00',
        'updated_at': None
    }
    result = LeagueResponse(**test_data)
    print(f"✓ Success! Status: {result.status}")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n=== Test 3: Check LeagueStatus enum values ===")
print(f"LeagueStatus.FORMING = {LeagueStatus.FORMING}")
print(f"LeagueStatus.FORMING.value = {LeagueStatus.FORMING.value}")
print(f"LeagueStatus.FORMING.name = {LeagueStatus.FORMING.name}")

print("\n=== Test 4: Test from_orm simulation ===")
# Create a mock SQLAlchemy object
class MockLeague:
    def __init__(self):
        self.id = 'test-id'
        self.name = 'Test League'
        self.description = 'Test'
        self.league_type = 'dynasty'  # String from DB
        self.max_teams = 12
        self.min_teams = 4
        self.is_public = True
        self.season_year = 2025
        self.scoring_type = 'PPR'
        self.status = 'forming'  # String from DB
        self.current_teams = 0
        self.current_week = 1
        self.created_at = '2025-02-01T12:00:00'
        self.updated_at = None

try:
    mock_league = MockLeague()
    result = LeagueResponse.from_orm(mock_league)
    print(f"✓ from_orm success! Status: {result.status}")
except Exception as e:
    print(f"✗ from_orm error: {e}")
    import traceback
    traceback.print_exc()
