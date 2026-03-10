"""
Scoring Engine for Bot Sports Empire.

Event-driven service for real-time fantasy scoring updates.
Consumes NFL game stats (from mock generator or real API) and updates fantasy scores.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .scoring_service import ScoringService

logger = logging.getLogger(__name__)


class ScoringEngine:
    """
    Main scoring engine that processes live NFL stats and updates fantasy scores.
    
    Architecture:
    1. Stats Ingestion: Polls data source (mock or real API) every 30-60 seconds
    2. Event Processing: Processes each stat event through ScoringService
    3. Score Updates: Updates matchup scores in database
    4. Notifications: (Optional) Sends real-time updates via WebSocket
    """
    
    def __init__(self, db_session_factory, use_mock_data: bool = True):
        """
        Initialize scoring engine.
        
        Args:
            db_session_factory: Function that returns a new SQLAlchemy session
            use_mock_data: Whether to use mock data generator (True for development)
        """
        self.db_session_factory = db_session_factory
        self.use_mock_data = use_mock_data
        self.is_running = False
        self.poll_interval = 30  # seconds
        
        # In-memory cache for recent stats to avoid duplicate processing
        self.processed_stat_ids = set()
        self.stat_cache_ttl = timedelta(minutes=5)
        
        # Mock data generator state
        self.mock_game_state = {}
        
        logger.info(f"ScoringEngine initialized (mock_data={use_mock_data})")
    
    async def start(self):
        """Start the scoring engine background task."""
        if self.is_running:
            logger.warning("ScoringEngine already running")
            return
        
        self.is_running = True
        logger.info("Starting ScoringEngine...")
        
        # Start background tasks
        asyncio.create_task(self._stats_polling_loop())
        asyncio.create_task(self._cleanup_cache_loop())
        
        logger.info("ScoringEngine started successfully")
    
    async def stop(self):
        """Stop the scoring engine."""
        self.is_running = False
        logger.info("ScoringEngine stopped")
    
    async def _stats_polling_loop(self):
        """Main loop that polls for new stats and processes them."""
        while self.is_running:
            try:
                # Fetch new stats
                new_stats = await self._fetch_latest_stats()
                
                if new_stats:
                    logger.info(f"Processing {len(new_stats)} new stat events")
                    
                    # Process each stat event
                    for stat_event in new_stats:
                        await self._process_stat_event(stat_event)
                
                # Wait before next poll
                await asyncio.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in stats polling loop: {e}")
                await asyncio.sleep(5)  # Brief pause on error
    
    async def _fetch_latest_stats(self) -> List[Dict[str, Any]]:
        """
        Fetch latest NFL game stats from data source.
        
        Returns:
            List of stat events
        """
        if self.use_mock_data:
            return self._generate_mock_stats()
        else:
            # TODO: Integrate with real NFL data API
            # This would make HTTP requests to SportsRadar, MySportsFeeds, etc.
            return []
    
    def _generate_mock_stats(self) -> List[Dict[str, Any]]:
        """Generate mock NFL game stats for development."""
        import random
        import uuid
        
        # Simulate 0-3 stat events per poll
        num_events = random.randint(0, 3)
        if num_events == 0:
            return []
        
        events = []
        stat_types = [
            "passing_yards", "passing_touchdowns", "passing_interceptions",
            "rushing_yards", "rushing_touchdowns",
            "receiving_yards", "receiving_touchdowns", "receptions",
            "field_goals_0_39", "field_goals_40_49", "field_goals_50_plus",
            "extra_points", "sacks", "interceptions", "fumble_recoveries",
        ]
        
        # Mock player IDs (would come from database in real implementation)
        mock_players = [
            "player_qb_1", "player_rb_1", "player_wr_1", "player_te_1",
            "player_k_1", "player_def_1", "player_qb_2", "player_rb_2",
        ]
        
        for _ in range(num_events):
            stat_type = random.choice(stat_types)
            player_id = random.choice(mock_players)
            
            # Generate appropriate stat value based on type
            if "yards" in stat_type:
                stat_value = random.randint(5, 80)
            elif "touchdown" in stat_type:
                stat_value = 1
            elif "interception" in stat_type or "fumble" in stat_type:
                stat_value = random.randint(0, 1)
            elif "reception" in stat_type:
                stat_value = 1
            elif stat_type.startswith("field_goal"):
                stat_value = 1
            elif stat_type == "extra_points":
                stat_value = 1
            elif stat_type == "sacks":
                stat_value = 1
            else:
                stat_value = random.randint(1, 3)
            
            event = {
                "event_id": str(uuid.uuid4()),
                "player_id": player_id,
                "stat_type": stat_type,
                "stat_value": stat_value,
                "game_id": f"MOCK-GAME-{random.randint(1, 3)}",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "description": f"{player_id} {stat_type.replace('_', ' ')}: {stat_value}",
            }
            
            # Only add if not recently processed
            if event["event_id"] not in self.processed_stat_ids:
                events.append(event)
                self.processed_stat_ids.add(event["event_id"])
        
        return events
    
    async def _process_stat_event(self, stat_event: Dict[str, Any]):
        """
        Process a single stat event and update fantasy scores.
        
        Args:
            stat_event: Stat event dictionary
        """
        logger.debug(f"Processing stat event: {stat_event.get('description', 'Unknown')}")
        
        # Create database session
        db_session = self.db_session_factory()
        
        try:
            # Get current week from league state
            # For now, assume week 1 for all leagues
            # TODO: Get actual current week from league settings
            week_number = 1
            
            # Find all active leagues
            from app.models.league import League, LeagueStatus
            
            active_leagues = db_session.query(League).filter(
                League.status.in_([LeagueStatus.ACTIVE, LeagueStatus.PLAYOFFS])
            ).all()
            
            for league in active_leagues:
                # Process stat for this league
                result = ScoringService.process_live_stat_update(
                    stat_event=stat_event,
                    league_id=league.id,
                    week_number=week_number,
                    db_session=db_session
                )
                
                # Update matchup scores for impacted teams
                if result["impacted_teams"]:
                    await self._update_matchup_scores(
                        result["impacted_teams"], db_session
                    )
            
            db_session.commit()
            logger.info(f"Processed stat event for {len(active_leagues)} leagues")
            
        except Exception as e:
            logger.error(f"Error processing stat event: {e}")
            db_session.rollback()
        finally:
            db_session.close()
    
    async def _update_matchup_scores(
        self,
        impacted_teams: List[Dict[str, Any]],
        db_session: Session
    ):
        """
        Update matchup scores based on impacted teams.
        
        Args:
            impacted_teams: List of teams impacted by stat update
            db_session: Database session
        """
        from app.models.matchup import Matchup
        
        for team_info in impacted_teams:
            matchup = db_session.query(Matchup).filter_by(
                id=team_info["matchup_id"]
            ).first()
            
            if not matchup:
                continue
            
            # Update score based on home/away team
            if team_info["is_home_team"]:
                matchup.home_score += team_info["points_added"]
            else:
                matchup.away_score += team_info["points_added"]
            
            # Update matchup status if not already in progress
            if matchup.status.value == "scheduled":
                from app.models.matchup import MatchupStatus
                matchup.status = MatchupStatus.IN_PROGRESS
            
            logger.debug(
                f"Updated {team_info['team_name']} score: "
                f"+{team_info['points_added']:.2f} points "
                f"(Total: {matchup.home_score if team_info['is_home_team'] else matchup.away_score:.2f})"
            )
    
    async def _cleanup_cache_loop(self):
        """Periodically clean up processed stat ID cache."""
        while self.is_running:
            await asyncio.sleep(300)  # Every 5 minutes
            
            # Simple cleanup: keep last 1000 events
            if len(self.processed_stat_ids) > 1000:
                # Convert to list, keep most recent
                ids_list = list(self.processed_stat_ids)
                self.processed_stat_ids = set(ids_list[-1000:])
                logger.debug(f"Cleaned stat ID cache: {len(self.processed_stat_ids)} entries")
    
    async def calculate_week_scores(self, league_id: str, week_number: int):
        """
        Calculate final scores for a week (batch processing).
        
        Args:
            league_id: League ID
            week_number: Week number to calculate
        """
        db_session = self.db_session_factory()
        
        try:
            from app.models.league import League
            from app.models.team import Team
            from app.models.matchup import Matchup, MatchupStatus
            
            league = db_session.query(League).filter_by(id=league_id).first()
            if not league:
                logger.error(f"League {league_id} not found")
                return
            
            # Get all matchups for this week
            matchups = db_session.query(Matchup).filter_by(
                league_id=league_id,
                week_number=week_number
            ).all()
            
            if not matchups:
                logger.info(f"No matchups found for league {league_id} week {week_number}")
                return
            
            # For each matchup, calculate scores from player stats
            for matchup in matchups:
                # Get teams
                home_team = db_session.query(Team).filter_by(id=matchup.home_team_id).first()
                away_team = db_session.query(Team).filter_by(id=matchup.away_team_id).first()
                
                if not home_team or not away_team:
                    continue
                
                # Generate mock stats for players in lineups
                all_player_ids = []
                if home_team.current_lineup:
                    all_player_ids.extend([pid for pid in home_team.current_lineup.values() if pid])
                if away_team.current_lineup:
                    all_player_ids.extend([pid for pid in away_team.current_lineup.values() if pid])
                
                # Remove duplicates
                all_player_ids = list(set(all_player_ids))
                
                # Get mock stats
                mock_stats = ScoringService.generate_mock_player_stats(
                    all_player_ids, week_number
                )
                
                # Calculate scores
                scoring_settings = league.settings.scoring_settings if league.settings else {}
                
                home_points = ScoringService.calculate_team_points_for_week(
                    home_team.current_lineup or {},
                    mock_stats,
                    scoring_settings
                )
                
                away_points = ScoringService.calculate_team_points_for_week(
                    away_team.current_lineup or {},
                    mock_stats,
                    scoring_settings
                )
                
                # Update matchup
                matchup.home_score = home_points
                matchup.away_score = away_points
                matchup.status = MatchupStatus.COMPLETED
                matchup.finalized_at = datetime.utcnow()
                
                logger.info(
                    f"Week {week_number} scores: "
                    f"{home_team.name} {home_points:.2f} - "
                    f"{away_team.name} {away_points:.2f}"
                )
            
            db_session.commit()
            logger.info(f"Calculated week {week_number} scores for league {league_id}")
            
        except Exception as e:
            logger.error(f"Error calculating week scores: {e}")
            db_session.rollback()
        finally:
            db_session.close()
    
    def get_live_scores(self, league_id: str) -> Dict[str, Any]:
        """
        Get current live scores for a league.
        
        Args:
            league_id: League ID
            
        Returns:
            Dictionary with current scores and matchups
        """
        db_session = self.db_session_factory()
        
        try:
            from app.models.matchup import Matchup, MatchupStatus
            from app.models.team import Team
            
            # Get current week (simplified - would come from league settings)
            current_week = 1
            
            matchups = db_session.query(Matchup).filter_by(
                league_id=league_id,
                week_number=current_week
            ).all()
            
            live_scores = {
                "league_id": league_id,
                "week": current_week,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "matchups": []
            }
            
            for matchup in matchups:
                home_team = db_session.query(Team).filter_by(id=matchup.home_team_id).first()
                away_team = db_session.query(Team).filter_by(id=matchup.away_team_id).first()
                
                matchup_data = {
                    "matchup_id": matchup.id,
                    "status": matchup.status.value,
                    "home_team": {
                        "team_id": matchup.home_team_id,
                        "name": home_team.name if home_team else "Unknown",
                        "score": matchup.home_score,
                        "projected_score": matchup.home_projected_score,
                    },
                    "away_team": {
                        "team_id": matchup.away_team_id,
                        "name": away_team.name if away_team else "Unknown",
                        "score": matchup.away_score,
                        "projected_score": matchup.away_projected_score,
                    },
                    "game_start": matchup.game_start_time.isoformat() if matchup.game_start_time else None,
                    "last_update": matchup.updated_at.isoformat() if matchup.updated_at else None,
                }
                
                live_scores["matchups"].append(matchup_data)
            
            return live_scores
            
        except Exception as e:
            logger.error(f"Error getting live scores: {e}")
            return {"error": str(e)}
        finally:
            db_session.close()