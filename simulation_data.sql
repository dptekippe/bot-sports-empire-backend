-- 2025 Dynasty Fantasy Football Simulation Training Data
-- Run this on Render PostgreSQL

-- Table: simulation_runs
CREATE TABLE IF NOT EXISTS simulation_runs (
    id SERIAL PRIMARY KEY,
    simulation_name VARCHAR(100) DEFAULT '2025_PPR_Draft_Sim',
    season_year INTEGER DEFAULT 2025,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_teams INTEGER DEFAULT 12,
    rounds_drafted INTEGER DEFAULT 20
);

-- Table: draft_picks
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
);

-- Table: weekly_scores
CREATE TABLE IF NOT EXISTS weekly_scores (
    id SERIAL PRIMARY KEY,
    simulation_run_id INTEGER REFERENCES simulation_runs(id),
    team_name VARCHAR(100),
    week_num INTEGER,
    points_scored DECIMAL(10,2)
);

-- Table: final_standings
CREATE TABLE IF NOT EXISTS final_standings (
    id SERIAL PRIMARY KEY,
    simulation_run_id INTEGER REFERENCES simulation_runs(id),
    team_name VARCHAR(100),
    team_strategy VARCHAR(255),
    regular_season_points DECIMAL(10,2),
    final_rank INTEGER,
    playoff_finish VARCHAR(50)
);

-- Insert simulation run
INSERT INTO simulation_runs (simulation_name, season_year, total_teams, rounds_drafted)
VALUES ('2025_PPR_Draft_Sim', 2025, 12, 20)
RETURNING id;

-- Draft picks data (Roger at pick 1.10, 20 rounds)
INSERT INTO draft_picks (simulation_run_id, team_name, team_strategy, round_num, pick_num, player_name, player_position, player_team, adp_rank) VALUES
(1, 'Roger (Balanced)', 'Follow ADP strictly, balanced RB/WR/TE', 1, 10, 'Derrick Henry', 'RB', 'BAL', 10),
(1, 'Roger (Balanced)', 'Follow ADP strictly, balanced RB/WR/TE', 2, 23, 'Brian Thomas Jr.', 'WR', 'JAC', 15),
(1, 'Roger (Balanced)', 'Follow ADP strictly, balanced RB/WR/TE', 3, 34, 'Jalen Hurts', 'QB', 'PHI', 34),
(1, 'Roger (Balanced)', 'Follow ADP strictly, balanced RB/WR/TE', 4, 39, 'Terry McLaurin', 'WR', 'WAS', 39),
(1, 'Roger (Balanced)', 'Follow ADP strictly, balanced RB/WR/TE', 5, 58, 'David Montgomery', 'RB', 'HOU', 58);

-- Weekly scores for Roger (weeks 1-14, simulated)
INSERT INTO weekly_scores (simulation_run_id, team_name, week_num, points_scored) VALUES
(1, 'Roger (Balanced)', 1, 42.3),
(1, 'Roger (Balanced)', 2, 45.1),
(1, 'Roger (Balanced)', 3, 38.7),
(1, 'Roger (Balanced)', 4, 51.2),
(1, 'Roger (Balanced)', 5, 39.8),
(1, 'Roger (Balanced)', 6, 44.5),
(1, 'Roger (Balanced)', 7, 47.1),
(1, 'Roger (Balanced)', 8, 35.6),
(1, 'Roger (Balanced)', 9, 49.2),
(1, 'Roger (Balanced)', 10, 41.3),
(1, 'Roger (Balanced)', 11, 46.8),
(1, 'Roger (Balanced)', 12, 43.2),
(1, 'Roger (Balanced)', 13, 38.9),
(1, 'Roger (Balanced)', 14, 44.7);

-- All teams final standings
INSERT INTO final_standings (simulation_run_id, team_name, team_strategy, regular_season_points, final_rank, playoff_finish) VALUES
(1, 'Safe Draft', 'High floor players only', 1002.9, 1, 'Did not make playoffs'),
(1, 'Value WR', 'Wait on WR, target value picks', 978.4, 2, 'CHAMPION'),
(1, 'Zero RB', 'Load up WR first 4 rounds', 879.5, 3, 'Semifinals'),
(1, 'PPR Specialist', 'Target high-catch WRs', 826.1, 4, 'Semifinals'),
(1, 'Best Player', 'Take best available always', 809.9, 5, 'Quarterfinals'),
(1, 'Veteran Hunter', 'Prioritize proven veterans', 719.4, 6, 'Quarterfinals'),
(1, 'Risk Taker', 'High variance, high ceiling', 618.5, 7, 'Did not make playoffs'),
(1, 'Roger (Balanced)', 'Follow ADP strictly, balanced RB/WR/TE', 605.4, 8, 'Did not make playoffs'),
(1, 'Sleeper Hunter', 'Target ADP sleepers', 595.5, 9, 'Did not make playoffs'),
(1, 'Hero RB', 'First 2 picks RB, then value', 592.5, 10, 'Did not make playoffs'),
(1, 'Youth Movement', 'Prioritize younger players', 467.8, 11, 'Did not make playoffs'),
(1, 'Elite QB', 'Prioritize QB early (superflex)', 459.9, 12, 'Did not make playoffs');

-- Additional training metadata
CREATE TABLE IF NOT EXISTS training_metadata (
    id SERIAL PRIMARY KEY,
    simulation_run_id INTEGER REFERENCES simulation_runs(id),
    key VARCHAR(100),
    value TEXT
);

INSERT INTO training_metadata (simulation_run_id, key, value) VALUES
(1, 'scoring_format', 'PPR'),
(1, 'league_size', '12 teams'),
(1, 'roster_positions', '1 QB, 2 RB, 3 WR, 1 TE, 1 FLEX'),
(1, 'draft_type', 'Snake'),
(1, 'regular_season_weeks', '14'),
(1, 'playoff_weeks', '3 (15-17)'),
(1, 'data_source_adp', 'FantasyPros 2025 PPR Consensus'),
(1, 'data_source_stats', 'FantasyPros 2025 Season Totals');
