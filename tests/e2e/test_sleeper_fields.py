#!/usr/bin/env python3
"""
Test to see actual Sleeper API fields for schema planning.
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.integrations.sleeper_client import SleeperClient


async def analyze_sleeper_fields():
    """Analyze Sleeper API fields to plan database schema."""
    print("🔍 Analyzing Sleeper API fields for schema planning...")
    
    async with SleeperClient() as client:
        # Get a small sample of players
        players = await client.get_all_players()
        
        if not players:
            print("❌ No players returned from Sleeper")
            return
        
        print(f"✅ Got {len(players)} players")
        
        # Take first 5 players and analyze their fields
        sample_players = list(players.items())[:5]
        
        all_fields = set()
        field_types = {}
        
        for player_id, player_data in sample_players:
            print(f"\n📋 Player: {player_data.get('first_name', '')} {player_data.get('last_name', '')}")
            print(f"   ID: {player_id}")
            
            for field, value in player_data.items():
                all_fields.add(field)
                field_type = type(value).__name__
                
                if field not in field_types:
                    field_types[field] = set()
                field_types[field].add(field_type)
        
        print(f"\n{'='*60}")
        print("📊 FIELD ANALYSIS FOR DATABASE SCHEMA")
        print("="*60)
        
        # Categorize fields
        core_fields = [
            'player_id', 'first_name', 'last_name', 'full_name', 
            'position', 'team', 'status', 'injury_status'
        ]
        
        physical_fields = [
            'height', 'weight', 'age', 'college'
        ]
        
        fantasy_fields = [
            'fantasy_positions', 'bye_week', 'years_exp',
            'metadata', 'search_rank', 'search_first_name', 'search_last_name'
        ]
        
        external_id_fields = [
            'espn_id', 'yahoo_id', 'rotowire_id', 'sportradar_id', 'stats_id'
        ]
        
        print("\n🎯 CORE FIELDS (Essential for drafts):")
        for field in sorted(core_fields):
            if field in all_fields:
                types = ', '.join(field_types.get(field, ['unknown']))
                print(f"  • {field:20} → {types}")
        
        print("\n🏃 PHYSICAL ATTRIBUTES:")
        for field in sorted(physical_fields):
            if field in all_fields:
                types = ', '.join(field_types.get(field, ['unknown']))
                print(f"  • {field:20} → {types}")
        
        print("\n📈 FANTASY FIELDS:")
        for field in sorted(fantasy_fields):
            if field in all_fields:
                types = ', '.join(field_types.get(field, ['unknown']))
                print(f"  • {field:20} → {types}")
        
        print("\n🔗 EXTERNAL ID FIELDS:")
        for field in sorted(external_id_fields):
            if field in all_fields:
                types = ', '.join(field_types.get(field, ['unknown']))
                print(f"  • {field:20} → {types}")
        
        print("\n📝 OTHER FIELDS:")
        other_fields = sorted(all_fields - set(core_fields + physical_fields + fantasy_fields + external_id_fields))
        for field in other_fields[:20]:  # Show first 20
            types = ', '.join(field_types.get(field, ['unknown']))
            print(f"  • {field:20} → {types}")
        
        if len(other_fields) > 20:
            print(f"  ... and {len(other_fields) - 20} more fields")
        
        # Show metadata structure for one player
        print(f"\n{'='*60}")
        print("🔍 METADATA FIELD STRUCTURE (for JSON storage):")
        print("="*60)
        
        for player_id, player_data in sample_players[:1]:
            metadata = player_data.get('metadata', {})
            if metadata:
                print(f"Metadata keys: {list(metadata.keys())}")
                # Show a few important metadata fields
                important_meta = ['adp', 'adp_formatted', 'adp_ppr', 'adp_half_ppr']
                for key in important_meta:
                    if key in metadata:
                        print(f"  • {key}: {metadata[key]}")
            
            # Show stats if present
            stats = player_data.get('stats', {})
            if stats:
                print(f"\nStats keys (sample): {list(stats.keys())[:10]}")
        
        print(f"\n{'='*60}")
        print("💡 DATABASE SCHEMA RECOMMENDATIONS:")
        print("="*60)
        print("""
1. CORE TABLE (players):
   • Keep existing fields: player_id, first_name, last_name, full_name, position, team
   • Add: status, injury_status (from Sleeper)
   • Add: sleeper_metadata (JSON) for all other Sleeper fields

2. SEPARATE TABLES (future):
   • player_stats: season, week, player_id, stat_type, value
   • player_adp_history: date, player_id, format, adp_value
   • player_news: timestamp, player_id, source, headline, impact

3. IMMEDIATE ACTION:
   • Add status, injury_status columns to players table
   • Add sleeper_metadata JSON column
   • Keep existing fantasy_positions, stats JSON columns
        """)
        
        # Save sample for reference
        with open('sleeper_sample.json', 'w') as f:
            json.dump(sample_players[0][1], f, indent=2)
        print(f"\n💾 Saved sample player data to 'sleeper_sample.json'")


if __name__ == "__main__":
    asyncio.run(analyze_sleeper_fields())