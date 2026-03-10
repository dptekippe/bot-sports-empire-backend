#!/usr/bin/env python3
"""
Initialize database on first startup.
Creates empty database with schema if it doesn't exist.
"""

import os
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import engine, Base, SessionLocal
from app.models.player import Player
from app.models.draft import Draft, DraftPick
from app.models.team import Team
from app.models.league import League
from app.models.mood import BotAgent, MoodEvent
from app.models.scoring import ScoringRule
from app.models.dynasty import FutureDraftPick

def init_database():
    """Create all tables if they don't exist."""
    print("🔧 Initializing database...")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    
    # Create a test player to verify
    db = SessionLocal()
    try:
        # Check if any players exist
        player_count = db.query(Player).count()
        print(f"📊 Current player count: {player_count}")
        
        if player_count == 0:
            print("⚠️  Database is empty - player data needs to be imported")
            print("   Run: python import_players.py (when available)")
        else:
            print(f"✅ Database has {player_count} players")
            
    finally:
        db.close()
    
    print("🎯 Database initialization complete")

if __name__ == "__main__":
    init_database()