#!/usr/bin/env python3
"""
Load trades to MEMO database without embeddings.
Use this when OpenAI/MiniMax API is not available.
"""
import json
import psycopg2
import uuid
import sys
from datetime import datetime

DATABASE_URL = "postgresql://dynastydroid_user:BKJZCv57P3sYpi5RGL3ciU9CylXsFRWv@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid?sslmode=require"

def load_trade(conn, trade_path):
    """Load a single trade JSON to the database."""
    with open(trade_path, 'r') as f:
        trade = json.load(f)
    
    cur = conn.cursor()
    
    # Get game_id for fantasy_football
    cur.execute("SELECT id FROM games WHERE game_type = 'fantasy_football' LIMIT 1")
    game_row = cur.fetchone()
    if game_row:
        game_id = game_row[0]
    else:
        # Create game if not exists
        game_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO games (id, game_type, name, metadata) VALUES (%s, %s, %s, %s)",
            (game_id, 'fantasy_football', 'Fantasy Football', json.dumps({"scoring": "PPR"}))
        )
    
    # Check if trajectory already exists
    cur.execute("SELECT id FROM trajectories WHERE external_id = %s", (trade['trade_id'],))
    if cur.fetchone():
        print(f"  ⏭️  Already exists: {trade['trade_id']}")
        return False
    
    # Create trajectory
    trajectory_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO trajectories (id, game_id, metadata, trajectory_type, external_id)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        trajectory_id,
        game_id,
        json.dumps(trade.get('context', {})),
        'trade',
        trade['trade_id']
    ))
    
    # Create trajectory states and insights
    for step in trade.get('steps', []):
        state_id = str(uuid.uuid4())
        
        # Create state
        team_a_assets = step.get('team_a_offers', [])
        team_b_assets = step.get('team_b_offers', [])
        
        state_data = {
            'team_a_offers': team_a_assets,
            'team_b_offers': team_b_assets,
            'team_a_total': step.get('team_a_total_value', 0),
            'team_b_total': step.get('team_b_total_value', 0)
        }
        
        cur.execute("""
            INSERT INTO trajectory_states (id, trajectory_id, step_number, state_data, state_type, outcome, value_difference)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            state_id,
            trajectory_id,
            step.get('step', 1),
            json.dumps(state_data),
            'trade_offer',
            step.get('outcome'),
            step.get('value_difference', 0)
        ))
        
        # Create insight
        insight_id = str(uuid.uuid4())
        reasoning = step.get('reasoning', '')
        outcome = step.get('outcome', '')
        
        # Generate insight text
        a_names = [a.get('player', a.get('pick', 'Unknown')) for a in team_a_assets]
        b_names = [b.get('player', b.get('pick', 'Unknown')) for b in team_b_assets]
        
        insight_text = f"Trade Step {step.get('step', 1)}: Team A {a_names} vs Team B {b_names}. Outcome: {outcome}. {reasoning}"
        
        cur.execute("""
            INSERT INTO insights (id, trajectory_id, text, outcome, score, status, game_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            insight_id,
            trajectory_id,
            insight_text,
            outcome,
            step.get('value_difference', 0) / 1000 if step.get('value_difference') else 0,
            'active',
            'fantasy_football'
        ))
        
        print(f"  ✅ {trade['trade_id']} - Step {step.get('step', 1)}: {outcome}")
    
    return True

def main():
    conn = psycopg2.connect(DATABASE_URL)
    
    # Get all trade files from trades directory
    import os
    trades_dir = os.path.join(os.path.dirname(__file__), 'trades')
    
    trade_files = sorted([f for f in os.listdir(trades_dir) if f.endswith('.json')])
    
    print(f"Found {len(trade_files)} trade files")
    print()
    
    loaded = 0
    skipped = 0
    for tf in trade_files:
        trade_path = os.path.join(trades_dir, tf)
        try:
            if load_trade(conn, trade_path):
                loaded += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  ❌ Error: {e}")
            skipped += 1
    
    conn.commit()
    conn.close()
    
    print()
    print(f"Done! Loaded: {loaded}, Skipped: {skipped}")

if __name__ == "__main__":
    main()
