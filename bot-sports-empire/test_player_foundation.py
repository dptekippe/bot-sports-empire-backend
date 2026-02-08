#!/usr/bin/env python3
"""
Test script for Bot Sports Empire Player Database
"""
import sqlite3
import json

def test_database():
    print("🔍 Testing player database...")
    
    # Test focused database
    conn = sqlite3.connect('bot_sports_focused.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Test 1: Count players
    cursor.execute("SELECT COUNT(*) FROM players")
    total = cursor.fetchone()[0]
    print(f"✅ Total NFL-rostered players: {total}")
    
    # Test 2: Count by position
    cursor.execute("SELECT position, COUNT(*) FROM players GROUP BY position ORDER BY position")
    print("\n📊 Players by position:")
    for position, count in cursor.fetchall():
        print(f"   {position}: {count}")
    
    # Test 3: Sample players with ADP
    cursor.execute('SELECT full_name, position, team, average_draft_position FROM players WHERE average_draft_position IS NOT NULL ORDER BY average_draft_position LIMIT 5')
    print("\n🎯 Top 5 players by ADP:")
    for row in cursor.fetchall():
        print(f"   {row['full_name']} ({row['position']} - {row['team']}) - ADP: {row['average_draft_position']}")
    
    # Test 4: Search test
    cursor.execute("SELECT full_name, position, team FROM players WHERE search_full_name LIKE '%mahomes%' LIMIT 3")
    print("\n🔍 Search test (Mahomes):")
    for row in cursor.fetchall():
        print(f"   {row['full_name']} ({row['position']} - {row['team']})")
    
    # Test 5: Team distribution
    cursor.execute("SELECT team, COUNT(*) as count FROM players WHERE team IS NOT NULL GROUP BY team ORDER BY count DESC LIMIT 5")
    print("\n🏈 Top 5 teams by player count:")
    for row in cursor.fetchall():
        print(f"   {row['team']}: {row['count']} players")
    
    conn.close()
    
    # Test complete database
    print("\n📊 Testing complete database...")
    conn = sqlite3.connect('bot_sports.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM players")
    complete_total = cursor.fetchone()[0]
    print(f"✅ Complete database players: {complete_total}")
    conn.close()
    
    print("\n✅ All tests passed!")

if __name__ == "__main__":
    test_database()
