#!/usr/bin/env python3
"""
Debug script to test league queries
"""
import sys
sys.path.append('.')

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models.league import League
import json

# Create session
db = SessionLocal()

try:
    print("=== Testing League Query ===")
    
    # Test 1: Count leagues
    count = db.query(League).count()
    print(f"1. League count: {count}")
    
    # Test 2: Get all leagues
    print("2. Getting all leagues...")
    leagues = db.query(League).all()
    print(f"   Found {len(leagues)} leagues")
    
    # Test 3: Try to serialize first league
    if leagues:
        print("3. Testing serialization of first league:")
        league = leagues[0]
        print(f"   ID: {league.id}")
        print(f"   Name: {league.name}")
        print(f"   Status: {league.status} (type: {type(league.status)})")
        print(f"   League Type: {league.league_type} (type: {type(league.league_type)})")
        print(f"   Created At: {league.created_at} (type: {type(league.created_at)})")
        
        # Try to convert to dict
        try:
            league_dict = {c.name: getattr(league, c.name) for c in league.__table__.columns}
            print("   ✓ Can convert to dict")
        except Exception as e:
            print(f"   ✗ Error converting to dict: {e}")
    
    # Test 4: Check database schema
    print("4. Checking League table columns:")
    for column in League.__table__.columns:
        print(f"   - {column.name}: {column.type}")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()

print("\n=== Debug Complete ===")
