#!/usr/bin/env python3
"""
Embedding agent for DynastyDroid MEMO pipeline.
Loads trade JSON, generates OpenAI embeddings, stores in pgvector.
"""

import os
import sys
import json
import argparse
from uuid import uuid4
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("❌ openai package not installed. Run: pip install openai")
    sys.exit(1)

try:
    import psycopg2
except ImportError:
    print("❌ psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

# Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://dynastydroid_user:BKJZCv57P3sYpi5RGL3ciU9CylXsFRWv@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid"
)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = 1536  # text-embedding-3-small default

def get_openai_client():
    """Get OpenAI client with API key from environment."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set in environment")
    return OpenAI(api_key=api_key)

def load_trade(trade_path: str) -> dict:
    """Load trade JSON file."""
    with open(trade_path, 'r') as f:
        return json.load(f)

def generate_embedding(client: OpenAI, text: str) -> list:
    """Generate embedding for text using OpenAI API."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding

def get_insights_without_embeddings(conn, trajectory_id: str = None) -> list:
    """Get insights that don't have embeddings yet, optionally filtered by trajectory."""
    cur = conn.cursor()
    if trajectory_id:
        cur.execute("""
            SELECT i.id, i.text, i.trajectory_id
            FROM insights i
            LEFT JOIN insight_embeddings ie ON i.id = ie.insight_id
            WHERE ie.id IS NULL
            AND i.status = 'active'
            AND i.trajectory_id = %s
        """, (trajectory_id,))
    else:
        cur.execute("""
            SELECT i.id, i.text, i.trajectory_id
            FROM insights i
            LEFT JOIN insight_embeddings ie ON i.id = ie.insight_id
            WHERE ie.id IS NULL
            AND i.status = 'active'
        """)
    results = cur.fetchall()
    cur.close()
    return [{"id": r[0], "text": r[1], "trajectory_id": r[2]} for r in results]

def load_trade_to_db(conn, trade: dict) -> str:
    """Load trade JSON into database. Returns trajectory_id."""
    cur = conn.cursor()
    
    # Check if trajectory already exists
    cur.execute("SELECT id FROM trajectories WHERE external_id = %s", (trade['trade_id'],))
    existing = cur.fetchone()
    if existing:
        print(f"   Trade {trade['trade_id']} already exists, skipping insert")
        cur.close()
        return existing[0]
    
    # Get or create game
    game_type = trade.get('context', {}).get('league_type', 'fantasy_football')
    cur.execute("""
        INSERT INTO games (id, game_type, name, config)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (game_type, name) DO UPDATE SET config = EXCLUDED.config
        RETURNING id
    """, (str(uuid4()), game_type, 'DynastyDroid', json.dumps({"scoring": "PPR"})))
    game_id = cur.fetchone()[0]
    
    # Create trajectory
    traj_id = str(uuid4())
    cur.execute("""
        INSERT INTO trajectories (id, game_id, trajectory_type, external_id, metadata)
        VALUES (%s, %s, %s, %s, %s)
    """, (traj_id, game_id, 'trade', trade['trade_id'], json.dumps(trade.get('context', {}))))
    
    # Create states and insights
    for step in trade['steps']:
        state_id = str(uuid4())
        cur.execute("""
            INSERT INTO trajectory_states (id, trajectory_id, step_number, state_type, state_data, outcome, value_difference)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (state_id, traj_id, step['step'], 'trade_offer', json.dumps(step), step['outcome'], step['value_difference']))
        
        # Create insight
        insight_id = str(uuid4())
        def get_asset_name(p):
            if isinstance(p, dict):
                return p.get('player') or p.get('pick', str(p))
            return str(p)
        a_players = [get_asset_name(p) for p in step.get('team_a_offers', [])]
        b_players = [get_asset_name(p) for p in step.get('team_b_offers', [])]
        insight_text = f"Trade Step {step['step']}: Team A {a_players} vs Team B {b_players}. Outcome: {step['outcome']}. {step.get('reasoning', '')}"
        cur.execute("""
            INSERT INTO insights (id, trajectory_id, text, score, outcome, game_type)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (insight_id, traj_id, insight_text, abs(step['value_difference'])/1000, step['outcome'], game_type))
    
    conn.commit()
    cur.close()
    return traj_id

