"""
Mock Player Stats Service for Bot Sports Empire.

Provides hardcoded player stats for MVP development of Player Evaluation Sub-Agent.
Based on realistic 2024 season averages for top players.
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class MockPlayerStatsService:
    """Service providing mock player stats for development/testing."""
    
    # Mock stats based on 2024 season averages (realistic projections)
    # Format: player_id -> {stat_type: value}
    MOCK_STATS = {
        # Patrick Mahomes (QB1)
        "QB1": {
            "passing_yards": 285.0,          # per game average
            "passing_touchdowns": 2.1,       # per game
            "passing_interceptions": 0.7,    # per game
            "rushing_yards": 15.0,           # per game
            "rushing_touchdowns": 0.2,       # per game
            "fumbles_lost": 0.1,             # per game
            "passing_2pt_conversions": 0.05, # occasional
            "rushing_2pt_conversions": 0.02, # rare
        },
        
        # Christian McCaffrey (RB1)
        "RB1": {
            "rushing_yards": 95.0,           # per game
            "rushing_touchdowns": 0.9,       # per game
            "receiving_yards": 45.0,         # per game
            "receiving_touchdowns": 0.3,     # per game
            "receptions": 5.5,               # per game (PPR gold)
            "fumbles_lost": 0.1,             # per game
            "rushing_2pt_conversions": 0.05, # occasional
            "receiving_2pt_conversions": 0.03, # occasional
        },
        
        # Justin Jefferson (WR1)
        "WR1": {
            "receiving_yards": 105.0,        # per game
            "receiving_touchdowns": 0.8,     # per game
            "receptions": 7.2,               # per game (elite PPR)
            "rushing_yards": 5.0,            # occasional gadget plays
            "fumbles_lost": 0.05,            # per game
            "receiving_2pt_conversions": 0.04, # occasional
        },
        
        # Travis Kelce (TE1)
        "TE1": {
            "receiving_yards": 75.0,         # per game
            "receiving_touchdowns": 0.6,     # per game
            "receptions": 6.0,               # per game (elite for TE)
            "fumbles_lost": 0.05,            # per game
            "receiving_2pt_conversions": 0.03, # occasional
        },
        
        # Additional mock players for testing (if needed)
        "QB2": {
            "passing_yards": 250.0,
            "passing_touchdowns": 1.8,
            "passing_interceptions": 0.8,
            "rushing_yards": 20.0,
            "rushing_touchdowns": 0.15,
            "fumbles_lost": 0.15,
        },
        "RB2": {
            "rushing_yards": 80.0,
            "rushing_touchdowns": 0.7,
            "receiving_yards": 30.0,
            "receiving_touchdowns": 0.2,
            "receptions": 3.5,
            "fumbles_lost": 0.15,
        },
        "WR2": {
            "receiving_yards": 85.0,
            "receiving_touchdowns": 0.6,
            "receptions": 5.8,
            "fumbles_lost": 0.08,
        },
        "TE2": {
            "receiving_yards": 55.0,
            "receiving_touchdowns": 0.4,
            "receptions": 4.5,
            "fumbles_lost": 0.08,
        },
    }
    
    # Position-specific stat templates for generating stats for unknown players
    POSITION_TEMPLATES = {
        "QB": {
            "passing_yards": 240.0,
            "passing_touchdowns": 1.6,
            "passing_interceptions": 0.9,
            "rushing_yards": 12.0,
            "rushing_touchdowns": 0.1,
            "fumbles_lost": 0.15,
        },
        "RB": {
            "rushing_yards": 70.0,
            "rushing_touchdowns": 0.5,
            "receiving_yards": 25.0,
            "receiving_touchdowns": 0.15,
            "receptions": 3.0,
            "fumbles_lost": 0.12,
        },
        "WR": {
            "receiving_yards": 65.0,
            "receiving_touchdowns": 0.4,
            "receptions": 4.5,
            "fumbles_lost": 0.07,
        },
        "TE": {
            "receiving_yards": 45.0,
            "receiving_touchdowns": 0.3,
            "receptions": 3.8,
            "fumbles_lost": 0.06,
        },
        "K": {
            "extra_points": 2.5,
            "field_goals_0_39": 1.2,
            "field_goals_40_49": 0.8,
            "field_goals_50_plus": 0.3,
        },
        "DEF": {
            "sacks": 2.5,
            "interceptions": 1.2,
            "fumble_recoveries": 0.8,
            "defensive_touchdowns": 0.3,
            "safeties": 0.05,
            "blocked_kicks": 0.15,
            "points_allowed": 21.5,
        },
    }
    
    @classmethod
    def get_player_stats(cls, player_id: str, position: Optional[str] = None) -> Dict[str, float]:
        """
        Get mock stats for a player.
        
        Args:
            player_id: Player identifier
            position: Player position (QB, RB, WR, TE, K, DEF)
            
        Returns:
            Dictionary of stat_name -> stat_value
        """
        # Check if we have specific mock stats for this player
        if player_id in cls.MOCK_STATS:
            logger.debug(f"Returning specific mock stats for {player_id}")
            return cls.MOCK_STATS[player_id].copy()
        
        # If no specific stats, use position template
        if position and position.upper() in cls.POSITION_TEMPLATES:
            logger.debug(f"Returning position template stats for {player_id} ({position})")
            return cls.POSITION_TEMPLATES[position.upper()].copy()
        
        # Default to generic offensive player stats
        logger.debug(f"Returning generic offensive stats for {player_id}")
        return {
            "passing_yards": 0.0,
            "passing_touchdowns": 0.0,
            "passing_interceptions": 0.0,
            "rushing_yards": 0.0,
            "rushing_touchdowns": 0.0,
            "receiving_yards": 0.0,
            "receiving_touchdowns": 0.0,
            "receptions": 0.0,
            "fumbles_lost": 0.0,
        }
    
    @classmethod
    def get_season_projection(cls, player_id: str, position: Optional[str] = None, 
                             games: int = 17) -> Dict[str, float]:
        """
        Get season-long projections based on per-game averages.
        
        Args:
            player_id: Player identifier
            position: Player position
            games: Number of games in season (default 17)
            
        Returns:
            Dictionary of stat_name -> season_total
        """
        per_game_stats = cls.get_player_stats(player_id, position)
        
        # Multiply per-game stats by number of games
        season_stats = {}
        for stat_name, per_game_value in per_game_stats.items():
            season_stats[stat_name] = per_game_value * games
        
        return season_stats
    
    @classmethod
    def get_all_player_stats(cls) -> Dict[str, Dict[str, float]]:
        """
        Get mock stats for all known players.
        
        Returns:
            Dictionary of player_id -> stats_dict
        """
        return cls.MOCK_STATS.copy()
    
    @classmethod
    def validate_stats_for_scoring(cls, player_id: str, scoring_rules: list) -> bool:
        """
        Validate that player has all required stats for scoring rules.
        
        Args:
            player_id: Player identifier
            scoring_rules: List of ScoringRule objects
            
        Returns:
            True if player has all required stats, False otherwise
        """
        player_stats = cls.get_player_stats(player_id)
        
        # Extract required stat identifiers from scoring rules
        required_stats = set()
        for rule in scoring_rules:
            required_stats.add(rule.stat_identifier.value)
        
        # Check if player has all required stats
        # Note: This is a simplified check - actual implementation would need
        # to map stat identifiers to our mock stat keys
        logger.debug(f"Required stats for {player_id}: {required_stats}")
        
        # For MVP, assume we have all required stats
        return True
    
    @classmethod
    def get_player_comparison(cls, player_ids: list) -> Dict[str, Dict[str, Any]]:
        """
        Get comparison data for multiple players.
        
        Args:
            player_ids: List of player IDs to compare
            
        Returns:
            Dictionary with comparison data
        """
        comparison = {}
        
        for player_id in player_ids:
            stats = cls.get_player_stats(player_id)
            season_stats = cls.get_season_projection(player_id)
            
            # Calculate some derived metrics
            total_touchdowns = (
                stats.get("passing_touchdowns", 0) +
                stats.get("rushing_touchdowns", 0) +
                stats.get("receiving_touchdowns", 0)
            )
            
            total_yards = (
                stats.get("passing_yards", 0) +
                stats.get("rushing_yards", 0) +
                stats.get("receiving_yards", 0)
            )
            
            comparison[player_id] = {
                "per_game": stats,
                "season_projection": season_stats,
                "derived_metrics": {
                    "total_touchdowns_per_game": total_touchdowns,
                    "total_yards_per_game": total_yards,
                    "touchdown_rate": total_touchdowns / max(total_yards, 1) * 100,
                },
                "summary": f"{player_id}: {total_yards:.1f} YPG, {total_touchdowns:.1f} TD/G"
            }
        
        return comparison