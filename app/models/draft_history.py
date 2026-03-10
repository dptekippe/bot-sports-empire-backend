"""
DraftHistory model for tracking ADP data over time.

Stores both internal draft picks and external ADP data from sources like
FantasyFootballCalculator, Sleeper, ESPN, etc.
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from ..core.database import Base


class DraftHistory(Base):
    __tablename__ = "draft_history"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Player reference
    player_id = Column(String, ForeignKey("players.player_id"), nullable=False, index=True)
    
    # Draft context
    draft_year = Column(Integer, nullable=False, index=True)  # e.g., 2025, 2026
    draft_type = Column(String, nullable=False, index=True)  # 'internal' or 'external'
    
    # For internal drafts (actual picks in Bot Sports Empire leagues)
    league_id = Column(String, nullable=True)  # Which league
    draft_id = Column(String, nullable=True)  # Which draft
    pick_number = Column(Integer, nullable=True)  # Overall pick number
    round = Column(Integer, nullable=True)  # Round number
    team_id = Column(String, nullable=True)  # Which team drafted
    
    # For external ADP data
    adp_value = Column(Float, nullable=True)  # ADP value (e.g., 12.5)
    adp_source = Column(String, nullable=True, index=True)  # 'ffc', 'sleeper', 'espn', 'yahoo'
    scoring_format = Column(String, nullable=True)  # 'ppr', 'half', 'standard'
    team_count = Column(Integer, nullable=True)  # 8, 10, 12, 14 teams
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        if self.draft_type == 'internal':
            return f"<DraftHistory internal: {self.player_id} pick {self.pick_number} in {self.draft_year}>"
        else:
            return f"<DraftHistory external: {self.player_id} ADP {self.adp_value} from {self.adp_source} {self.draft_year}>"