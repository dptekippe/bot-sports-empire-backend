#!/usr/bin/env python3
"""
Verify Sleeper player import to Render PostgreSQL database.
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json

# Database connection from Render
DATABASE_URL = "postgresql://bots_sports_empire_db_user:aO5wZt9RCxzo33s4hnskiVAw6DOexWI6@dpg-d61sf615pdvs73f4g1ug-a.virginia-postgres.render.com/bots_sports_empire_db"

def verify_import():
    """Verify player import to database."""
    print("🔍 VERIFYING SLEEPER PLAYER IMPORT")
    print("=" * 50)
    
    try:
        # Connect to database
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("✅ Connected to Render PostgreSQL database")
        
        # Check total players
        cursor.execute("SELECT COUNT(*) as count FROM players")
        total_players = cursor.fetchone()['count']
        print(f"📊 Total players in database: {total_players}")
        
        # Check player breakdown
        cursor.execute("""
            SELECT position, COUNT(*) as count 
            FROM players 
            WHERE status = 'Active' 
            AND position IN ('QB', 'RB', 'WR', 'TE')
            GROUP BY position 
            ORDER BY position
        """)
        
        print("\n🏈 ACTIVE SKILL POSITION PLAYERS:")
        active_counts = {}
        for row in cursor.fetchall():
            position = row['position']
            count = row['count']
            active_counts[position] = count
            print(f"  {position}: {count} players")
        
        total_active = sum(active_counts.values())
        print(f"  TOTAL: {total_active} active players")
        
        # Check sample players
        print("\n🔍 SAMPLE PLAYERS (first 5):")
        cursor.execute("""
            SELECT player_id, full_name, position, team, status 
            FROM players 
            WHERE status = 'Active'
            LIMIT 5
        """)
        
        for row in cursor.fetchall():
            print(f"  - {row['full_name']} ({row['position']} - {row['team']})")
        
        # Check if we have the original 4 sample players
        print("\n🎯 ORIGINAL SAMPLE PLAYERS CHECK:")
        original_players = ['Patrick Mahomes', 'Christian McCaffrey', 'Justin Jefferson', 'Travis Kelce']
        for name in original_players:
            cursor.execute("SELECT COUNT(*) as count FROM players WHERE full_name = %s", (name,))
            count = cursor.fetchone()['count']
            status = "✅ PRESENT" if count > 0 else "❌ MISSING"
            print(f"  {name}: {status}")
        
        # Data quality check
        print("\n📈 DATA QUALITY METRICS:")
        
        # Check for null critical fields
        cursor.execute("SELECT COUNT(*) as count FROM players WHERE full_name IS NULL")
        null_names = cursor.fetchone()['count']
        print(f"  Players without name: {null_names}")
        
        cursor.execute("SELECT COUNT(*) as count FROM players WHERE position IS NULL")
        null_positions = cursor.fetchone()['count']
        print(f"  Players without position: {null_positions}")
        
        cursor.execute("SELECT COUNT(*) as count FROM players WHERE team IS NULL")
        null_teams = cursor.fetchone()['count']
        print(f"  Players without team: {null_teams}")
        
        # Close connection
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 50)
        
        # Summary
        if total_players >= 679:
            print("✅ IMPORT SUCCESS: Database has real player data!")
            print(f"   Ready for: Mock drafts, PlayerEvaluationService, Bot AI")
        else:
            print("⚠️  IMPORT INCOMPLETE: Need to investigate")
            
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    verify_import()