def insert_embedding(conn, insight_id: str, embedding: list, version: int, model: str):
    """Insert embedding into database."""
    cur = conn.cursor()
    emb_id = str(uuid4())
    # Convert list to string format for pgvector
    emb_str = "[" + ",".join([str(x) for x in embedding]) + "]"
    
    cur.execute("""
        INSERT INTO insight_embeddings (id, insight_id, embedding, embedding_version, embedding_model, created_at)
        VALUES (%s, %s, %s::vector, %s, %s, NOW())
    """, (emb_id, insight_id, emb_str, version, model))
    cur.close()
    conn.commit()

def run_pipeline(trade_path: str):
    """Run full embedding pipeline."""
    print(f"📦 Loading trade from {trade_path}...")
    trade = load_trade(trade_path)
    print(f"   Trade ID: {trade['trade_id']}")
    print(f"   Steps: {len(trade['steps'])}")
    
    # Connect to database
    print(f"\n🔌 Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    print("   ✅ Connected!")
    
    # Load trade into database
    print(f"\n📥 Loading trade to database...")
    traj_id = load_trade_to_db(conn, trade)
    print(f"   ✅ Trajectory: {traj_id[:8]}...")
    
    # Get OpenAI client
    print(f"\n🤖 Initializing OpenAI client ({EMBEDDING_MODEL})...")
    client = get_openai_client()
    print("   ✅ Client ready!")
    
    # Get insights without embeddings for this trajectory
    insights = get_insights_without_embeddings(conn, traj_id)
    print(f"\n📊 Insights needing embeddings: {len(insights)}")
    
    if len(insights) == 0:
        print("   All insights already have embeddings!")
    else:
        # Generate and insert embeddings
        version = 1  # First version of embeddings
        for i, insight in enumerate(insights, 1):
            print(f"\n   [{i}/{len(insights)}] Generating embedding for insight {insight['id'][:8]}...")
            try:
                embedding = generate_embedding(client, insight['text'])
                insert_embedding(conn, insight['id'], embedding, version, EMBEDDING_MODEL)
                print(f"   ✅ Stored! (dim={len(embedding)})")
            except Exception as e:
                print(f"   ❌ Error: {e}")
                continue
    
    # Verify
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM insight_embeddings")
    emb_count = cur.fetchone()[0]
    cur.execute("SELECT embedding FROM insight_embeddings LIMIT 1")
    sample = cur.fetchone()[0]
    cur.close()
    conn.close()
    
    print(f"\n✅ Pipeline complete!")
    print(f"   Total embeddings: {emb_count}")
    if sample:
        print(f"   Sample embedding dims: {len(sample)}")
    
    return True

def query_similar(query: str, top_k: int = 3):
    """Query for similar insights using cosine similarity."""
    print(f"\n🔍 Query: '{query}'")
    
    client = get_openai_client()
    conn = psycopg2.connect(DATABASE_URL)
    
    # Generate query embedding
    print("   Generating query embedding...")
    query_emb = generate_embedding(client, query)
    emb_str = "[" + ",".join([str(x) for x in query_emb]) + "]"
    
    # Search
    cur = conn.cursor()
    cur.execute("""
        SELECT i.id, i.text, i.score, i.outcome,
               1 - (ie.embedding <=> %s::vector) as cosine_sim
        FROM insights i
        JOIN insight_embeddings ie ON i.id = ie.insight_id
        WHERE i.status = 'active'
        ORDER BY ie.embedding <=> %s::vector
        LIMIT %s
    """, (emb_str, emb_str, top_k))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    print(f"\n📋 Top {top_k} results:")
    for r in results:
        print(f"\n   [{r[4]:.3f}] {r[3]}")
        print(f"   {r[1][:100]}...")
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MEMO Embedding Agent")
    parser.add_argument("--trades", type=str, help="Path to trade JSON file")
    parser.add_argument("--query", type=str, help="Query string to search")
    parser.add_argument("--top-k", type=int, default=3, help="Number of results")
    
    args = parser.parse_args()
    
    if args.trades:
        run_pipeline(args.trades)
    elif args.query:
        query_similar(args.query, args.top_k)
    else:
        parser.print_help()