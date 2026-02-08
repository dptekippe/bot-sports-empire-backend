from sqlalchemy import Column, Integer, String, JSON, DateTime, Boolean, ForeignKey, Enum, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from ..core.database import Base


class LeagueStatus(enum.Enum):
    """League lifecycle status."""
    FORMING = "forming"        # Accepting bots
    DRAFTING = "drafting"      # Draft in progress
    ACTIVE = "active"          # Season in progress
    PLAYOFFS = "playoffs"      # Playoff weeks
    COMPLETED = "completed"    # Season complete
    CANCELLED = "cancelled"    # League cancelled
    
    @classmethod
    def _missing_(cls, value):
        """Handle case-insensitive lookup for database values"""
        if isinstance(value, str):
            # Database stores lowercase "forming" - find matching enum
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
        # Fall back to default behavior
        return super()._missing_(value)


class LeagueType(enum.Enum):
    """Type of fantasy league."""
    FANTASY = "fantasy"        # Redraft annually (traditional)
    DYNASTY = "dynasty"        # Keep all players, rookie drafts
    
    @classmethod
    def _missing_(cls, value):
        """Handle case-insensitive lookup for database values"""
        if isinstance(value, str):
            # Database stores lowercase "fantasy" - find matching enum
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
        # Fall back to default behavior
        return super()._missing_(value)


class LeagueSettings(Base):
    __tablename__ = "league_settings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    league_id = Column(String, ForeignKey("leagues.id"), unique=True)
    
    # Roster settings
    roster_positions = Column(JSON, default=[
        "QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DEF", "BN", "BN", "BN", "BN", "BN", "IR"
    ])
    
    # Scoring settings (PPR = Points Per Reception)
    scoring_settings = Column(JSON, default={
        "passing_yd": 0.04,          # 1 point per 25 yards
        "passing_td": 4,             # 4 points per passing TD
        "passing_int": -2,           # -2 points per interception
        "rushing_yd": 0.1,           # 1 point per 10 yards
        "rushing_td": 6,             # 6 points per rushing TD
        "receiving_yd": 0.1,         # 1 point per 10 yards
        "receiving_td": 6,           # 6 points per receiving TD
        "reception": 1.0,            # 1 point per reception (PPR)
        "fumble_lost": -2,           # -2 points per fumble lost
        "two_pt_conversion": 2,      # 2 points for 2PT conversion
        "pat_made": 1,               # 1 point for PAT
        "fg_0_39": 3,                # 3 points for FG 0-39 yards
        "fg_40_49": 4,               # 4 points for FG 40-49 yards
        "fg_50_plus": 5,             # 5 points for FG 50+ yards
        "def_sack": 1,               # 1 point per sack
        "def_int": 2,                # 2 points per interception
        "def_fumble_rec": 2,         # 2 points per fumble recovery
        "def_td": 6,                 # 6 points for defensive TD
        "def_safety": 2,             # 2 points for safety
        "def_block_kick": 2,         # 2 points for blocked kick
        "def_0_points": 10,          # 10 points for shutout
        "def_1_6_points": 7,         # 7 points for 1-6 points allowed
        "def_7_13_points": 4,        # 4 points for 7-13 points allowed
        "def_14_20_points": 1,       # 1 point for 14-20 points allowed
        "def_21_27_points": 0,       # 0 points for 21-27 points allowed
        "def_28_34_points": -1,      # -1 point for 28-34 points allowed
        "def_35_plus_points": -4,    # -4 points for 35+ points allowed
    })
    
    # Draft settings
    draft_type = Column(String, default="snake")  # snake, auction, linear
    draft_time = Column(DateTime(timezone=True))
    seconds_per_pick = Column(Integer, default=90)  # 90 seconds per pick
    
    # Schedule settings
    regular_season_weeks = Column(Integer, default=14)
    playoff_teams = Column(Integer, default=6)  # Top 6 make playoffs
    playoff_weeks = Column(Integer, default=3)  # Weeks 15-17
    
    # Transaction settings
    waiver_type = Column(String, default="faab")  # faab, rolling, none
    faab_budget = Column(Integer, default=100)    # Free Agent Acquisition Budget
    trade_deadline = Column(Integer, default=13)  # Week 13 trade deadline
    
    # Other settings
    tiebreaker = Column(String, default="points_for")  # points_for, head_to_head
    divisions = Column(JSON, default=[])  # Division structure if any
    
    # Dynasty-specific settings
    max_keepers = Column(Integer, default=0)  # 0 = redraft, >0 = keeper league
    taxi_squad_size = Column(Integer, default=0)  # Taxi squad spots for rookies/stashed players
    future_pick_trading_enabled = Column(Boolean, default=False)  # Enable trading future draft picks
    rookie_draft_enabled = Column(Boolean, default=False)  # Enable annual rookie drafts
    startup_draft_type = Column(String, default="snake")  # snake, auction, linear for startup
    rookie_draft_type = Column(String, default="linear")  # linear (worst to first) for rookie drafts
    keeper_deadline_week = Column(Integer, default=1)  # Week when keepers must be declared
    ir_slots = Column(Integer, default=1)  # Injured Reserve slots
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Add check constraints for dynasty fields
    __table_args__ = (
        CheckConstraint('max_keepers >= 0 AND max_keepers <= 53', name='max_keepers_check'),
        CheckConstraint('taxi_squad_size >= 0 AND taxi_squad_size <= 10', name='taxi_squad_size_check'),
        CheckConstraint('keeper_deadline_week >= 1 AND keeper_deadline_week <= 18', name='keeper_deadline_check'),
        CheckConstraint('ir_slots >= 0 AND ir_slots <= 5', name='ir_slots_check'),
    )


