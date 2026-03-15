#!/usr/bin/env python3
"""
Store 2025 Draft Simulation in PostgreSQL
Run this script to insert the simulation data into Render PostgreSQL
"""
import os
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

# Get DATABASE_URL from environment (set this for Render)
DATABASE_URL = os.getenv("DATABASE_URL")

# Full draft data for all 12 teams (first 5 picks each)
DRAFT_DATA = [
    # Team, Strategy, Round, Pick, Player, Pos, Team, ADP
    ("Best Player", "Take best available always", 1, 1, "Ja'Marr Chase", "WR", "CIN", 1),
    ("Best Player", "Take best available always", 2, 24, "Bucky Irving", "RB", "TB", 24),
    ("Best Player", "Take best available always", 3, 25, "Kyren Williams", "RB", "LAR", 25),
    ("Best Player", "Take best available always", 4, 48, "DK Metcalf", "WR", "PIT", 48),
    ("Best Player", "Take best available always", 5, 49, "Patrick Mahomes", "QB", "KC", 49),
    
    ("Youth Movement", "Prioritize younger players", 1, 2, "Bijan Robinson", "RB", "ATL", 2),
    ("Youth Movement", "Prioritize younger players", 2, 23, "Lamar Jackson", "QB", "BAL", 23),
    ("Youth Movement", "Prioritize younger players", 3, 26, "Ladd McConkey", "WR", "LAC", 26),
    ("Youth Movement", "Prioritize younger players", 4, 47, "James Conner", "RB", "ARI", 47),
    ("Youth Movement", "Prioritize younger players", 5, 50, "DJ Moore", "WR", "BUF", 50),
    
    ("Zero RB", "Load up WR first 4 rounds", 1, 3, "Saquon Barkley", "RB", "PHI", 3),
    ("Zero RB", "Load up WR first 4 rounds", 2, 22, "Chase Brown", "RB", "CIN", 22),
    ("Zero RB", "Load up WR first 4 rounds", 3, 27, "Trey McBride", "TE", "ARI", 27),
    ("Zero RB", "Load up WR first 4 rounds", 4, 46, "Chuba Hubbard", "RB", "CAR", 46),
    ("Zero RB", "Load up WR first 4 rounds", 5, 51, "Courtland Sutton", "WR", "DEN", 51),
    
    ("PPR Specialist", "Target high-catch WRs", 1, 4, "Jahmyr Gibbs", "RB", "DET", 4),
    ("PPR Specialist", "Target high-catch WRs", 2, 21, "A.J. Brown", "WR", "PHI", 21),
    ("PPR Specialist", "Target high-catch WRs", 3, 28, "James Cook III", "RB", "BUF", 28),
    ("PPR Specialist", "Target high-catch WRs", 4, 45, "TreVeyon Henderson", "RB", "NE", 45),
    ("PPR Specialist", "Target high-catch WRs", 5, 52, "Sam LaPorta", "TE", "DET", 52),
    
    ("Sleeper Hunter", "Target ADP sleepers", 1, 5, "CeeDee Lamb", "WR", "DAL", 5),
    ("Sleeper Hunter", "Target ADP sleepers", 2, 20, "Josh Allen", "QB", "BUF", 20),
    ("Sleeper Hunter", "Target ADP sleepers", 3, 29, "Jayden Daniels", "QB", "WAS", 29),
    ("Sleeper Hunter", "Target ADP sleepers", 4, 44, "Marvin Harrison Jr.", "WR", "ARI", 44),
    ("Sleeper Hunter", "Target ADP sleepers", 5, 53, "Xavier Worthy", "WR", "KC", 53),
    
    ("Veteran Hunter", "Prioritize proven veterans", 1, 6, "Justin Jefferson", "WR", "MIN", 6),
    ("Veteran Hunter", "Prioritize proven veterans", 2, 19, "Brock Bowers", "TE", "LV", 19),
    ("Veteran Hunter", "Prioritize proven veterans", 3, 30, "Tee Higgins", "WR", "CIN", 30),
    ("Veteran Hunter", "Prioritize proven veterans", 4, 43, "Kenneth Walker III", "RB", "KC", 43),
    ("Veteran Hunter", "Prioritize proven veterans", 5, 54, "D'Andre Swift", "RB", "CHI", 54),
    
    ("Safe Draft", "High floor players only", 1, 7, "Christian McCaffrey", "RB", "SF", 7),
    ("Safe Draft", "High floor players only", 2, 18, "Jonathan Taylor", "RB", "IND", 18),
    ("Safe Draft", "High floor players only", 3, 31, "Tyreek Hill", "WR", "MIA", 31),
    ("Safe Draft", "High floor players only", 4, 42, "Davante Adams", "WR", "LAR", 42),
    ("Safe Draft", "High floor players only", 5, 55, "DeVonta Smith", "WR", "PHI", 55),
    
    ("Elite QB", "Prioritize QB early (superflex)", 1, 8, "Malik Nabers", "WR", "NYG", 8),
    ("Elite QB", "Prioritize QB early (superflex)", 2, 17, "Drake London", "WR", "ATL", 17),
    ("Elite QB", "Prioritize QB early (superflex)", 3, 32, "Joe Burrow", "QB", "CIN", 32),
    ("Elite QB", "Prioritize QB early (superflex)", 4, 41, "Garrett Wilson", "WR", "NYJ", 41),
    ("Elite QB", "Prioritize QB early (superflex)", 5, 56, "Tetairoa McMillan", "WR", "CAR", 56),
    
    ("Value WR", "Wait on WR, target value picks", 1, 9, "Amon-Ra St. Brown", "WR", "DET", 9),
    ("Value WR", "Wait on WR, target value picks", 2, 16, "Josh Jacobs", "RB", "GB", 16),
    ("Value WR", "Wait on WR, target value picks", 3, 33, "Jaxon Smith-Njigba", "WR", "SEA", 33),
    ("Value WR", "Wait on WR, target value picks", 4, 40, "Mike Evans", "WR", "SF", 40),
    ("Value WR", "Wait on WR, target value picks", 5, 57, "Jameson Williams", "WR", "DET", 57),
    
    ("Roger (Balanced)", "Follow ADP strictly, balanced RB/WR/TE", 1, 10, "Derrick Henry", "RB", "BAL", 10),
    ("Roger (Balanced)", "Follow ADP strictly, balanced RB/WR/TE", 2, 15, "Brian Thomas Jr.", "WR", "JAC", 15),
    ("Roger (Balanced)", "Follow ADP strictly, balanced RB/WR/TE", 3, 34, "Jalen Hurts", "QB", "PHI", 34),
    ("Roger (Balanced)", "Follow ADP strictly, balanced RB/WR/TE", 4, 39, "Terry McLaurin", "WR", "WAS", 39),
    ("Roger (Balanced)", "Follow ADP strictly, balanced RB/WR/TE", 5, 58, "David Montgomery", "RB", "HOU", 58),
    
    ("Hero RB", "First 2 picks RB, then value", 1, 11, "Ashton Jeanty", "RB", "LV", 11),
    ("Hero RB", "First 2 picks RB, then value", 2, 14, "De'Von Achane", "RB", "MIA", 14),
    ("Hero RB", "First 2 picks RB, then value", 3, 35, "Omarion Hampton", "RB", "LAC", 35),
    ("Hero RB", "First 2 picks RB, then value", 4, 38, "Breece Hall", "RB", "NYJ", 38),
    ("Hero RB", "First 2 picks RB, then value", 5, 59, "RJ Harvey", "RB", "DEN", 59),
    
    ("Risk Taker", "High variance, high ceiling", 1, 12, "Puka Nacua", "WR", "LAR", 12),
    ("Risk Taker", "High variance, high ceiling", 2, 13, "Nico Collins", "WR", "HOU", 13),
    ("Risk Taker", "High variance, high ceiling", 3, 36, "Alvin Kamara", "RB", "NO", 36),
    ("Risk Taker", "High variance, high ceiling", 4, 37, "George Kittle", "TE", "SF", 37),
    ("Risk Taker", "High variance, high ceiling", 5, 60, "Isiah Pacheco", "RB", "DET", 60),
]

