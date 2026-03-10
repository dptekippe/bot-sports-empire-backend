"""
Scoring Service for Bot Sports Empire.

Database-driven fantasy point calculations based on league-specific ScoringRule records.
Agnostic of data source - works with mock data or real NFL stats.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from sqlalchemy.orm import Session

from app.models.scoring_rule import ScoringRule, StatIdentifier, PositionScope

logger = logging.getLogger(__name__)


class ScoringService:
    """Database-driven service for calculating fantasy points."""
    
    @staticmethod
    def calculate_team_points_for_week_db(
        db_session: Session,
        league_id: str,
        team_id: str,
        week_number: int,
        player_stats: Dict[str, Dict[str, Any]]
    ) -> float:
        """
        Calculate total fantasy points for a team in a given week using database ScoringRules.
        
        Args:
            db_session: Database session
            league_id: League ID
            team_id: Team ID
            week_number: Week number
            player_stats: Dictionary of player stats for the week {player_id: {stat_type: value}}
            
        Returns:
            Total fantasy points for the team
        """
        # Step A: Fetch all ScoringRule records for this league
        scoring_rules = db_session.query(ScoringRule).filter_by(
            league_id=league_id
        ).all()
        
        if not scoring_rules:
            logger.warning(f"No scoring rules found for league {league_id}")
            return 0.0
        
        # Step B: Get team lineup (we need to fetch team from database)
        from app.models.team import Team
        team = db_session.query(Team).filter_by(id=team_id).first()
        
        if not team or not team.current_lineup:
            logger.warning(f"Team {team_id} not found or has no lineup")
            return 0.0
        
        total_points = 0.0
        
        # Step C: For each player in lineup, calculate points using matching ScoringRules
        for position, player_id in team.current_lineup.items():
            if not player_id:  # Skip empty lineup slots
                continue
                
            if player_id in player_stats:
                player_week_stats = player_stats[player_id]
                player_points = ScoringService._calculate_player_points_db(
                    player_week_stats, scoring_rules, position
                )
                total_points += player_points
                logger.debug(f"Player {player_id} at {position}: {player_points:.2f} points")
            else:
                logger.warning(f"No stats found for player {player_id} in lineup position {position}")
        
        logger.info(f"Team {team.name} week {week_number}: {total_points:.2f} total points")
        return total_points
    
    @staticmethod
    def _calculate_player_points_db(
        player_stats: Dict[str, Any],
        scoring_rules: List[ScoringRule],
        position: str
    ) -> float:
        """
        Calculate fantasy points for a single player using database ScoringRules.
        
        Args:
            player_stats: Dictionary of player stats {stat_type: value}
            scoring_rules: List of ScoringRule objects for the league
            position: Player position (QB, RB, WR, TE, K, DEF, etc.)
            
        Returns:
            Total points for the player
        """
        points = 0.0
        
        # Map stat keys from player stats to StatIdentifier enum values
        # This converts various stat naming conventions to our standardized identifiers
        stat_key_mapping = {
            # Passing stats
            "passing_yards": StatIdentifier.PASSING_YARDS,
            "passing_touchdowns": StatIdentifier.PASSING_TOUCHDOWNS,
            "passing_interceptions": StatIdentifier.PASSING_INTERCEPTIONS,
            "passing_2pt_conversions": StatIdentifier.PASSING_2PT_CONVERSIONS,
            
            # Rushing stats
            "rushing_yards": StatIdentifier.RUSHING_YARDS,
            "rushing_touchdowns": StatIdentifier.RUSHING_TOUCHDOWNS,
            "rushing_2pt_conversions": StatIdentifier.RUSHING_2PT_CONVERSIONS,
            
            # Receiving stats
            "receiving_yards": StatIdentifier.RECEIVING_YARDS,
            "receiving_touchdowns": StatIdentifier.RECEIVING_TOUCHDOWNS,
            "receptions": StatIdentifier.RECEPTIONS,
            "receiving_2pt_conversions": StatIdentifier.RECEIVING_2PT_CONVERSIONS,
            
            # Kicking stats
            "extra_points": StatIdentifier.EXTRA_POINTS_MADE,
            "field_goals_0_39": StatIdentifier.FIELD_GOALS_30_39,  # Close mapping
            "field_goals_40_49": StatIdentifier.FIELD_GOALS_40_49,
            "field_goals_50_plus": StatIdentifier.FIELD_GOALS_50_PLUS,
            
            # Defense stats
            "sacks": StatIdentifier.SACKS,
            "interceptions": StatIdentifier.INTERCEPTIONS,
            "fumble_recoveries": StatIdentifier.FUMBLE_RECOVERIES,
            "defensive_touchdowns": StatIdentifier.DEFENSIVE_TOUCHDOWNS,
            "safeties": StatIdentifier.SAFETIES,
            "blocked_kicks": StatIdentifier.BLOCKED_KICKS,
            "points_allowed": None,  # Special handling below
            
            # Miscellaneous
            "fumbles_lost": StatIdentifier.FUMBLES_LOST,
            "two_point_conversions": StatIdentifier.TWO_POINT_CONVERSIONS,
        }
        
        # Calculate points for each stat
        for stat_key, stat_value in player_stats.items():
            if stat_key not in stat_key_mapping:
                logger.debug(f"Unknown stat key: {stat_key}, skipping")
                continue
            
            stat_identifier = stat_key_mapping[stat_key]
            
            # Special handling for defense points allowed
            if stat_key == "points_allowed" and position == "DEF":
                points += ScoringService._calculate_defense_points_allowed_db(
                    stat_value, scoring_rules
                )
                continue
            
            if stat_identifier is None:
                continue
            
            # Find matching scoring rules for this stat and position
            matching_rules = [
                rule for rule in scoring_rules
                if rule.stat_identifier == stat_identifier
                and rule.applies_to_player(position)
            ]
            
            # Apply each matching rule
            for rule in matching_rules:
                rule_points = rule.calculate_points(stat_value)
                points += rule_points
                logger.debug(f"  {stat_key}: {stat_value} × {rule.points_value} = {rule_points:.2f} (rule: {rule.stat_identifier.value})")
        
        return points
    
    @staticmethod
    def _calculate_defense_points_allowed_db(
        points_allowed: int,
        scoring_rules: List[ScoringRule]
    ) -> float:
        """Calculate defense points based on points allowed using ScoringRules."""
        # Map points allowed ranges to StatIdentifier
        points_ranges = [
            (0, 0, StatIdentifier.POINTS_ALLOWED_0),
            (1, 6, StatIdentifier.POINTS_ALLOWED_1_6),
            (7, 13, StatIdentifier.POINTS_ALLOWED_7_13),
            (14, 20, StatIdentifier.POINTS_ALLOWED_14_20),
            (21, 27, StatIdentifier.POINTS_ALLOWED_21_27),
            (28, 34, StatIdentifier.POINTS_ALLOWED_28_34),
            (35, 1000, StatIdentifier.POINTS_ALLOWED_35_PLUS),  # Upper bound
        ]
        
        # Find the matching range
        matching_identifier = None
        for min_val, max_val, identifier in points_ranges:
            if min_val <= points_allowed <= max_val:
                matching_identifier = identifier
                break
        
        if not matching_identifier:
            return 0.0
        
        # Find scoring rules for this points allowed range
        defense_rules = [
            rule for rule in scoring_rules
            if rule.stat_identifier == matching_identifier
            and rule.applies_to_position == PositionScope.DEF
        ]
        
        # Apply the rules (typically just one rule per range)
        total_points = 0.0
        for rule in defense_rules:
            # For points allowed, we typically use the rule's points_value directly
            # (not multiplied by points_allowed)
            total_points += rule.points_value
        
        return total_points
    
    @staticmethod
    def process_live_stat_update_db(
        stat_event: Dict[str, Any],
        league_id: str,
        week_number: int,
        db_session: Session
    ) -> Dict[str, Any]:
        """
        Process a live stat update and calculate impact on fantasy scores using ScoringRules.
        
        Args:
            stat_event: {
                "player_id": "123",
                "stat_type": "passing_touchdowns",
                "stat_value": 1,
                "game_id": "GB-CHI-2025-01",
                "timestamp": "2025-09-10T20:15:00Z"
            }
            league_id: League ID
            week_number: Current week
            db_session: Database session
            
        Returns:
            Dictionary of impacted teams and point changes
        """
        from app.models.league import League
        from app.models.team import Team
        from app.models.matchup import Matchup
        
        # 1. Get league scoring rules
        scoring_rules = db_session.query(ScoringRule).filter_by(
            league_id=league_id
        ).all()
        
        if not scoring_rules:
            logger.error(f"No scoring rules found for league {league_id}")
            return {"impacted_teams": []}
        
        # 2. Find teams with this player in their starting lineup this week
        impacted_teams = []
        
        # Get all matchups for this league and week
        matchups = db_session.query(Matchup).filter_by(
            league_id=league_id,
            week_number=week_number
        ).all()
        
        for matchup in matchups:
            # Check both home and away teams
            for team_id in [matchup.home_team_id, matchup.away_team_id]:
                team = db_session.query(Team).filter_by(id=team_id).first()
                if not team:
                    continue
                
                # Check if player is in team's current lineup
                if ScoringService._is_player_in_lineup(
                    stat_event["player_id"], team.current_lineup
                ):
                    # Get player position from lineup
                    player_position = None
                    for position, pid in team.current_lineup.items():
                        if pid == stat_event["player_id"]:
                            player_position = position
                            break
                    
                    if not player_position:
                        continue
                    
                    # Calculate points for this stat using ScoringRules
                    points = ScoringService._calculate_points_for_stat_db(
                        stat_event["stat_type"],
                        stat_event["stat_value"],
                        player_position,
                        scoring_rules
                    )
                    
                    if points != 0:  # Only track if points were actually added
                        impacted_teams.append({
                            "team_id": team_id,
                            "team_name": team.name,
                            "player_id": stat_event["player_id"],
                            "player_position": player_position,
                            "stat_type": stat_event["stat_type"],
                            "stat_value": stat_event["stat_value"],
                            "points_added": points,
                            "matchup_id": matchup.id,
                            "is_home_team": team_id == matchup.home_team_id
                        })
        
        logger.info(f"Stat update impacted {len(impacted_teams)} teams")
        return {"impacted_teams": impacted_teams}
    
    @staticmethod
    def _calculate_points_for_stat_db(
        stat_type: str,
        stat_value: float,
        player_position: str,
        scoring_rules: List[ScoringRule]
    ) -> float:
        """
        Calculate points for a single stat using ScoringRules.
        
        Args:
            stat_type: Type of stat (e.g., "passing_touchdowns")
            stat_value: Value of the stat
            player_position: Player position (QB, RB, WR, etc.)
            scoring_rules: List of ScoringRule objects
            
        Returns:
            Points earned for this stat
        """
        # Map stat type to StatIdentifier
        stat_key_mapping = {
            "passing_yards": StatIdentifier.PASSING_YARDS,
            "passing_touchdowns": StatIdentifier.PASSING_TOUCHDOWNS,
            "passing_interceptions": StatIdentifier.PASSING_INTERCEPTIONS,
            "rushing_yards": StatIdentifier.RUSHING_YARDS,
            "rushing_touchdowns": StatIdentifier.RUSHING_TOUCHDOWNS,
            "receiving_yards": StatIdentifier.RECEIVING_YARDS,
            "receiving_touchdowns": StatIdentifier.RECEIVING_TOUCHDOWNS,
            "receptions": StatIdentifier.RECEPTIONS,
            "fumbles_lost": StatIdentifier.FUMBLES_LOST,
            "two_point_conversions": StatIdentifier.TWO_POINT_CONVERSIONS,
            "extra_points": StatIdentifier.EXTRA_POINTS_MADE,
            "field_goals_0_39": StatIdentifier.FIELD_GOALS_30_39,
            "field_goals_40_49": StatIdentifier.FIELD_GOALS_40_49,
            "field_goals_50_plus": StatIdentifier.FIELD_GOALS_50_PLUS,
            "sacks": StatIdentifier.SACKS,
            "interceptions": StatIdentifier.INTERCEPTIONS,
            "fumble_recoveries": StatIdentifier.FUMBLE_RECOVERIES,
            "defensive_touchdowns": StatIdentifier.DEFENSIVE_TOUCHDOWNS,
            "safeties": StatIdentifier.SAFETIES,
            "blocked_kicks": StatIdentifier.BLOCKED_KICKS,
        }
        
        if stat_type not in stat_key_mapping:
            logger.debug(f"Unknown stat type for points calculation: {stat_type}")
            return 0.0
        
        stat_identifier = stat_key_mapping[stat_type]
        
        # Find matching scoring rules
        matching_rules = [
            rule for rule in scoring_rules
            if rule.stat_identifier == stat_identifier
            and rule.applies_to_player(player_position)
        ]
        
        # Calculate total points from all matching rules
        total_points = 0.0
        for rule in matching_rules:
            total_points += rule.calculate_points(stat_value)
        
        return total_points
    
    @staticmethod
    def _is_player_in_lineup(player_id: str, lineup: Dict[str, str]) -> bool:
        """Check if a player is in a team's starting lineup."""
        if not lineup:
            return False
        return player_id in lineup.values()
    
    @staticmethod
    def generate_mock_player_stats(
        player_ids: List[str],
        week_number: int
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate mock player stats for development/testing.
        
        Args:
            player_ids: List of player IDs
            week_number: Week number for stats
            
        Returns:
            Dictionary of mock stats for each player
        """
        import random
        
        mock_stats = {}
        
        for player_id in player_ids:
            # Generate realistic-ish mock stats based on position
            # For simplicity, assume QB for ids ending with 1, RB with 2, etc.
            player_type = player_id[-1] if player_id else "1"
            
            if player_type in ["1", "6"]:  # QB
                stats = {
                    "passing_yards": random.randint(150, 400),
                    "passing_touchdowns": random.randint(0, 4),
                    "passing_interceptions": random.randint(0, 2),
                    "rushing_yards": random.randint(0, 50),
                    "rushing_touchdowns": random.randint(0, 1),
                    "fumbles_lost": random.randint(0, 1),
                }
            elif player_type in ["2", "7"]:  # RB
                stats = {
                    "rushing_yards": random.randint(40, 150),
                    "rushing_touchdowns": random.randint(0, 2),
                    "receiving_yards": random.randint(10, 80),
                    "receiving_touchdowns": random.randint(0, 1),
                    "receptions": random.randint(1, 6),
                    "fumbles_lost": random.randint(0, 1),
                }
            elif player_type in ["3", "8"]:  # WR
                stats = {
                    "receiving_yards": random.randint(30, 120),
                    "receiving_touchdowns": random.randint(0, 2),
                    "receptions": random.randint(2, 8),
                    "rushing_yards": random.randint(0, 20),
                    "fumbles_lost": random.randint(0, 1),
                }
            elif player_type in ["4", "9"]:  # TE
                stats = {
                    "receiving_yards": random.randint(20, 80),
                    "receiving_touchdowns": random.randint(0, 1),
                    "receptions": random.randint(1, 5),
                    "fumbles_lost": random.randint(0, 1),
                }
            elif player_type == "5":  # K
                stats = {
                    "extra_points": random.randint(1, 5),
                    "field_goals_0_39": random.randint(0, 2),
                    "field_goals_40_49": random.randint(0, 2),
                    "field_goals_50_plus": random.randint(0, 1),
                }
            else:  # DEF
                stats = {
                    "sacks": random.randint(0, 5),
                    "interceptions": random.randint(0, 3),
                    "fumble_recoveries": random.randint(0, 2),
                    "defensive_touchdowns": random.randint(0, 1),
                    "safeties": random.randint(0, 1),
                    "blocked_kicks": random.randint(0, 1),
                    "points_allowed": random.randint(0, 35),
                }
            
            mock_stats[player_id] = stats
        
        return mock_stats