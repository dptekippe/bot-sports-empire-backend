#!/usr/bin/env python3
"""
Create test players in Docker database.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.player import Player

db = SessionLocal()

# Create test players
test_players = [
    {
        "player_id": "4046",
        "first_name": "Patrick",
        "last_name": "Mahomes",
        "full_name": "Patrick Mahomes",
        "position": "QB",
        "team": "KC",
        "average_draft_position": 25.5,
        "external_adp": 24.8,
        "active": True
    },
    {
        "player_id": "5177",
        "first_name": "Ja'Marr",
        "last_name": "Chase",
        "full_name": "Ja'Marr Chase",
        "position": "WR",
        "team": "CIN",
        "average_draft_position": 1.4,
        "external_adp": 1.4,
        "active": True
    },
    {
        "player_id": "5670",
        "first_name": "Bijan",
        "last_name": "Robinson",
        "full_name": "Bijan Robinson",
        "position": "RB",
        "team": "ATL",
        "average_draft_position": 1.9,
        "external_adp": 1.9,
        "active": True
    },
    {
        "player_id": "2860",
        "first_name": "Saquon",
        "last_name": "Barkley",
        "full_name": "Saquon Barkley",
        "position": "RB",
        "team": "PHI",
        "average_draft_position": 1.85,
        "external_adp": 1.85,
        "active": True
    },
    {
        "player_id": "4876",
        "first_name": "Justin",
        "last_name": "Jefferson",
        "full_name": "Justin Jefferson",
        "position": "WR",
        "team": "MIN",
        "average_draft_position": 4.2,
        "external_adp": 4.2,
        "active": True
    }
]

print("🚀 Creating test players in Docker database...")
created_count = 0

for player_data in test_players:
    try:
        # Check if player exists
        existing = db.query(Player).filter(Player.player_id == player_data["player_id"]).first()
        
        if existing:
            # Update existing player
            for key, value in player_data.items():
                setattr(existing, key, value)
            print(f"✅ Updated: {player_data['full_name']}")
        else:
            # Create new player
            player = Player(**player_data)
            db.add(player)
            print(f"✅ Created: {player_data['full_name']}")
        
        created_count += 1
        
    except Exception as e:
        print(f"❌ Error with {player_data.get('full_name', 'unknown')}: {e}")

try:
    db.commit()
    print(f"\n🎯 Successfully created/updated {created_count} players")
    
    # Verify
    total_players = db.query(Player).count()
    print(f"📊 Total players in database: {total_players}")
    
except Exception as e:
    print(f"❌ Commit failed: {e}")
    db.rollback()
finally:
    db.close()