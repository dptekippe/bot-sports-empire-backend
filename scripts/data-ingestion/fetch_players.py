#!/usr/bin/env python3
"""
Fetch NFL player data from Sleeper API and store in our database.
"""
import asyncio
import httpx
import json
from datetime import datetime
from pathlib import Path
import sys

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.core.database import SessionLocal
from app.models.player import Player


SLEEPER_API_URL = "https://api.sleeper.app/v1/players/nfl"


async def fetch_players():
    """Fetch all NFL players from Sleeper API."""
    print(f"Fetching players from {SLEEPER_API_URL}...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(SLEEPER_API_URL)
            response.raise_for_status()
            players_data = response.json()
            print(f"Fetched {len(players_data)} players")
            return players_data
        except Exception as e:
            print(f"Error fetching players: {e}")
            return {}


def process_player_data(player_id, player_data):
    """Process raw Sleeper player data into our schema."""
    if not player_data:
        return None
    
    # Extract basic info
    player = {
        "player_id": player_id,
        "first_name": player_data.get("first_name", ""),
        "last_name": player_data.get("last_name", ""),
        "full_name": player_data.get("full_name", ""),
        "position": player_data.get("position", ""),
        "team": player_data.get("team", ""),
        "height": player_data.get("height", ""),
        "weight": player_data.get("weight"),
        "age": player_data.get("age"),
        "college": player_data.get("college", ""),
        "status": player_data.get("status", ""),
        "injury_status": player_data.get("injury_status", ""),
        "injury_notes": player_data.get("injury_notes", ""),
        "fantasy_positions": player_data.get("fantasy_positions", []),
        "stats": player_data.get("stats", {}),
        "metadata": {
            "espn_id": player_data.get("espn_id"),
            "yahoo_id": player_data.get("yahoo_id"),
            "rotowire_id": player_data.get("rotowire_id"),
            "sportradar_id": player_data.get("sportradar_id"),
            "gsis_id": player_data.get("gsis_id"),
        },
        "search_full_name": player_data.get("search_full_name", "").lower(),
        "search_first_name": player_data.get("search_first_name", "").lower(),
        "search_last_name": player_data.get("search_last_name", "").lower(),
    }
    
    return player


async def save_players_to_db(players_data):
    """Save processed player data to database."""
    db = SessionLocal()
    try:
        players_processed = 0
        players_created = 0
        players_updated = 0
        
        for player_id, raw_data in players_data.items():
            players_processed += 1
            
            # Process the data
            player_dict = process_player_data(player_id, raw_data)
            if not player_dict:
                continue
            
            # Check if player exists
            existing_player = db.query(Player).filter(Player.player_id == player_id).first()
            
            if existing_player:
                # Update existing player
                for key, value in player_dict.items():
                    if key != "player_id":  # Don't update primary key
                        setattr(existing_player, key, value)
                existing_player.updated_at = datetime.utcnow()
                players_updated += 1
            else:
                # Create new player
                player = Player(**player_dict)
                db.add(player)
                players_created += 1
            
            # Commit every 100 players to avoid huge transactions
            if players_processed % 100 == 0:
                db.commit()
                print(f"Processed {players_processed} players...")
        
        # Final commit
        db.commit()
        
        print(f"\nPlayer ingestion complete:")
        print(f"  Total processed: {players_processed}")
        print(f"  New players: {players_created}")
        print(f"  Updated players: {players_updated}")
        
    except Exception as e:
        db.rollback()
        print(f"Error saving players to database: {e}")
        raise
    finally:
        db.close()


async def main():
    """Main ingestion function."""
    print("Starting NFL player data ingestion...")
    
    # Fetch players from Sleeper API
    players_data = await fetch_players()
    
    if not players_data:
        print("No player data fetched. Exiting.")
        return
    
    # Save to database
    await save_players_to_db(players_data)
    
    print("Player ingestion completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())