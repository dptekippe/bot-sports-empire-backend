#!/usr/bin/env python3
"""
Backfill script: Migrate agent_memories to memories table.

This script copies the 67 rows from agent_memories (old schema) to memories (new schema)
to ensure historical data is available to pgvector-memory hooks.

Usage:
    python3 backfill_memories.py
"""

import os
import sys

# Load .env FIRST before reading any env vars
from dotenv import load_dotenv
load_dotenv(os.path.expanduser('~/.openclaw/.env'))

import psycopg2
from datetime import datetime

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://dynastydroid_user:BKJZCv57P3sYpi5RGL3ciU9CylXsFRWv@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid"
)

def get_connection():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn

def count_rows(table_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count

def get_agent_memories():
    """Fetch all rows from agent_memories"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT content, source_type, namespace, importance, tags, timestamp
        FROM agent_memories
        WHERE is_deleted = FALSE
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def insert_into_memories(rows):
    """Insert rows into memories table"""
    conn = get_connection()
    cur = conn.cursor()
    
    migrated = 0
    skipped = 0
    
    for row in rows:
        content, source_type, namespace, importance, tags, timestamp = row
        
        # Map to memories schema
        memory_type = namespace if namespace in ('fact', 'procedure', 'instruction', 'experience', 'preference', 'general') else 'general'
        project_val = 'default'  # agent_memories doesn't have project
        tags_val = tags if tags else []
        importance_val = float(importance) if importance else 5.0
        created_at_ts = int(timestamp.timestamp()) if timestamp else int(datetime.now().timestamp())
        created_at_val = timestamp if timestamp else datetime.now()
        
        try:
            cur.execute("""
                INSERT INTO memories (content, memory_type, tags, importance, project, sensitivity, created_at_ts, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (content, memory_type, tags_val, importance_val, project_val, 'internal', created_at_ts, created_at_val))
            
            result = cur.fetchone()
            if result:
                migrated += 1
                print(f"✓ Migrated: {content[:50]}...")
            else:
                skipped += 1
                
        except Exception as e:
            skipped += 1
            print(f"⚠️  Skipped (error): {content[:50]}... - {str(e)[:50]}")
    
    cur.close()
    conn.close()
    return migrated, skipped

def main():
    print("=" * 60)
    print("Memory Backfill Script - agent_memories → memories")
    print("=" * 60)
    
    # Count before
    agent_count = count_rows('agent_memories')
    memories_count = count_rows('memories')
    
    print(f"\nBefore migration:")
    print(f"  agent_memories: {agent_count} rows")
    print(f"  memories: {memories_count} rows")
    
    # Fetch rows from agent_memories
    print(f"\nFetching rows from agent_memories...")
    rows = get_agent_memories()
    print(f"  Found {len(rows)} rows to migrate")
    
    if not rows:
        print("\nNo rows to migrate. Exiting.")
        return
    
    # Insert into memories
    print(f"\nMigrating to memories table...")
    migrated, skipped = insert_into_memories(rows)
    
    # Count after
    memories_count_after = count_rows('memories')
    
    print(f"\nAfter migration:")
    print(f"  memories: {memories_count_after} rows (was {memories_count})")
    print(f"\nMigration complete:")
    print(f"  ✓ Migrated: {migrated}")
    print(f"  ⚠️  Skipped: {skipped}")

if __name__ == "__main__":
    main()
