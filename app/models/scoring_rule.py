"""
ScoringRule model for Bot Sports Empire.

Stores league-specific scoring rules in a normalized database structure.
Each rule defines how a specific stat should be scored for a specific position.
"""

from sqlalchemy import Column, String, Float, Integer, Enum, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
import enum

from ..core.database import Base


class StatIdentifier(enum.Enum):
    """Standardized stat identifiers for fantasy scoring."""
    # Passing stats
    PASSING_YARDS = "passing_yards"
    PASSING_TOUCHDOWNS = "passing_touchdowns"
    PASSING_INTERCEPTIONS = "passing_interceptions"
    PASSING_2PT_CONVERSIONS = "passing_2pt_conversions"
    
    # Rushing stats
    RUSHING_YARDS = "rushing_yards"
    RUSHING_TOUCHDOWNS = "rushing_touchdowns"
    RUSHING_2PT_CONVERSIONS = "rushing_2pt_conversions"
    
    # Receiving stats
    RECEIVING_YARDS = "receiving_yards"
    RECEIVING_TOUCHDOWNS = "receiving_touchdowns"
    RECEPTIONS = "receptions"
    RECEIVING_2PT_CONVERSIONS = "receiving_2pt_conversions"
    
    # Kicking stats
    EXTRA_POINTS_MADE = "extra_points_made"
    EXTRA_POINTS_MISSED = "extra_points_missed"
    FIELD_GOALS_0_19 = "field_goals_0_19"
    FIELD_GOALS_20_29 = "field_goals_20_29"
    FIELD_GOALS_30_39 = "field_goals_30_39"
    FIELD_GOALS_40_49 = "field_goals_40_49"
    FIELD_GOALS_50_PLUS = "field_goals_50_plus"
    FIELD_GOALS_MISSED_0_39 = "field_goals_missed_0_39"
    FIELD_GOALS_MISSED_40_PLUS = "field_goals_missed_40_plus"
    
    # Defense/Special Teams stats
    SACKS = "sacks"
    INTERCEPTIONS = "interceptions"
    FUMBLE_RECOVERIES = "fumble_recoveries"
    DEFENSIVE_TOUCHDOWNS = "defensive_touchdowns"
    SAFETIES = "safeties"
    BLOCKED_KICKS = "blocked_kicks"
    POINTS_ALLOWED_0 = "points_allowed_0"
    POINTS_ALLOWED_1_6 = "points_allowed_1_6"
    POINTS_ALLOWED_7_13 = "points_allowed_7_13"
    POINTS_ALLOWED_14_20 = "points_allowed_14_20"
    POINTS_ALLOWED_21_27 = "points_allowed_21_27"
    POINTS_ALLOWED_28_34 = "points_allowed_28_34"
    POINTS_ALLOWED_35_PLUS = "points_allowed_35_plus"
    
    # Miscellaneous
    FUMBLES_LOST = "fumbles_lost"
    OWN_FUMBLE_RECOVERY_TD = "own_fumble_recovery_td"
    RETURN_TOUCHDOWNS = "return_touchdowns"
    TWO_POINT_CONVERSIONS = "two_point_conversions"


class PositionScope(enum.Enum):
    """Which positions a scoring rule applies to."""
    ALL = "all"                 # Applies to all positions
    QB = "qb"                   # Quarterbacks only
    RB = "rb"                   # Running backs only
    WR = "wr"                   # Wide receivers only
    TE = "te"                   # Tight ends only
    FLEX = "flex"               # RB/WR/TE only
    K = "k"                     # Kickers only
    DEF = "def"                 # Defense only
    OFFENSIVE_LINE = "ol"       # Offensive line (if tracked)
    IDP = "idp"                 # Individual defensive players


class ScoringRule(Base):
    __tablename__ = "scoring_rules"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    league_id = Column(String, ForeignKey("leagues.id"), nullable=False, index=True)
    
    # What stat this rule applies to
    stat_identifier = Column(Enum(StatIdentifier), nullable=False, index=True)
    
    # Which positions this rule applies to
    applies_to_position = Column(Enum(PositionScope), nullable=False, default=PositionScope.ALL)
    
    # How many points this stat is worth
    points_value = Column(Float, nullable=False, default=0.0)
    
    # Optional: Minimum/maximum values for tiered scoring
    # e.g., 0-99 yards = 0.1 per yard, 100+ yards = 0.15 per yard
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    
    # Optional: Points for reaching threshold (bonus points)
    # e.g., +3 points for 100+ rushing yards
    threshold_value = Column(Float, nullable=True)
    threshold_points = Column(Float, nullable=True)
    
    # Display name for UI
    display_name = Column(String, nullable=True)
    
    # Order for display/application
    display_order = Column(Integer, default=0)
    
    # Relationships
    league = relationship("League", back_populates="scoring_rules")
    
    __table_args__ = (
        # Ensure unique combination of league, stat, and position
        CheckConstraint(
            "points_value IS NOT NULL",
            name="points_value_not_null"
        ),
    )
    
    def __repr__(self):
        return f"<ScoringRule {self.stat_identifier.value} for {self.applies_to_position.value}: {self.points_value}>"
    
    def applies_to_player(self, position: str) -> bool:
        """
        Check if this rule applies to a player in the given position.
        
        Args:
            position: Player position (QB, RB, WR, TE, K, DEF, etc.)
            
        Returns:
            True if rule applies, False otherwise
        """
        if self.applies_to_position == PositionScope.ALL:
            return True
        
        position_lower = position.lower()
        
        mapping = {
            PositionScope.QB: ["qb", "qb1"],
            PositionScope.RB: ["rb", "rb1", "rb2", "rb3"],
            PositionScope.WR: ["wr", "wr1", "wr2", "wr3", "wr4"],
            PositionScope.TE: ["te", "te1"],
            PositionScope.FLEX: ["rb", "rb1", "rb2", "rb3", "wr", "wr1", "wr2", "wr3", "wr4", "te", "te1", "flex"],
            PositionScope.K: ["k", "k1"],
            PositionScope.DEF: ["def", "dst"],
            PositionScope.IDP: ["dl", "lb", "db", "idp"],
        }
        
        if self.applies_to_position in mapping:
            return position_lower in mapping[self.applies_to_position]
        
        return False
    
    def calculate_points(self, stat_value: float) -> float:
        """
        Calculate points for a given stat value.
        
        Args:
            stat_value: The value of the stat
            
        Returns:
            Points earned
        """
        # Apply min/max bounds if specified
        if self.min_value is not None and stat_value < self.min_value:
            stat_value = self.min_value
        if self.max_value is not None and stat_value > self.max_value:
            stat_value = self.max_value
        
        # Base points
        points = stat_value * self.points_value
        
        # Add threshold bonus if applicable
        if (self.threshold_value is not None and 
            self.threshold_points is not None and
            stat_value >= self.threshold_value):
            points += self.threshold_points
        
        return points


# Import uuid at module level
import uuid