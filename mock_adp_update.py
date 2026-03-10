#!/usr/bin/env python3
"""
Mock ADP update for development/testing.

Generates realistic ADP values for players based on position.
Allows Phase 5 development to proceed while Sleeper API is investigated.
"""
import sys
import os
import random
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.player import Player

# Realistic ADP ranges by position (based on 2024 fantasy drafts)
POSITION_ADP_RANGES = {
    "QB": (1, 150),      # QBs go 1st-12th round
    "RB": (1, 200),      # RBs dominate early rounds
    "WR": (1, 200),      # WRs also early-mid rounds
    "TE": (20, 150),     # TEs after elite ones
    "K": (150, 250),     # Kickers late
    "DEF": (150, 250),   # Defenses late
    # IDP positions
    "DL": (200, 300),
    "LB": (200, 300),
    "DB": (200, 300),
    # Other positions
    "P": (250, 350),
    "LS": (300, 400),
}

# Top players by position (mock elite ADPs)
TOP_PLAYERS = {
    "QB": ["4046", "6796", "7244"],      # Mahomes, Allen, Hurts
    "RB": ["4034", "6795", "7248"],      # McCaffrey, Taylor, Ekeler
    "WR": ["4038", "6797", "7247"],      # Jefferson, Chase, Hill
    "TE": ["4056", "6798", "7249"],      # Kelce, Andrews, Hockenson
}


def generate_realistic_adp(position: str, player_id: str) -> float:
    """Generate realistic ADP value for a player."""
    if position not in POSITION_ADP_RANGES:
        position = "WR"  # Default
    
    min_adp, max_adp = POSITION_ADP_RANGES[position]
    
    # Ensure positive values
    min_adp = max(1, min_adp)
    max_adp = max(min_adp + 10, max_adp)
    
    # Check if this is a top player
    for pos, top_ids in TOP_PLAYERS.items():
        if position == pos and player_id in top_ids:
            # Top players get elite ADP (early rounds)
            return round(random.uniform(1, 20), 1)
    
    # Regular players: generate based on position distribution
    # Most players cluster in the middle of the range
    base = random.uniform(min_adp, max_adp)
    
    # Ensure positive and reasonable
    base = max(1, base)
    base = min(300, base)  # Cap at 300
    
    # Add some randomness but keep realistic distribution
    if position in ["QB", "RB", "WR", "TE"]:
        # Skill positions: more variance
        result = base + random.uniform(-10, 10)
    else:
        # Other positions: less variance
        result = base + random.uniform(-5, 5)
    
    # Ensure positive
    result = max(1, result)
    return round(result, 1)


def update_mock_adp():
    """Update all players with mock ADP data."""
    db = SessionLocal()
    
    try:
        print("🚀 Generating Mock ADP Data")
        print("=" * 60)
        
        # Get all players
        players = db.query(Player).all()
        print(f"Found {len(players)} players in database")
        
        updated_count = 0
        position_counts: Dict[str, int] = {}
        
        for player in players:
            if not player.position:
                continue
            
            # Generate realistic ADP
            new_adp = generate_realistic_adp(player.position, player.player_id)
            player.average_draft_position = new_adp
            
            # Also generate fantasy pro rank (correlated with ADP)
            if new_adp < 100:
                player.fantasy_pro_rank = int(new_adp * 0.8 + random.uniform(0, 20))
            else:
                player.fantasy_pro_rank = int(new_adp * 0.9 + random.uniform(0, 50))
            
            updated_count += 1
            position_counts[player.position] = position_counts.get(player.position, 0) + 1
        
        # Commit changes
        db.commit()
        
        print(f"\n✅ Mock ADP update complete!")
        print(f"   Updated: {updated_count} players")
        print(f"   By position:")
        for pos, count in sorted(position_counts.items()):
            print(f"     • {pos}: {count} players")
        
        # Test: Show top players by position
        print("\n🎯 Sample Top Players by ADP:")
        print("=" * 50)
        
        for position in ["QB", "RB", "WR", "TE"]:
            top_players = db.query(Player).filter(
                Player.position == position,
                Player.average_draft_position.isnot(None)
            ).order_by(
                Player.average_draft_position.asc()
            ).limit(3).all()
            
            if top_players:
                print(f"\n{position}:")
                for i, player in enumerate(top_players, 1):
                    adp = player.average_draft_position
                    rank = player.fantasy_pro_rank
                    print(f"  {i}. {player.full_name:25} | ADP: {adp:6.1f} | Rank: {rank or 'N/A':4}")
        
        # Verify curl test would work
        print("\n🔧 Test command (after server restart):")
        print('curl -s "http://localhost:8002/api/v1/players/?position=QB&limit=5" | python3 -c "')
        print('import sys, json')
        print('data = json.load(sys.stdin)')
        print('print(\"QBs by ADP:\")')
        print('for p in data[\"players\"]:')
        print('    print(f\"  • {p[\"full_name\"]}: {p.get(\\\"average_draft_position\\\", \\\"N/A\\\")}\")')
        print('"')
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("Mock ADP Update for Development")
    print("Note: Using realistic mock data while Sleeper API is investigated")
    print()
    
    confirm = input("Generate mock ADP data for all players? (yes/no): ")
    
    if confirm.lower() in ["yes", "y"]:
        success = update_mock_adp()
        if success:
            print("\n✅ Phase 5 can now proceed with ADP-based features!")
            print("🎯 WebSocket draft room, bot AI, and Clawdbook hook ready for development.")
            sys.exit(0)
        else:
            print("\n❌ Mock ADP update failed")
            sys.exit(1)
    else:
        print("❌ Update cancelled.")
        sys.exit(0)