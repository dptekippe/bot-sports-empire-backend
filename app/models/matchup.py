from sqlalchemy import Column, Integer, String, JSON, DateTime, Boolean, ForeignKey, Enum, Float, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from ..core.database import Base
import uuid


class MatchupStatus(enum.Enum):
    """Matchup lifecycle status."""
    SCHEDULED = "scheduled"      # Matchup scheduled but not played
    IN_PROGRESS = "in_progress"  # Week is active, scores updating
    COMPLETED = "completed"      # Week complete, final scores set
    CANCELLED = "cancelled"      # Matchup cancelled


class Matchup(Base):
    __tablename__ = "matchups"

    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # League and week context
    league_id = Column(String, ForeignKey("leagues.id"), nullable=False, index=True)
    week_number = Column(Integer, nullable=False)  # Week 1-17 (or playoff week)
    is_playoff = Column(Boolean, default=False)    # Is this a playoff matchup?
    playoff_round = Column(Integer)                # Round 1, 2, 3 (championship)
    
    # Teams in the matchup
    home_team_id = Column(String, ForeignKey("teams.id"), nullable=False, index=True)
    away_team_id = Column(String, ForeignKey("teams.id"), nullable=False, index=True)
    
    # Scores
    home_score = Column(Float, default=0.0)
    away_score = Column(Float, default=0.0)
    
    # Status
    status = Column(Enum(MatchupStatus), nullable=False, default=MatchupStatus.SCHEDULED)
    
    # Projected scores (for pre-game analysis)
    home_projected_score = Column(Float)
    away_projected_score = Column(Float)
    
    # Game details
    game_start_time = Column(DateTime(timezone=True))  # When the NFL games start
    game_end_time = Column(DateTime(timezone=True))    # When all games are complete
    
    # Metadata
    matchup_metadata = Column("metadata", JSON, default={
        "notes": "",                    # Commissioner notes
        "highlight_players": [],        # Key players to watch
        "trash_talk": [],               # Bot trash talk during the week
        "weather_impact": None,         # Weather conditions affecting games
        "injury_report": {},            # Key injuries for this matchup
        "projection_accuracy": None,    # How accurate were projections
    })
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    finalized_at = Column(DateTime(timezone=True))  # When scores were finalized
    
    # Relationships
    league = relationship("League", back_populates="matchups")
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matchups")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matchups")
    
    # Composite index for league/week lookups
    __table_args__ = (
        Index('ix_matchups_league_week', 'league_id', 'week_number'),
        Index('ix_matchups_team_week', 'home_team_id', 'week_number'),
        Index('ix_matchups_team_week_away', 'away_team_id', 'week_number'),
    )
    
    def __repr__(self):
        return f"<Matchup Week {self.week_number}: {self.home_team_id[:8]} vs {self.away_team_id[:8]} ({self.status.value})>"
    
    @property
    def winner_id(self):
        """Get the winning team ID, or None if tie/not completed."""
        if self.status != MatchupStatus.COMPLETED:
            return None
        
        if self.home_score > self.away_score:
            return self.home_team_id
        elif self.away_score > self.home_score:
            return self.away_team_id
        else:
            return None  # Tie
    
    @property
    def loser_id(self):
        """Get the losing team ID, or None if tie/not completed."""
        if self.status != MatchupStatus.COMPLETED:
            return None
        
        if self.home_score < self.away_score:
            return self.home_team_id
        elif self.away_score < self.home_score:
            return self.away_team_id
        else:
            return None  # Tie
    
    @property
    def is_tie(self):
        """Check if the matchup resulted in a tie."""
        if self.status != MatchupStatus.COMPLETED:
            return False
        
        return self.home_score == self.away_score
    
    @property
    def margin_of_victory(self):
        """Get the margin of victory (absolute value)."""
        if self.status != MatchupStatus.COMPLETED:
            return None
        
        return abs(self.home_score - self.away_score)
    
    @property
    def total_points(self):
        """Get total points scored in the matchup."""
        return self.home_score + self.away_score
    
    def get_result_for_team(self, team_id):
        """Get result (W/L/T) for a specific team."""
        if self.status != MatchupStatus.COMPLETED:
            return None
        
        if team_id == self.home_team_id:
            if self.home_score > self.away_score:
                return "W"
            elif self.home_score < self.away_score:
                return "L"
            else:
                return "T"
        elif team_id == self.away_team_id:
            if self.away_score > self.home_score:
                return "W"
            elif self.away_score < self.home_score:
                return "L"
            else:
                return "T"
        
        return None
    
    def get_opponent_id(self, team_id):
        """Get the opponent team ID for a given team."""
        if team_id == self.home_team_id:
            return self.away_team_id
        elif team_id == self.away_team_id:
            return self.home_team_id
        return None
    
    def to_sleeper_format(self):
        """Convert to Sleeper-like format for API compatibility."""
        return {
            "matchup_id": self.id,
            "week": self.week_number,
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "status": self.status.value,
            "is_playoff": self.is_playoff,
            "playoff_round": self.playoff_round,
        }