# Final standings data
STANDINGS_DATA = [
    ("Safe Draft", "High floor players only", 1002.9, 1, "Did not make playoffs"),
    ("Value WR", "Wait on WR, target value picks", 978.4, 2, "CHAMPION"),
    ("Zero RB", "Load up WR first 4 rounds", 879.5, 3, "Semifinals"),
    ("PPR Specialist", "Target high-catch WRs", 826.1, 4, "Semifinals"),
    ("Best Player", "Take best available always", 809.9, 5, "Quarterfinals"),
    ("Veteran Hunter", "Prioritize proven veterans", 719.4, 6, "Quarterfinals"),
    ("Risk Taker", "High variance, high ceiling", 618.5, 7, "Did not make playoffs"),
    ("Roger (Balanced)", "Follow ADP strictly, balanced RB/WR/TE", 605.4, 8, "Did not make playoffs"),
    ("Sleeper Hunter", "Target ADP sleepers", 595.5, 9, "Did not make playoffs"),
    ("Hero RB", "First 2 picks RB, then value", 592.5, 10, "Did not make playoffs"),
    ("Youth Movement", "Prioritize younger players", 467.8, 11, "Did not make playoffs"),
    ("Elite QB", "Prioritize QB early (superflex)", 459.9, 12, "Did not make playoffs"),
]

