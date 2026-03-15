#!/usr/bin/env python3
"""
Store 10 simulations in SQLite (local) + PostgreSQL-ready export
"""
import json
import sqlite3
from datetime import datetime

# Load simulation results
with open("simulation_results_10.json", "r") as f:
    data = json.load(f)

# Create SQLite database
conn = sqlite3.connect("simulations.db")
cur = conn.cursor()

# Create tables
cur.execute("""
CREATE TABLE IF NOT EXISTS simulation_runs (
    id INTEGER PRIMARY KEY,
    simulation_name TEXT,
    season_year INTEGER,
    created_at TEXT,
    total_teams INTEGER,
    rounds_drafted INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS draft_picks (
    id INTEGER PRIMARY KEY,
    simulation_run_id INTEGER,
    team_name TEXT,
    team_strategy TEXT,
    round_num INTEGER,
    pick_num INTEGER,
    player_name TEXT,
    player_position TEXT,
    player_team TEXT,
    adp_rank INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS final_standings (
    id INTEGER PRIMARY KEY,
    simulation_run_id INTEGER,
    team_name TEXT,
    team_strategy TEXT,
    regular_season_points REAL,
    final_rank INTEGER,
    playoff_finish TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS training_metadata (
    id INTEGER PRIMARY KEY,
    simulation_run_id INTEGER,
    key TEXT,
    value TEXT
)
""")

# Insert simulations
for sim in data["simulations"]:
    sim_id = sim["simulation_id"]
    
    # Insert simulation run
    cur.execute("""
        INSERT INTO simulation_runs (id, simulation_name, season_year, created_at, total_teams, rounds_drafted)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (sim_id, "2025_PPR_Draft_Sim", 2025, datetime.now().isoformat(), 12, 20))
    
    # Insert draft picks
    for team, roster in sim["draft"].items():
        strategy = sim.get("standings", [{}])[0].get("strategy", "")
        # Find strategy from standings
        for s in sim["standings"]:
            if s["team"] == team:
                strategy = s["strategy"]
                break
        
        for rnd, player in enumerate(roster, 1):
            cur.execute("""
                INSERT INTO draft_picks (simulation_run_id, team_name, team_strategy, round_num, pick_num, player_name, player_position, player_team, adp_rank)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (sim_id, team, strategy, rnd, rnd * 12 - 11 + list(sim["draft"].keys()).index(team), player["name"], player["pos"], player["team"], player["adp"]))
    
    # Insert standings
    for standing in sim["standings"]:
        playoff_finish = "CHAMPION" if standing["rank"] == 1 else ("Semifinals" if standing["rank"] <= 2 else ("Quarterfinals" if standing["rank"] <= 4 else "Did not make playoffs"))
        cur.execute("""
            INSERT INTO final_standings (simulation_run_id, team_name, team_strategy, regular_season_points, final_rank, playoff_finish)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sim_id, standing["team"], standing["strategy"], standing["points"], standing["rank"], playoff_finish))

# Insert metadata
metadata = [
    ("scoring_format", "PPR"),
    ("league_size", "12 teams"),
    ("roster_positions", "1 QB, 2 RB, 3 WR, 1 TE, 1 FLEX"),
    ("draft_type", "Snake"),
    ("regular_season_weeks", "14"),
    ("playoff_weeks", "3 (15-17)"),
    ("data_source_adp", "FantasyPros 2025 PPR Consensus"),
    ("data_source_stats", "FantasyPros 2025 Season Totals"),
]
for key, value in metadata:
    cur.execute("""
        INSERT INTO training_metadata (simulation_run_id, key, value)
        VALUES (?, ?, ?)
    """, (1, key, value))

conn.commit()

# Verify counts
cur.execute("SELECT COUNT(*) FROM simulation_runs")
print(f"Simulation runs: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM draft_picks")
print(f"Draft picks: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM final_standings")
print(f"Standings: {cur.fetchone()[0]}")

conn.close()

print("\n✅ Stored in SQLite: simulations.db")
print("\nTo export to PostgreSQL, run:")
print("  sqlite3 simulations.db .dump > simulations.sql")
print("  # Then import into Render PostgreSQL")
