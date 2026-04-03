#!/usr/bin/env python3
"""
Add domain column to memories table and backfill domain tags for all 364 memories.

Usage:
    python3 add_domain_column.py

Domains:
- architecture — system design, infrastructure, technical decisions
- trade — dynasty trades, player values, fantasy strategy
- memory-system — memory architecture, hooks, retrieval
- agent-ops — team coordination, delegation, Scout/Hermes/Iris
- project — DynastyDroid platform, specific features
- episodic — daily logs, personal notes
"""

import os
import sys

from dotenv import load_dotenv
load_dotenv(os.path.expanduser('~/.openclaw/.env'))

import psycopg2

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://dynastydroid_user:BKJZCv57P3sYpi5RGL3ciU9CylXsFRWv@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid"
)

DOMAIN_TRIGGERS = {
    'architecture': ['build', 'design', 'implement', 'create', 'setup', 'architect', 'system', 'infrastructure', 'deploy', 'render', 'postgres', 'database', 'api', 'endpoint', 'server', 'config'],
    'trade': ['trade', 'accept', 'reject', 'offer', 'value', 'dynasty', 'roster', 'draft', 'player', 'fantasy', 'superflex', 'ktc', 'pick', 'sf'],
    'memory-system': ['memory', 'recall', 'pgvector', 'hook', 'embed', 'retrieve', 'cognitive', 'store', 'vector', 'embedding'],
    'agent-ops': ['scout', 'hermes', 'iris', 'team', 'delegate', 'agent', 'subagent', 'orchestrator', 'blackboard'],
    'project': ['dynastydroid', 'moltbook', 'platform', 'feature', 'ui', 'frontend', 'dashboard', 'trade-calculator', 'draft'],
    'episodic': ['log', 'checkin', 'daily', 'standup', 'note', 'journal', 'reflection', 'yesterday', 'today', 'blocker'],
}


def get_connection():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn


def add_domain_column():
    """Add domain column to memories table"""
    conn = get_connection()
    cur = conn.cursor()
    
    print("Adding domain column to memories table...")
    cur.execute("""
        ALTER TABLE memories ADD COLUMN IF NOT EXISTS domain VARCHAR(50);
    """)
    print("✓ Domain column added")
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_memories_domain ON memories(domain);
    """)
    print("✓ Domain index created")
    
    cur.close()
    conn.close()


def detect_domain(content: str) -> str:
    """Detect domain from content using trigger keywords"""
    content_lower = content.lower()
    
    scores = {}
    for domain, triggers in DOMAIN_TRIGGERS.items():
        score = sum(1 for t in triggers if t in content_lower)
        scores[domain] = score
    
    if max(scores.values()) > 0:
        return max(scores, key=scores.get)
    return 'episodic'  # default


def backfill_domains():
    """Backfill domain tags for all memories"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Get all memories
    cur.execute("SELECT id, content FROM memories WHERE domain IS NULL")
    memories = cur.fetchall()
    
    print(f"\nBackfilling {len(memories)} memories...")
    
    updated = 0
    for memory_id, content in memories:
        domain = detect_domain(content or '')
        cur.execute(
            "UPDATE memories SET domain = %s WHERE id = %s",
            (domain, memory_id)
        )
        updated += 1
        if updated % 50 == 0:
            print(f"  Updated {updated}/{len(memories)}...")
    
    print(f"✓ Backfilled {updated} memories")
    
    # Print distribution
    cur.execute("SELECT domain, COUNT(*) FROM memories GROUP BY domain ORDER BY COUNT(*) DESC")
    print("\nDomain distribution:")
    for domain, count in cur.fetchall():
        print(f"  {domain}: {count}")
    
    cur.close()
    conn.close()


def main():
    print("=" * 60)
    print("Memory Domain Tagging - Add Column + Backfill")
    print("=" * 60)
    
    add_domain_column()
    backfill_domains()
    
    print("\n✅ Domain tagging complete!")


if __name__ == "__main__":
    main()