def create_tables(conn):
    """Create the simulation tables"""
    with conn.cursor() as cur:
        # Simulation runs table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS simulation_runs (
                id SERIAL PRIMARY KEY,
                simulation_name VARCHAR(100) DEFAULT '2025_PPR_Draft_Sim',
                season_year INTEGER DEFAULT 2025,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_teams INTEGER DEFAULT 12,
                rounds_drafted INTEGER DEFAULT 20
            )
        """)
        
        # Draft picks table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS draft_picks (
                id SERIAL PRIMARY KEY,
                simulation_run_id INTEGER REFERENCES simulation_runs(id),
                team_name VARCHAR(100),
                team_strategy VARCHAR(255),
                round_num INTEGER,
                pick_num INTEGER,
                player_name VARCHAR(100),
                player_position VARCHAR(10),
                player_team VARCHAR(10),
                adp_rank INTEGER
            )
        """)
        
        # Weekly scores table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS weekly_scores (
                id SERIAL PRIMARY KEY,
                simulation_run_id INTEGER REFERENCES simulation_runs(id),
                team_name VARCHAR(100),
                week_num INTEGER,
                points_scored DECIMAL(10,2)
            )
        """)
        
        # Final standings table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS final_standings (
                id SERIAL PRIMARY KEY,
                simulation_run_id INTEGER REFERENCES simulation_runs(id),
                team_name VARCHAR(100),
                team_strategy VARCHAR(255),
                regular_season_points DECIMAL(10,2),
                final_rank INTEGER,
                playoff_finish VARCHAR(50)
            )
        """)
        
        # Training metadata table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS training_metadata (
                id SERIAL PRIMARY KEY,
                simulation_run_id INTEGER REFERENCES simulation_runs(id),
                key VARCHAR(100),
                value TEXT
            )
        """)
        
        conn.commit()
        print("Tables created successfully!")

def insert_data(conn):
    """Insert simulation data"""
    with conn.cursor() as cur:
        # Insert simulation run
        cur.execute("""
            INSERT INTO simulation_runs (simulation_name, season_year, total_teams, rounds_drafted)
            VALUES ('2025_PPR_Draft_Sim', 2025, 12, 20)
            RETURNING id
        """)
        sim_id = cur.fetchone()[0]
        print(f"Created simulation run with ID: {sim_id}")
        
        # Insert draft picks
        draft_values = [
            (sim_id, team, strategy, rnd, pick, player, pos, team_code, adp)
            for team, strategy, rnd, pick, player, pos, team_code, adp in DRAFT_DATA
        ]
        execute_values(
            cur,
            """INSERT INTO draft_picks 
               (simulation_run_id, team_name, team_strategy, round_num, pick_num, player_name, player_position, player_team, adp_rank)
               VALUES %s""",
            draft_values
        )
        print(f"Inserted {len(DRAFT_DATA)} draft picks")
        
        # Insert final standings
        standings_values = [
            (sim_id, team, strategy, pts, rank, playoff)
            for team, strategy, pts, rank, playoff in STANDINGS_DATA
        ]
        execute_values(
            cur,
            """INSERT INTO final_standings
               (simulation_run_id, team_name, team_strategy, regular_season_points, final_rank, playoff_finish)
               VALUES %s""",
            standings_values
        )
        print(f"Inserted {len(STANDINGS_DATA)} standings entries")
        
        # Insert metadata
        metadata = [
            (sim_id, 'scoring_format', 'PPR'),
            (sim_id, 'league_size', '12 teams'),
            (sim_id, 'roster_positions', '1 QB, 2 RB, 3 WR, 1 TE, 1 FLEX'),
            (sim_id, 'draft_type', 'Snake'),
            (sim_id, 'regular_season_weeks', '14'),
            (sim_id, 'playoff_weeks', '3 (15-17)'),
            (sim_id, 'data_source_adp', 'FantasyPros 2025 PPR Consensus'),
            (sim_id, 'data_source_stats', 'FantasyPros 2025 Season Totals'),
        ]
        execute_values(
            cur,
            """INSERT INTO training_metadata (simulation_run_id, key, value) VALUES %s""",
            metadata
        )
        print(f"Inserted {len(metadata)} metadata entries")
        
        conn.commit()
        print(f"\n✅ Simulation data stored successfully!")
        print(f"   Simulation ID: {sim_id}")

def main():
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL environment variable not set")
        print("Set it with: export DATABASE_URL='postgresql://user:password@host:port/dbname'")
        print("\nOr run the SQL file directly on Render PostgreSQL:")
        print("  psql $DATABASE_URL -f simulation_data.sql")
        return
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        print("Connected to PostgreSQL!")
        
        create_tables(conn)
        insert_data(conn)
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        print("\nAlternative: Run the SQL file directly on Render PostgreSQL")

if __name__ == "__main__":
    main()
