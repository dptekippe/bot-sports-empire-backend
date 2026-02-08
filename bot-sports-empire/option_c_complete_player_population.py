#!/usr/bin/env python3
"""
OPTION C: Complete Player Population Foundation
===============================================
Goal: Import all 679 active skill position players from Sleeper API data
      to establish a complete foundation for the Bot Sports Empire platform.

Strategy:
1. Initialize database with proper schema
2. Filter Sleeper data for active QB/RB/WR/TE players
3. Import with proper data mapping
4. Add ADP data from external sources
5. Verify complete population
"""

import json
import sqlite3
from datetime import datetime
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def initialize_database():
    """Create SQLite database with proper schema"""
    print("🔧 Initializing database...")
    
    conn = sqlite3.connect('bot_sports.db')
    cursor = conn.cursor()
    
    # Create players table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS players (
        player_id TEXT PRIMARY KEY,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        full_name TEXT NOT NULL,
        position TEXT NOT NULL,
        team TEXT,
        height TEXT,
        weight INTEGER,
        age INTEGER,
        college TEXT,
        status TEXT,
        injury_status TEXT,
        injury_notes TEXT,
        fantasy_positions TEXT,  -- JSON array as text
        stats TEXT,  -- JSON as text
        metadata TEXT,  -- JSON as text
        espn_id TEXT,
        yahoo_id TEXT,
        rotowire_id INTEGER,
        current_team_id TEXT,
        draft_year INTEGER,
        draft_round INTEGER,
        bye_week INTEGER,
        average_draft_position REAL,
        fantasy_pro_rank INTEGER,
        external_adp REAL,
        external_adp_source TEXT,
        external_adp_updated_at TEXT,
        active INTEGER,  -- SQLite uses INTEGER for boolean
        years_exp INTEGER,
        jersey_number INTEGER,
        birth_date TEXT,
        high_school TEXT,
        depth_chart_position TEXT,
        practice_description TEXT,
        team_abbr TEXT,
        team_changed_at TEXT,
        sportradar_id TEXT,
        stats_id INTEGER,
        fantasy_data_id INTEGER,
        gsis_id TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        last_stats_update TEXT,
        search_full_name TEXT,
        search_first_name TEXT,
        search_last_name TEXT
    )
    ''')
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_players_position ON players(position)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_players_team ON players(team)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_players_active ON players(active)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_players_search_full_name ON players(search_full_name)')
    
    conn.commit()
    print("✅ Database initialized with players table")
    return conn

def load_sleeper_data():
    """Load and parse Sleeper player data"""
    print("📊 Loading Sleeper player data...")
    
    try:
        with open('sleeper_players_raw.json', 'r') as f:
            data = json.load(f)
        print(f"✅ Loaded {len(data):,} player records from Sleeper")
        return data
    except FileNotFoundError:
        print("❌ sleeper_players_raw.json not found!")
        print("Please ensure the Sleeper data file exists in the project root")
        return None

def filter_active_skill_players(sleeper_data):
    """Filter for active QB/RB/WR/TE players"""
    print("🎯 Filtering active skill position players...")
    
    active_skill_players = []
    skill_positions = {'QB', 'RB', 'WR', 'TE'}
    
    for player_id, player_data in sleeper_data.items():
        # Check if player has required fields
        if not all(key in player_data for key in ['first_name', 'last_name', 'position', 'status']):
            continue
            
        position = player_data.get('position')
        status = player_data.get('status')
        
        # Filter for active skill position players
        if position in skill_positions and status == 'Active':
            active_skill_players.append((player_id, player_data))
    
    print(f"✅ Found {len(active_skill_players)} active skill position players")
    
    # Count by position
    position_counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0}
    for _, player_data in active_skill_players:
        position = player_data.get('position')
        if position in position_counts:
            position_counts[position] += 1
    
    print(f"   QB: {position_counts['QB']}")
    print(f"   RB: {position_counts['RB']}")
    print(f"   WR: {position_counts['WR']}")
    print(f"   TE: {position_counts['TE']}")
    
    return active_skill_players

def map_player_data(player_id, sleeper_data):
    """Map Sleeper API data to our database schema"""
    player = sleeper_data
    
    # Basic mapping
    mapped = {
        'player_id': player_id,
        'first_name': player.get('first_name', ''),
        'last_name': player.get('last_name', ''),
        'full_name': player.get('full_name', ''),
        'position': player.get('position', ''),
        'team': player.get('team', ''),
        'height': player.get('height', ''),
        'weight': player.get('weight'),
        'age': player.get('age'),
        'college': player.get('college', ''),
        'status': player.get('status', ''),
        'injury_status': player.get('injury_status', ''),
        'injury_notes': player.get('injury_notes', ''),
        'active': 1 if player.get('active') else 0,
        'years_exp': player.get('years_exp'),
        'jersey_number': player.get('number'),
        'birth_date': player.get('birth_date', ''),
        'high_school': player.get('high_school', ''),
        'depth_chart_position': player.get('depth_chart_position', ''),
        'practice_description': player.get('practice_description', ''),
        'team_abbr': player.get('team_abbr', ''),
        'sportradar_id': player.get('sportradar_id', ''),
        'stats_id': player.get('stats_id'),
        'fantasy_data_id': player.get('fantasy_data_id'),
        'gsis_id': player.get('gsis_id', ''),
    }
    
    # Handle JSON fields
    fantasy_positions = player.get('fantasy_positions', [])
    mapped['fantasy_positions'] = json.dumps(fantasy_positions) if fantasy_positions else None
    
    stats = player.get('stats', {})
    mapped['stats'] = json.dumps(stats) if stats else None
    
    metadata = player.get('metadata', {})
    mapped['metadata'] = json.dumps(metadata) if metadata else None
    
    # External IDs
    mapped['espn_id'] = player.get('espn_id', '')
    mapped['yahoo_id'] = player.get('yahoo_id', '')
    mapped['rotowire_id'] = player.get('rotowire_id')
    
    # Search optimization fields
    mapped['search_full_name'] = player.get('full_name', '').lower()
    mapped['search_first_name'] = player.get('first_name', '').lower()
    mapped['search_last_name'] = player.get('last_name', '').lower()
    
    # Timestamps
    now = datetime.now().isoformat()
    mapped['created_at'] = now
    mapped['updated_at'] = now
    
    return mapped

def import_players(conn, players_data):
    """Import filtered players into database"""
    print("🚀 Importing players to database...")
    
    cursor = conn.cursor()
    imported_count = 0
    skipped_count = 0
    
    for player_id, sleeper_data in players_data:
        try:
            # Map data
            player = map_player_data(player_id, sleeper_data)
            
            # Check if player already exists
            cursor.execute('SELECT player_id FROM players WHERE player_id = ?', (player_id,))
            exists = cursor.fetchone()
            
            if exists:
                # Update existing player
                set_clause = ', '.join([f'{key} = ?' for key in player.keys()])
                values = list(player.values()) + [player_id]
                cursor.execute(f'UPDATE players SET {set_clause} WHERE player_id = ?', values)
                skipped_count += 1
            else:
                # Insert new player
                columns = ', '.join(player.keys())
                placeholders = ', '.join(['?' for _ in player])
                values = list(player.values())
                cursor.execute(f'INSERT INTO players ({columns}) VALUES ({placeholders})', values)
                imported_count += 1
            
            # Commit every 100 records
            if (imported_count + skipped_count) % 100 == 0:
                conn.commit()
                
        except Exception as e:
            print(f"❌ Error importing player {player_id}: {e}")
            conn.rollback()
            continue
    
    # Final commit
    conn.commit()
    
    print(f"\n🎯 Import complete!")
    print(f"✅ New players imported: {imported_count}")
    print(f"✅ Existing players updated: {skipped_count}")
    print(f"📊 Total players in database: {imported_count + skipped_count}")
    
    return imported_count + skipped_count

def verify_import(conn):
    """Verify the import was successful"""
    print("\n🔍 Verifying import...")
    
    cursor = conn.cursor()
    
    # Count total players
    cursor.execute('SELECT COUNT(*) FROM players')
    total = cursor.fetchone()[0]
    
    # Count by position
    cursor.execute('SELECT position, COUNT(*) FROM players GROUP BY position ORDER BY position')
    position_counts = cursor.fetchall()
    
    # Count active players
    cursor.execute('SELECT COUNT(*) FROM players WHERE active = 1')
    active_count = cursor.fetchone()[0]
    
    print(f"📊 Verification Results:")
    print(f"   Total players: {total}")
    print(f"   Active players: {active_count}")
    
    for position, count in position_counts:
        print(f"   {position}: {count}")
    
    # Sample some players
    cursor.execute('SELECT full_name, position, team FROM players LIMIT 5')
    samples = cursor.fetchall()
    
    print(f"\n🎯 Sample players:")
    for name, position, team in samples:
        print(f"   {name} ({position} - {team})")
    
    return total

def add_adp_data(conn):
    """Add ADP data for top players (mock data for now)"""
    print("\n📈 Adding ADP data for top players...")
    
    # Top 50 ADP data (mock - would come from external API)
    top_adp_players = {
        # Top 10
        "4034": 1.2,   # Christian McCaffrey
        "7248": 1.9,   # Bijan Robinson
        "4038": 2.1,   # Justin Jefferson
        "6797": 1.4,   # Ja'Marr Chase
        "6795": 4.2,   # Jonathan Taylor
        "7247": 5.1,   # Tyreek Hill
        "4039": 6.3,   # Austin Ekeler
        "4040": 8.1,   # Derrick Henry
        "6796": 9.0,   # Josh Allen
        "4046": 10.2,  # Patrick Mahomes
        
        # Next 40 (sample)
        "7244": 11.5,  # Jalen Hurts
        "6798": 13.6,  # Mark Andrews
        "7249": 14.3,  # Sam LaPorta
        "4042": 15.7,  # Stefon Diggs
        "6799": 16.4,  # CeeDee Lamb
        "7250": 17.2,  # Garrett Wilson
        "4043": 18.5,  # Davante Adams
        "6800": 19.3,  # A.J. Brown
        "7251": 20.1,  # Chris Olave
        "4044": 21.4,  # Travis Kelce
    }
    
    cursor = conn.cursor()
    updated_count = 0
    
    for player_id, adp in top_adp_players.items():
        try:
            cursor.execute('''
                UPDATE players 
                SET average_draft_position = ?, 
                    external_adp = ?,
                    external_adp_source = 'Mock Data',
                    external_adp_updated_at = ?
                WHERE player_id = ?
            ''', (adp, adp, datetime.now().isoformat(), player_id))
            
            if cursor.rowcount > 0:
                updated_count += 1
                
        except Exception as e:
            print(f"❌ Error updating ADP for player {player_id}: {e}")
    
    conn.commit()
    print(f"✅ Updated ADP for {updated_count} top players")
    
    return updated_count

def main():
    """Main execution function"""
    print("=" * 60)
    print("OPTION C: COMPLETE PLAYER POPULATION FOUNDATION")
    print("=" * 60)
    print("Goal: Establish complete player database foundation")
    print("Target: 679 active skill position players from Sleeper")
    print("=" * 60)
    
    # Step 1: Initialize database
    conn = initialize_database()
    if not conn:
        return
    
    # Step 2: Load Sleeper data
    sleeper_data = load_sleeper_data()
    if not sleeper_data:
        conn.close()
        return
    
    # Step 3: Filter active skill players
    active_players = filter_active_skill_players(sleeper_data)
    if not active_players:
        print("❌ No active skill players found!")
        conn.close()
        return
    
    # Step 4: Import players
    total_imported = import_players(conn, active_players)
    
    # Step 5: Add ADP data
    adp_updated = add_adp_data(conn)
    
    # Step 6: Verify import
    verify_import(conn)
    
    # Step 7: Summary
    print("\n" + "=" * 60)
    print("🎯 OPTION C COMPLETE - PLAYER FOUNDATION ESTABLISHED")
    print("=" * 60)
    print(f"✅ Database: bot_sports.db")
    print(f"✅ Players imported: {total_imported}")
    print(f"✅ ADP data added: {adp_updated} top players")
    print(f"✅ Foundation ready for fantasy operations")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Test API endpoints with complete player data")
    print("2. Implement player search and filtering")
    print("3. Add stats integration for current season")
    print("4. Build draft system on top of player foundation")
    
    conn.close()

if __name__ == "__main__":
    main()