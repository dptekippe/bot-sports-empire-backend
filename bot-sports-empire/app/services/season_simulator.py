"""
Season Simulator Service for Bot Sports Empire.

The core engine that automates weekly matchups, scoring, and mood events.
This service creates the automated game loop for the platform.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.database import SessionLocal
from app.models.matchup import Matchup, MatchupStatus
from app.models.team import Team
from app.models.league import League
from app.models.bot import BotAgent
from app.services.scoring_service import ScoringService
from app.services.mood_calculation import MoodCalculationService, MoodEvent
from app.services.scoring_engine import ScoringEngine

logger = logging.getLogger(__name__)


class SeasonSimulator:
    """
    Service that simulates a week of fantasy football matchups.
    
    Core responsibilities:
    1. Fetch scheduled matchups for a given league and week
    2. Generate player stats (mock or real)
    3. Calculate scores using ScoringService with league-specific ScoringRules
    4. Update matchup winners/losers
    5. Trigger WIN/LOSS mood events for bots
    6. Update league standings
    """
    
    def __init__(self):
        """Initialize the season simulator with required services."""
        self.scoring_service = ScoringService()
        self.mood_service = MoodCalculationService()
        # ScoringEngine requires a db_session_factory - a function that returns a new session
        self.scoring_engine = ScoringEngine(db_session_factory=SessionLocal, use_mock_data=True)
    
    def simulate_week(self, league_id: str, week_number: int) -> Dict[str, Any]:
        """
        Simulate a week of matchups for a given league.
        
        This is the main method that orchestrates the weekly simulation:
        1. Fetches scheduled matchups
        2. Uses ScoringService (with league-specific ScoringRules) to generate scores
        3. Updates matchup winners/losers
        4. Triggers WIN/LOSS mood events
        
        Args:
            league_id: The ID of the league to simulate
            week_number: The week number to simulate (1-17 for regular season)
            
        Returns:
            Dictionary with simulation results including:
            - matchups_simulated: Number of matchups processed
            - total_points_scored: Total fantasy points scored in the week
            - mood_events_triggered: Number of WIN/LOSS mood events triggered
            - matchups: List of matchup results
        """
        db = SessionLocal()
        
        try:
            logger.info(f"🎮 Starting week {week_number} simulation for league {league_id}")
            
            # 1. Fetch scheduled matchups for this league and week
            matchups = self._get_scheduled_matchups(db, league_id, week_number)
            
            if not matchups:
                logger.warning(f"No scheduled matchups found for league {league_id}, week {week_number}")
                return {
                    "matchups_simulated": 0,
                    "total_points_scored": 0.0,
                    "mood_events_triggered": 0,
                    "matchups": [],
                    "message": f"No scheduled matchups for week {week_number}"
                }
            
            logger.info(f"Found {len(matchups)} matchups to simulate")
            
            # 2. Generate player stats for the week
            # For now, use mock data. In production, this would fetch from NFL API
            player_stats = self._generate_player_stats_for_week(db, league_id, week_number)
            
            # 3. Process each matchup
            results = []
            total_points = 0.0
            mood_events_count = 0
            
            for matchup in matchups:
                matchup_result = self._simulate_matchup(
                    db, matchup, player_stats, week_number
                )
                results.append(matchup_result)
                total_points += matchup_result.get("total_points", 0.0)
                mood_events_count += matchup_result.get("mood_events_triggered", 0)
            
            # 4. Update league standings
            self._update_league_standings(db, league_id)
            
            logger.info(f"✅ Week {week_number} simulation complete: "
                       f"{len(matchups)} matchups, {total_points:.1f} total points, "
                       f"{mood_events_count} mood events")
            
            return {
                "matchups_simulated": len(matchups),
                "total_points_scored": total_points,
                "mood_events_triggered": mood_events_count,
                "matchups": results,
                "league_id": league_id,
                "week_number": week_number,
                "simulated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error simulating week {week_number} for league {league_id}: {str(e)}")
            raise
        finally:
            db.close()
    
    def _get_scheduled_matchups(self, db: Session, league_id: str, week_number: int) -> List[Matchup]:
        """
        Fetch scheduled matchups for a given league and week.
        
        Args:
            db: Database session
            league_id: League ID
            week_number: Week number
            
        Returns:
            List of Matchup objects with status SCHEDULED
        """
        matchups = db.query(Matchup).filter(
            and_(
                Matchup.league_id == league_id,
                Matchup.week_number == week_number,
                Matchup.status == MatchupStatus.SCHEDULED
            )
        ).all()
        
        return matchups
    
    def _generate_player_stats_for_week(self, db: Session, league_id: str, week_number: int) -> Dict[str, Dict[str, Any]]:
        """
        Generate player stats for a given week.
        
        For MVP, this generates mock data. In production, this would:
        1. Fetch real NFL stats from an API (Sleeper, ESPN, etc.)
        2. Map NFL players to fantasy players in the league
        3. Return structured stats for scoring
        
        Args:
            db: Database session
            league_id: League ID
            week_number: Week number
            
        Returns:
            Dictionary mapping player_id to their stats for the week
            Format: {player_id: {stat_type: value, ...}}
        """
        # Get all teams in the league to collect player IDs from lineups
        from app.models.team import Team
        
        teams = db.query(Team).filter(Team.league_id == league_id).all()
        
        # Collect all player IDs from team lineups
        all_player_ids = []
        for team in teams:
            if team.current_lineup:
                # current_lineup is a dict like {position: player_id}
                player_ids = [pid for pid in team.current_lineup.values() if pid]
                all_player_ids.extend(player_ids)
        
        # Remove duplicates
        all_player_ids = list(set(all_player_ids))
        
        if not all_player_ids:
            logger.warning(f"No players found in lineups for league {league_id}")
            return {}
        
        # Use ScoringService to generate mock stats
        player_stats = ScoringService.generate_mock_player_stats(
            player_ids=all_player_ids,
            week_number=week_number
        )
        
        logger.info(f"Generated stats for {len(player_stats)} players in week {week_number}")
        return player_stats
    
    def _simulate_matchup(self, db: Session, matchup: Matchup, 
                         player_stats: Dict[str, Dict[str, Any]], 
                         week_number: int) -> Dict[str, Any]:
        """
        Simulate a single matchup.
        
        Args:
            db: Database session
            matchup: The matchup to simulate
            player_stats: Player stats for the week
            week_number: Week number
            
        Returns:
            Dictionary with matchup simulation results
        """
        logger.info(f"  Simulating matchup: {matchup.home_team_id[:8]} vs {matchup.away_team_id[:8]}")
        
        # 1. Calculate scores for both teams
        home_score = self.scoring_service.calculate_team_points_for_week_db(
            db_session=db,
            league_id=matchup.league_id,
            team_id=matchup.home_team_id,
            week_number=week_number,
            player_stats=player_stats
        )
        
        away_score = self.scoring_service.calculate_team_points_for_week_db(
            db_session=db,
            league_id=matchup.league_id,
            team_id=matchup.away_team_id,
            week_number=week_number,
            player_stats=player_stats
        )
        
        # 2. Update the matchup with scores
        matchup.home_score = home_score
        matchup.away_score = away_score
        matchup.status = MatchupStatus.COMPLETED
        matchup.finalized_at = datetime.now(timezone.utc)
        
        # 3. Determine winner and loser
        winner_id = matchup.winner_id
        loser_id = matchup.loser_id
        is_tie = matchup.is_tie
        
        # 4. Trigger mood events for bots (if not a tie)
        mood_events_triggered = 0
        if not is_tie and winner_id and loser_id:
            # Get bot IDs for the teams
            home_bot_id = self._get_bot_id_for_team(db, matchup.home_team_id)
            away_bot_id = self._get_bot_id_for_team(db, matchup.away_team_id)
            
            if home_bot_id and away_bot_id:
                # Determine which bot won and lost
                if winner_id == matchup.home_team_id:
                    winning_bot_id = home_bot_id
                    losing_bot_id = away_bot_id
                else:
                    winning_bot_id = away_bot_id
                    losing_bot_id = home_bot_id
                
                # Trigger WIN mood event for winner
                win_event = MoodEvent(
                    type="WIN",
                    impact=20,  # Positive impact for winning
                    metadata={
                        "matchup_id": matchup.id,
                        "week_number": week_number,
                        "score": home_score if winner_id == matchup.home_team_id else away_score,
                        "opponent_score": away_score if winner_id == matchup.home_team_id else home_score,
                        "margin_of_victory": matchup.margin_of_victory
                    }
                )
                
                # Trigger LOSS mood event for loser
                loss_event = MoodEvent(
                    type="LOSS",
                    impact=-15,  # Negative impact for losing
                    metadata={
                        "matchup_id": matchup.id,
                        "week_number": week_number,
                        "score": home_score if loser_id == matchup.home_team_id else away_score,
                        "opponent_score": away_score if loser_id == matchup.home_team_id else home_score,
                        "margin_of_victory": matchup.margin_of_victory
                    }
                )
                
                # Process mood events
                try:
                    # process_event is async, so we need to run it properly
                    # For now, we'll run it synchronously with asyncio
                    import asyncio
                    asyncio.run(self.mood_service.process_event(winning_bot_id, win_event))
                    asyncio.run(self.mood_service.process_event(losing_bot_id, loss_event))
                    mood_events_triggered = 2
                    logger.info(f"    Triggered WIN/LOSS mood events for bots")
                except Exception as e:
                    logger.error(f"    Failed to trigger mood events: {str(e)}")
        
        # 5. Save the matchup
        db.commit()
        
        # 6. Return simulation results
        return {
            "matchup_id": matchup.id,
            "home_team_id": matchup.home_team_id,
            "away_team_id": matchup.away_team_id,
            "home_score": home_score,
            "away_score": away_score,
            "winner_id": winner_id,
            "loser_id": loser_id,
            "is_tie": is_tie,
            "margin_of_victory": matchup.margin_of_victory,
            "total_points": home_score + away_score,
            "mood_events_triggered": mood_events_triggered,
            "status": matchup.status.value
        }
    
    def _get_bot_id_for_team(self, db: Session, team_id: str) -> Optional[str]:
        """
        Get the bot ID associated with a team.
        
        Args:
            db: Database session
            team_id: Team ID
            
        Returns:
            Bot ID if found, None otherwise
        """
        team = db.query(Team).filter(Team.id == team_id).first()
        if team and team.bot_id:
            return team.bot_id
        return None
    
    def _update_league_standings(self, db: Session, league_id: str):
        """
        Update league standings after a week of simulations.
        
        This would typically:
        1. Update team records (wins, losses, ties)
        2. Calculate points for and points against
        3. Update playoff picture if applicable
        4. Update league metadata
        
        Args:
            db: Database session
            league_id: League ID
        """
        # For MVP, this is a placeholder
        # In a full implementation, this would update team standings
        league = db.query(League).filter(League.id == league_id).first()
        if league:
            # Update last simulated week
            # Note: league.metadata might be a SQLAlchemy MetaData object or dict
            # We need to handle it carefully
            try:
                # Try to update metadata if it's a dict
                if hasattr(league, 'metadata'):
                    # Create a new dict if metadata is None or not a dict
                    if league.metadata is None:
                        league.metadata = {}
                    elif not isinstance(league.metadata, dict):
                        # If it's not a dict, we can't update it
                        logger.warning(f"League metadata is not a dict: {type(league.metadata)}")
                        return
                    
                    league.metadata["last_simulated_week"] = datetime.now(timezone.utc).isoformat()
                    league.metadata["standings_updated_at"] = datetime.now(timezone.utc).isoformat()
                    
                    db.commit()
                    logger.info(f"Updated league metadata for {league_id}")
            except Exception as e:
                logger.warning(f"Could not update league metadata: {e}")
                # Don't fail the whole simulation if metadata update fails
                db.rollback()
    
    def simulate_entire_season(self, league_id: str, start_week: int = 1, end_week: int = 17) -> Dict[str, Any]:
        """
        Simulate an entire season (multiple weeks).
        
        Args:
            league_id: League ID
            start_week: Starting week (default: 1)
            end_week: Ending week (default: 17 for regular season)
            
        Returns:
            Dictionary with season simulation results
        """
        logger.info(f"🏈 Starting full season simulation for league {league_id} (weeks {start_week}-{end_week})")
        
        season_results = {
            "league_id": league_id,
            "start_week": start_week,
            "end_week": end_week,
            "weeks_simulated": [],
            "total_matchups": 0,
            "total_points": 0.0,
            "total_mood_events": 0,
            "started_at": datetime.now(timezone.utc).isoformat()
        }
        
        for week in range(start_week, end_week + 1):
            logger.info(f"  Simulating week {week}...")
            
            week_result = self.simulate_week(league_id, week)
            season_results["weeks_simulated"].append(week_result)
            season_results["total_matchups"] += week_result.get("matchups_simulated", 0)
            season_results["total_points"] += week_result.get("total_points_scored", 0.0)
            season_results["total_mood_events"] += week_result.get("mood_events_triggered", 0)
            
            # Small delay to avoid overwhelming the system
            import time
            time.sleep(0.1)
        
        season_results["completed_at"] = datetime.now(timezone.utc).isoformat()
        season_results["duration_seconds"] = (
            datetime.now(timezone.utc) - 
            datetime.fromisoformat(season_results["started_at"].replace('Z', '+00:00'))
        ).total_seconds()
        
        logger.info(f"✅ Season simulation complete: "
                   f"{season_results['total_matchups']} matchups, "
                   f"{season_results['total_points']:.1f} total points, "
                   f"{season_results['total_mood_events']} mood events")
        
        return season_results