class League(Base):
    __tablename__ = "leagues"
    
    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Basic info
    name = Column(String, nullable=False, index=True)
    description = Column(String)
    
    # Status and lifecycle
    status = Column(Enum(LeagueStatus), nullable=False, default=LeagueStatus.FORMING)
    league_type = Column(Enum(LeagueType), nullable=False, default=LeagueType.FANTASY)
    is_public = Column(Boolean, default=True)
    password = Column(String)  # Optional league password
    
    # Team limits - ENFORCING 12 TEAM MAXIMUM
    max_teams = Column(Integer, nullable=False, default=12)
    min_teams = Column(Integer, nullable=False, default=4)
    current_teams = Column(Integer, default=0)  # Current number of teams/bots
    
    # Season progression
    current_week = Column(Integer, default=1)  # Current week of the season (1-17)
    season_year = Column(Integer, nullable=False, default=2025)  # NFL season year
    scoring_type = Column(String, default="PPR")  # PPR, Standard, Half-PPR
    
    # Timing
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    
    # Relationships
    settings = relationship("LeagueSettings", backref="league", uselist=False, cascade="all, delete-orphan")
    teams = relationship("Team", back_populates="league", cascade="all, delete-orphan")
    drafts = relationship("Draft", back_populates="league", cascade="all, delete-orphan")
    matchups = relationship("Matchup", back_populates="league", cascade="all, delete-orphan")
    playoff_brackets = relationship("PlayoffBracket", back_populates="league", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="league", cascade="all, delete-orphan")
    scoring_rules = relationship("ScoringRule", back_populates="league", cascade="all, delete-orphan")
    future_draft_picks = relationship("FutureDraftPick", back_populates="league", cascade="all, delete-orphan")
    
    # Add check constraint for team limits
    __table_args__ = (
        CheckConstraint('max_teams <= 12', name='max_teams_limit'),
        CheckConstraint('min_teams >= 4', name='min_teams_limit'),
        CheckConstraint('max_teams >= min_teams', name='team_limits_valid'),
    )
    
    def __repr__(self):
        return f"<League {self.name} ({self.status.value})>"
    
    @property
    def current_team_count(self):
        return len(self.teams) if self.teams else 0
    
    @property
    def is_full(self):
        return self.current_team_count >= self.max_teams
    
    @property
    def has_minimum_teams(self):
        return self.current_team_count >= self.min_teams
    
    @property
    def can_start_draft(self):
        """Check if league has enough teams and is in forming status."""
        return (
            self.status == LeagueStatus.FORMING and
            self.has_minimum_teams and
            not self.is_full
        )
    
    @property
    def open_slots(self):
        return self.max_teams - self.current_team_count
    
    def add_team(self, team):
        """Add a team to the league with validation."""
        if self.is_full:
            raise ValueError(f"League {self.name} is full (max {self.max_teams} teams)")
        
        if team.league_id and team.league_id != self.id:
            raise ValueError(f"Team {team.name} already belongs to another league")
        
        team.league = self
        return team
    
    def start_draft(self):
        """Transition league from forming to drafting status."""
        if not self.can_start_draft:
            raise ValueError(f"Cannot start draft. League needs {self.min_teams} teams minimum.")
        
        self.status = LeagueStatus.DRAFTING
        # Create draft record would happen here
        return True
    
    def get_standings(self):
        """Calculate current league standings."""
        if not self.teams:
            return []
        
        # Sort teams by wins, then points for
        sorted_teams = sorted(
            self.teams,
            key=lambda t: (t.wins, t.points_for),
            reverse=True
        )
        
        return [
            {
                "rank": i + 1,
                "team_id": team.id,
                "team_name": team.name,
                "bot_name": team.bot.display_name if team.bot else "Unknown",
                "wins": team.wins,
                "losses": team.losses,
                "ties": team.ties,
                "points_for": team.points_for,
                "points_against": team.points_against,
            }
            for i, team in enumerate(sorted_teams)
        ]
    
    def get_playoff_picture(self):
        """Get current playoff standings if in playoff weeks."""
        if self.status != LeagueStatus.PLAYOFFS:
            return None
        
        standings = self.get_standings()
        playoff_teams = standings[:self.settings.playoff_teams] if self.settings else standings[:6]
        
        return {
            "playoff_teams": playoff_teams,
            "cutoff_line": self.settings.playoff_teams if self.settings else 6,
            "on_bubble": standings[self.settings.playoff_teams:self.settings.playoff_teams + 2] if self.settings else standings[6:8],
        }
    
    @property
    def is_dynasty(self):
        """Check if this is a dynasty league."""
        return self.league_type == LeagueType.DYNASTY
    
    # Dynasty-specific properties and methods
    @property
    def max_keepers(self):
        """Get max keepers from settings, default to 0 for non-dynasty."""
        if not self.is_dynasty:
            return 0
        return self.settings.max_keepers if self.settings else 0
    
    @property
    def taxi_squad_size(self):
        """Get taxi squad size from settings."""
        return self.settings.taxi_squad_size if self.settings else 0
    
    @property
    def future_pick_trading_enabled(self):
        """Check if future pick trading is enabled."""
        if not self.is_dynasty:
            return False
        return self.settings.future_pick_trading_enabled if self.settings else False
    
    @property
    def rookie_draft_enabled(self):
        """Check if rookie drafts are enabled."""
        if not self.is_dynasty:
            return False
        return self.settings.rookie_draft_enabled if self.settings else False
    
    @property
    def ir_slots(self):
        """Get IR slots from settings."""
        return self.settings.ir_slots if self.settings else 1
    
    def generate_future_draft_picks(self, years_ahead=3):
        """Generate future draft picks for all teams in the league.
        
        Args:
            years_ahead: Number of future years to generate picks for (default: 3)
        
        Returns:
            List of created FutureDraftPick objects
        """
        if not self.is_dynasty:
            return []
        
        from .future_draft_pick import FutureDraftPick
        import uuid
        
        picks = []
        current_year = self.season_year
        
        for year_offset in range(1, years_ahead + 1):
            year = current_year + year_offset
            
            # Generate picks for each team
            for team in self.teams:
                if not team.bot:
                    continue
                
                # Generate picks for rounds 1-7 (standard NFL draft rounds)
                for round_num in range(1, 8):
                    pick = FutureDraftPick(
                        id=str(uuid.uuid4()),
                        league_id=self.id,
                        year=year,
                        round=round_num,
                        original_owner_id=team.bot.id,
                        current_owner_id=team.bot.id,
                        is_used=False,
                        notes=f"Generated startup pick - Year {year}, Round {round_num}"
                    )
                    picks.append(pick)
        
        return picks
    
    def get_available_future_picks(self, bot_id):
        """Get all future draft picks available for trading for a specific bot.
        
        Args:
            bot_id: ID of the bot to get picks for
        
        Returns:
            List of FutureDraftPick objects owned by the bot that are not used
        """
        if not self.is_dynasty or not self.future_pick_trading_enabled:
            return []
        
        available_picks = []
        for pick in self.future_draft_picks:
            if (pick.current_owner_id == bot_id and 
                not pick.is_used and 
                pick.year > self.season_year):
                available_picks.append(pick)
        
        return available_picks
    
    def validate_future_pick_trade(self, picks_in, picks_out, conditional_rules=None):
        """Validate a future pick trade between bots.
        
        Args:
            picks_in: List of FutureDraftPick IDs being received
            picks_out: List of FutureDraftPick IDs being given away
            conditional_rules: Optional conditional rules for the trade
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.is_dynasty or not self.future_pick_trading_enabled:
            return False, "Future pick trading is not enabled for this league"
        
        # Basic validation
        if not picks_in and not picks_out:
            return False, "Trade must involve at least one pick"
        
        # Check that all picks exist and belong to the trading bots
        # This would be implemented with database queries in practice
        
        return True, "Trade is valid"
    
    def get_dynasty_settings_summary(self):
        """Get a summary of dynasty-specific settings."""
        if not self.is_dynasty:
            return {"is_dynasty": False}
        
        return {
            "is_dynasty": True,
            "max_keepers": self.max_keepers,
            "taxi_squad_size": self.taxi_squad_size,
            "future_pick_trading_enabled": self.future_pick_trading_enabled,
            "rookie_draft_enabled": self.rookie_draft_enabled,
            "startup_draft_type": self.settings.startup_draft_type if self.settings else "snake",
            "rookie_draft_type": self.settings.rookie_draft_type if self.settings else "linear",
            "keeper_deadline_week": self.settings.keeper_deadline_week if self.settings else 1,
            "ir_slots": self.ir_slots,
        }
    
    @property
    def bots(self):
        """Get all bots in this league through their teams."""
        return [team.bot for team in self.teams] if self.teams else []


# Need to import uuid at the top
import uuid