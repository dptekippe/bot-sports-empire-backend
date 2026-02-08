"""
Draft Analytics Service for Bot Sports Empire.

Tracks internal draft picks, calculates community ADP, and provides insights
on draft trends within our bot community.

This service enables the "internal ADP evolution" vision where our bot
community's draft decisions create our own ADP data over time.
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
import statistics

from ..core.database import SessionLocal
from ..models.draft import Draft, DraftPick
from ..models.draft_history import DraftHistory
from ..models.player import Player
from ..models.league import League

logger = logging.getLogger(__name__)


class DraftAnalyticsService:
    """Service for tracking draft analytics and internal ADP evolution."""
    
    def __init__(self, db: Optional[Session] = None):
        self.db = db or SessionLocal()
    
    def record_internal_draft_pick(
        self,
        draft_pick: DraftPick,
        draft: Draft,
        league: Optional[League] = None
    ) -> DraftHistory:
        """
        Record an internal draft pick to DraftHistory.
        
        This should be called whenever a pick is made in our platform.
        Creates a DraftHistory record with type='internal' to track
        our community's actual draft decisions.
        
        Args:
            draft_pick: The DraftPick object that was just made
            draft: The Draft object containing the draft
            league: Optional League object for context
            
        Returns:
            Created DraftHistory record
        """
        try:
            # Get current year for draft context
            current_year = datetime.now().year
            
            # Create draft history record
            draft_history = DraftHistory(
                player_id=draft_pick.player_id,
                draft_year=current_year,
                draft_type='internal',
                league_id=league.id if league else None,
                draft_id=draft.id,
                pick_number=draft_pick.pick_number,
                round=draft_pick.round,
                team_id=draft_pick.team_id,
                # These fields are for external ADP, leave null for internal
                adp_value=None,
                adp_source=None,
                scoring_format=None,
                team_count=None
            )
            
            self.db.add(draft_history)
            self.db.commit()
            self.db.refresh(draft_history)
            
            logger.info(f"Recorded internal draft pick: {draft_pick.player_id} at pick {draft_pick.pick_number}")
            return draft_history
            
        except Exception as e:
            logger.error(f"Error recording internal draft pick: {e}")
            self.db.rollback()
            raise
    
    def calculate_player_internal_adp(
        self,
        player_id: str,
        year: Optional[int] = None,
        league_type: Optional[str] = None,
        min_picks: int = 3
    ) -> Optional[float]:
        """
        Calculate internal ADP for a player based on our community's drafts.
        
        Args:
            player_id: Player ID to calculate ADP for
            year: Optional year filter (defaults to current year)
            league_type: Optional filter by league type ('fantasy', 'dynasty')
            min_picks: Minimum number of picks required to calculate ADP
            
        Returns:
            Average draft position (ADP) or None if insufficient data
        """
        try:
            # Build query for internal draft picks of this player
            query = self.db.query(DraftHistory).filter(
                DraftHistory.player_id == player_id,
                DraftHistory.draft_type == 'internal',
                DraftHistory.pick_number.isnot(None)
            )
            
            if year:
                query = query.filter(DraftHistory.draft_year == year)
            
            if league_type and league_type in ['fantasy', 'dynasty']:
                # Join with leagues to filter by league_type
                query = query.join(League, DraftHistory.league_id == League.id)
                query = query.filter(League.league_type == league_type)
            
            # Get all pick numbers
            picks = query.all()
            
            if len(picks) < min_picks:
                logger.debug(f"Insufficient picks for player {player_id}: {len(picks)} < {min_picks}")
                return None
            
            # Calculate average pick number
            pick_numbers = [pick.pick_number for pick in picks]
            average_adp = statistics.mean(pick_numbers)
            
            logger.debug(f"Calculated internal ADP for {player_id}: {average_adp} from {len(picks)} picks")
            return round(average_adp, 2)
            
        except Exception as e:
            logger.error(f"Error calculating internal ADP for player {player_id}: {e}")
            return None
    
    def get_draft_trends(
        self,
        year: Optional[int] = None,
        league_type: Optional[str] = None,
        position: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get draft trends and insights from our community's drafts.
        
        Args:
            year: Optional year filter
            league_type: Optional filter by league type
            position: Optional filter by player position
            limit: Maximum number of trends to return
            
        Returns:
            List of draft trend dictionaries
        """
        try:
            # Build base query for internal draft picks
            query = self.db.query(
                DraftHistory.player_id,
                func.count(DraftHistory.id).label('pick_count'),
                func.avg(DraftHistory.pick_number).label('avg_adp'),
                func.min(DraftHistory.pick_number).label('earliest_pick'),
                func.max(DraftHistory.pick_number).label('latest_pick')
            ).filter(
                DraftHistory.draft_type == 'internal',
                DraftHistory.pick_number.isnot(None)
            )
            
            if year:
                query = query.filter(DraftHistory.draft_year == year)
            
            # Join with players for position filtering
            query = query.join(Player, DraftHistory.player_id == Player.player_id)
            
            if position:
                query = query.filter(Player.position == position)
            
            if league_type and league_type in ['fantasy', 'dynasty']:
                query = query.join(League, DraftHistory.league_id == League.id)
                query = query.filter(League.league_type == league_type)
            
            # Group by player and order by pick count (most drafted first)
            query = query.group_by(DraftHistory.player_id)
            query = query.order_by(desc('pick_count'))
            query = query.limit(limit)
            
            results = query.all()
            
            # Format results
            trends = []
            for result in results:
                trend = {
                    'player_id': result.player_id,
                    'pick_count': result.pick_count,
                    'internal_adp': round(result.avg_adp, 2) if result.avg_adp else None,
                    'adp_range': f"{result.earliest_pick}-{result.latest_pick}",
                    'consistency': round(result.latest_pick - result.earliest_pick, 2) if result.latest_pick and result.earliest_pick else None
                }
                trends.append(trend)
            
            logger.info(f"Generated {len(trends)} draft trends")
            return trends
            
        except Exception as e:
            logger.error(f"Error getting draft trends: {e}")
            return []
    
    def compare_internal_vs_external_adp(
        self,
        player_id: str,
        year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Compare internal ADP (our community) vs external ADP (sources like FFC).
        
        Args:
            player_id: Player ID to compare
            year: Optional year filter
            
        Returns:
            Dictionary with comparison data
        """
        try:
            comparison = {
                'player_id': player_id,
                'year': year or datetime.now().year,
                'internal_adp': None,
                'external_adp': None,
                'adp_difference': None,
                'internal_pick_count': 0,
                'external_source_count': 0
            }
            
            # Get internal ADP
            internal_adp = self.calculate_player_internal_adp(player_id, year)
            if internal_adp:
                comparison['internal_adp'] = internal_adp
            
            # Get internal pick count
            internal_query = self.db.query(DraftHistory).filter(
                DraftHistory.player_id == player_id,
                DraftHistory.draft_type == 'internal',
                DraftHistory.pick_number.isnot(None)
            )
            if year:
                internal_query = internal_query.filter(DraftHistory.draft_year == year)
            
            comparison['internal_pick_count'] = internal_query.count()
            
            # Get latest external ADP
            external_query = self.db.query(DraftHistory).filter(
                DraftHistory.player_id == player_id,
                DraftHistory.draft_type == 'external',
                DraftHistory.adp_value.isnot(None)
            )
            if year:
                external_query = external_query.filter(DraftHistory.draft_year == year)
            
            external_query = external_query.order_by(desc(DraftHistory.created_at))
            external_record = external_query.first()
            
            if external_record:
                comparison['external_adp'] = external_record.adp_value
                comparison['external_source'] = external_record.adp_source
                comparison['external_scoring_format'] = external_record.scoring_format
                comparison['external_team_count'] = external_record.team_count
            
            # Get external source count
            external_count_query = self.db.query(DraftHistory).filter(
                DraftHistory.player_id == player_id,
                DraftHistory.draft_type == 'external'
            )
            if year:
                external_count_query = external_count_query.filter(DraftHistory.draft_year == year)
            
            comparison['external_source_count'] = external_count_query.count()
            
            # Calculate ADP difference if both exist
            if comparison['internal_adp'] and comparison['external_adp']:
                comparison['adp_difference'] = round(
                    comparison['internal_adp'] - comparison['external_adp'], 
                    2
                )
                comparison['adp_difference_abs'] = abs(comparison['adp_difference'])
                
                # Determine if our community values player differently
                if comparison['adp_difference'] < -3:
                    comparison['community_valuation'] = 'higher'  # Drafted earlier than external
                elif comparison['adp_difference'] > 3:
                    comparison['community_valuation'] = 'lower'   # Drafted later than external
                else:
                    comparison['community_valuation'] = 'similar'
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing ADP for player {player_id}: {e}")
            return {'player_id': player_id, 'error': str(e)}
    
    def get_community_draft_insights(
        self,
        year: Optional[int] = None,
        min_picks_per_player: int = 5
    ) -> Dict[str, Any]:
        """
        Get high-level insights about our community's draft behavior.
        
        Args:
            year: Optional year filter
            min_picks_per_player: Minimum picks to consider a player "consistently drafted"
            
        Returns:
            Dictionary with community insights
        """
        try:
            insights = {
                'year': year or datetime.now().year,
                'total_internal_picks': 0,
                'unique_players_drafted': 0,
                'unique_leagues': 0,
                'unique_drafts': 0,
                'most_drafted_players': [],
                'biggest_adp_differences': [],
                'position_distribution': {},
                'draft_completion_rate': None
            }
            
            # Build base query for internal picks
            query = self.db.query(DraftHistory).filter(
                DraftHistory.draft_type == 'internal',
                DraftHistory.pick_number.isnot(None)
            )
            
            if year:
                query = query.filter(DraftHistory.draft_year == year)
            
            # Get total picks
            insights['total_internal_picks'] = query.count()
            
            # Get unique players
            unique_players = query.distinct(DraftHistory.player_id).count()
            insights['unique_players_drafted'] = unique_players
            
            # Get unique leagues and drafts
            unique_leagues = query.distinct(DraftHistory.league_id).count()
            unique_drafts = query.distinct(DraftHistory.draft_id).count()
            insights['unique_leagues'] = unique_leagues
            insights['unique_drafts'] = unique_drafts
            
            # Get most drafted players
            player_counts = self.db.query(
                DraftHistory.player_id,
                func.count(DraftHistory.id).label('pick_count')
            ).filter(
                DraftHistory.draft_type == 'internal',
                DraftHistory.pick_number.isnot(None)
            )
            
            if year:
                player_counts = player_counts.filter(DraftHistory.draft_year == year)
            
            player_counts = player_counts.group_by(DraftHistory.player_id)
            player_counts = player_counts.order_by(desc('pick_count'))
            player_counts = player_counts.limit(10)
            
            for result in player_counts.all():
                insights['most_drafted_players'].append({
                    'player_id': result.player_id,
                    'pick_count': result.pick_count
                })
            
            # Get position distribution
            position_query = self.db.query(
                Player.position,
                func.count(DraftHistory.id).label('pick_count')
            ).join(
                DraftHistory, DraftHistory.player_id == Player.player_id
            ).filter(
                DraftHistory.draft_type == 'internal',
                DraftHistory.pick_number.isnot(None)
            )
            
            if year:
                position_query = position_query.filter(DraftHistory.draft_year == year)
            
            position_query = position_query.group_by(Player.position)
            
            for result in position_query.all():
                insights['position_distribution'][result.position] = result.pick_count
            
            logger.info(f"Generated community draft insights for {insights['year']}")
            return insights
            
        except Exception as e:
            logger.error(f"Error getting community draft insights: {e}")
            return {'error': str(e)}
    
    def update_player_internal_adp_field(
        self,
        player_id: str,
        year: Optional[int] = None
    ) -> bool:
        """
        Update a player's internal_adp field based on current community data.
        
        This should be called periodically to keep player.internal_adp current.
        
        Args:
            player_id: Player ID to update
            year: Optional year filter
            
        Returns:
            True if updated, False otherwise
        """
        try:
            # Calculate current internal ADP
            internal_adp = self.calculate_player_internal_adp(player_id, year, min_picks=1)
            
            # Find player
            player = self.db.query(Player).filter(Player.player_id == player_id).first()
            if not player:
                logger.warning(f"Player {player_id} not found for ADP update")
                return False
            
            # Update player record
            player.internal_adp = internal_adp
            player.internal_adp_updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Updated internal ADP for {player_id}: {internal_adp}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating internal ADP for player {player_id}: {e}")
            self.db.rollback()
            return False