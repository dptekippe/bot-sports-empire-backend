from sqlalchemy import Column, Integer, String, JSON, DateTime, Boolean, Float
from sqlalchemy.sql import func
from ..core.database import Base


class Player(Base):
    __tablename__ = "players"

    # Primary key from Sleeper API
    player_id = Column(String, primary_key=True, index=True)
    
    # Basic info
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    position = Column(String, nullable=False)  # QB, RB, WR, TE, K, DEF
    team = Column(String)  # Team abbreviation
    
    # Physical attributes
    height = Column(String)
    weight = Column(Integer)
    age = Column(Integer)
    college = Column(String)
    
    # Status
    status = Column(String)  # Active, Inactive, Injured
    injury_status = Column(String)
    injury_notes = Column(String)
    
    # Stats and metadata
    fantasy_positions = Column(JSON)  # List of positions
    stats = Column(JSON)  # Current season stats
    player_metadata = Column("metadata", JSON)  # Additional data from Sleeper (renamed to avoid conflict)
    
    # External IDs
    espn_id = Column(String)
    yahoo_id = Column(String)
    rotowire_id = Column(Integer)
    
    # Fantasy football specific fields
    current_team_id = Column(String, index=True)  # Which team owns this player
    draft_year = Column(Integer)  # Year player was drafted
    draft_round = Column(Integer)  # Round player was drafted (null for undrafted)
    bye_week = Column(Integer)  # Player's bye week
    average_draft_position = Column(Float)  # ADP for current season (internal/consensus)
    fantasy_pro_rank = Column(Integer)  # Expert ranking
    
    # External ADP data (from FantasyFootballCalculator, etc.)
    external_adp = Column(Float)  # External ADP value
    external_adp_source = Column(String)  # Source of external ADP
    external_adp_updated_at = Column(DateTime)  # When external ADP was last updated
    
    # Sleeper-specific fields
    active = Column(Boolean)  # Whether player is active in NFL
    years_exp = Column(Integer)  # Years of experience (from Sleeper)
    jersey_number = Column(Integer)  # Player's jersey number
    birth_date = Column(String)  # Birth date as string
    high_school = Column(String)  # High school attended
    depth_chart_position = Column(String)  # Depth chart position
    practice_description = Column(String)  # Practice status description
    team_abbr = Column(String)  # Team abbreviation (sometimes different)
    team_changed_at = Column(DateTime(timezone=True))  # When team changed
    sportradar_id = Column(String)  # Sportradar ID
    stats_id = Column(Integer)  # Stats ID
    fantasy_data_id = Column(Integer)  # FantasyData ID
    gsis_id = Column(String)  # NFL GSIS ID
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_stats_update = Column(DateTime(timezone=True))
    
    # Search optimization (already indexed in database)
    search_full_name = Column(String, index=True)
    search_first_name = Column(String, index=True)
    search_last_name = Column(String, index=True)
    
    def __repr__(self):
        return f"<Player {self.full_name} ({self.position} - {self.team})>"
    
    @property
    def display_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_active(self):
        return self.status == "Active"
    
    @property
    def is_injured(self):
        return self.injury_status in ["Questionable", "Doubtful", "Out"]