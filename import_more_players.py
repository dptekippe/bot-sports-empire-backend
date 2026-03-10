#!/usr/bin/env python3
"""
Import more test players for Docker testing.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.player import Player

db = SessionLocal()

# Additional test players (top 50 fantasy players)
more_players = [
    # Top RBs
    {"player_id": "4034", "first_name": "Christian", "last_name": "McCaffrey", "full_name": "Christian McCaffrey", "position": "RB", "team": "SF", "average_draft_position": 1.2, "external_adp": 1.2, "active": True},
    {"player_id": "6795", "first_name": "Jonathan", "last_name": "Taylor", "full_name": "Jonathan Taylor", "position": "RB", "team": "IND", "average_draft_position": 4.2, "external_adp": 4.2, "active": True},
    {"player_id": "4039", "first_name": "Austin", "last_name": "Ekeler", "full_name": "Austin Ekeler", "position": "RB", "team": "WAS", "average_draft_position": 6.3, "external_adp": 6.3, "active": True},
    {"player_id": "7248", "first_name": "Bijan", "last_name": "Robinson", "full_name": "Bijan Robinson", "position": "RB", "team": "ATL", "average_draft_position": 1.9, "external_adp": 1.9, "active": True},
    {"player_id": "4040", "first_name": "Derrick", "last_name": "Henry", "full_name": "Derrick Henry", "position": "RB", "team": "BAL", "average_draft_position": 8.1, "external_adp": 8.1, "active": True},
    
    # Top WRs
    {"player_id": "4038", "first_name": "Justin", "last_name": "Jefferson", "full_name": "Justin Jefferson", "position": "WR", "team": "MIN", "average_draft_position": 2.1, "external_adp": 2.1, "active": True},
    {"player_id": "6797", "first_name": "Ja'Marr", "last_name": "Chase", "full_name": "Ja'Marr Chase", "position": "WR", "team": "CIN", "average_draft_position": 1.4, "external_adp": 1.4, "active": True},
    {"player_id": "7247", "first_name": "Tyreek", "last_name": "Hill", "full_name": "Tyreek Hill", "position": "WR", "team": "MIA", "average_draft_position": 5.1, "external_adp": 5.1, "active": True},
    {"player_id": "4042", "first_name": "Stefon", "last_name": "Diggs", "full_name": "Stefon Diggs", "position": "WR", "team": "HOU", "average_draft_position": 15.7, "external_adp": 15.7, "active": True},
    {"player_id": "6799", "first_name": "CeeDee", "last_name": "Lamb", "full_name": "CeeDee Lamb", "position": "WR", "team": "DAL", "average_draft_position": 16.4, "external_adp": 16.4, "active": True},
    
    # Top QBs
    {"player_id": "6796", "first_name": "Josh", "last_name": "Allen", "full_name": "Josh Allen", "position": "QB", "team": "BUF", "average_draft_position": 9.0, "external_adp": 9.0, "active": True},
    {"player_id": "4046", "first_name": "Patrick", "last_name": "Mahomes", "full_name": "Patrick Mahomes", "position": "QB", "team": "KC", "average_draft_position": 10.2, "external_adp": 10.2, "active": True},
    {"player_id": "7244", "first_name": "Jalen", "last_name": "Hurts", "full_name": "Jalen Hurts", "position": "QB", "team": "PHI", "average_draft_position": 11.5, "external_adp": 11.5, "active": True},
    {"player_id": "6802", "first_name": "Joe", "last_name": "Burrow", "full_name": "Joe Burrow", "position": "QB", "team": "CIN", "average_draft_position": 25.4, "external_adp": 25.4, "active": True},
    {"player_id": "7253", "first_name": "Justin", "last_name": "Herbert", "full_name": "Justin Herbert", "position": "QB", "team": "LAC", "average_draft_position": 26.1, "external_adp": 26.1, "active": True},
    
    # Top TEs
    {"player_id": "4044", "first_name": "Travis", "last_name": "Kelce", "full_name": "Travis Kelce", "position": "TE", "team": "KC", "average_draft_position": 21.4, "external_adp": 21.4, "active": True},
    {"player_id": "6798", "first_name": "Mark", "last_name": "Andrews", "full_name": "Mark Andrews", "position": "TE", "team": "BAL", "average_draft_position": 13.6, "external_adp": 13.6, "active": True},
    {"player_id": "7249", "first_name": "Sam", "last_name": "LaPorta", "full_name": "Sam LaPorta", "position": "TE", "team": "DET", "average_draft_position": 14.3, "external_adp": 14.3, "active": True},
    
    # More players for testing
    {"player_id": "4041", "first_name": "Dalvin", "last_name": "Cook", "full_name": "Dalvin Cook", "position": "RB", "team": "FA", "average_draft_position": 12.8, "external_adp": 12.8, "active": True},
    {"player_id": "7250", "first_name": "Garrett", "last_name": "Wilson", "full_name": "Garrett Wilson", "position": "WR", "team": "NYJ", "average_draft_position": 17.2, "external_adp": 17.2, "active": True},
    {"player_id": "4043", "first_name": "Davante", "last_name": "Adams", "full_name": "Davante Adams", "position": "WR", "team": "LV", "average_draft_position": 18.5, "external_adp": 18.5, "active": True},
    {"player_id": "6800", "first_name": "A.J.", "last_name": "Brown", "full_name": "A.J. Brown", "position": "WR", "team": "PHI", "average_draft_position": 19.3, "external_adp": 19.3, "active": True},
    {"player_id": "7251", "first_name": "Chris", "last_name": "Olave", "full_name": "Chris Olave", "position": "WR", "team": "NO", "average_draft_position": 20.1, "external_adp": 20.1, "active": True},
    {"player_id": "6801", "first_name": "Nick", "last_name": "Chubb", "full_name": "Nick Chubb", "position": "RB", "team": "CLE", "average_draft_position": 22.6, "external_adp": 22.6, "active": True},
    {"player_id": "7252", "first_name": "Jahmyr", "last_name": "Gibbs", "full_name": "Jahmyr Gibbs", "position": "RB", "team": "DET", "average_draft_position": 23.3, "external_adp": 23.3, "active": True},
    {"player_id": "4045", "first_name": "Saquon", "last_name": "Barkley", "full_name": "Saquon Barkley", "position": "RB", "team": "PHI", "average_draft_position": 24.7, "external_adp": 24.7, "active": True},
    {"player_id": "4047", "first_name": "Lamar", "last_name": "Jackson", "full_name": "Lamar Jackson", "position": "QB", "team": "BAL", "average_draft_position": 27.8, "external_adp": 27.8, "active": True},
]

print("🚀 Importing additional test players...")
created_count = 0
updated_count = 0

for player_data in more_players:
    try:
        # Check if player exists
        existing = db.query(Player).filter(Player.player_id == player_data["player_id"]).first()
        
        if existing:
            # Update existing player
            for key, value in player_data.items():
                setattr(existing, key, value)
            updated_count += 1
        else:
            # Create new player
            player = Player(**player_data)
            db.add(player)
            created_count += 1
        
    except Exception as e:
        print(f"❌ Error with {player_data.get('full_name', 'unknown')}: {e}")

try:
    db.commit()
    print(f"\n🎯 Import complete!")
    print(f"✅ Created: {created_count} new players")
    print(f"✅ Updated: {updated_count} existing players")
    
    # Verify total
    total_players = db.query(Player).count()
    print(f"📊 Total players in database: {total_players}")
    
except Exception as e:
    print(f"❌ Commit failed: {e}")
    db.rollback()
finally:
    db.close()