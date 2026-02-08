#!/usr/bin/env python3
"""
Simple database initialization - only creates essential tables.
"""

import os
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import engine, Base

def init_database_simple():
    """Create only essential tables to avoid import errors."""
    print("🔧 Initializing database (simple version)...")
    
    # Import only models that definitely exist
    from app.models.player import Player
    from app.models.draft import Draft, DraftPick
    from app.models.team import Team
    from app.models.league import League
    
    # Create tables for models we can import
    tables_to_create = [Player, Draft, DraftPick, Team, League]
    
    for model in tables_to_create:
        print(f"  Creating table for {model.__name__}...")
        model.__table__.create(bind=engine, checkfirst=True)
    
    print("✅ Essential tables created")
    print("🎯 Database ready for use")
    print("\nNote: Some tables (mood, scoring, dynasty) may need manual setup")

if __name__ == "__main__":
    init_database_simple()