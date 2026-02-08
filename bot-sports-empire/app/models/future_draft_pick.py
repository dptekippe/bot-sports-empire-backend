"""
FutureDraftPick model for Bot Sports Empire.

Represents future draft picks that can be traded in dynasty leagues.
These are valuable assets separate from players.
"""

from sqlalchemy import Column, String, Integer, JSON, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
import enum

from ..core.database import Base


class PickCondition(enum.Enum):
    """Possible conditions for draft picks."""
    UNCONDITIONAL = "unconditional"
    TOP_5_PROTECTED = "top_5_protected"  # If pick is top 5, becomes next year's 1st
    LOTTERY_PROTECTED = "lottery_protected"  # If pick is lottery (top 14), becomes next year's 1st
    PERFORMANCE_BASED = "performance_based"  # Based on player/stats performance


class FutureDraftPick(Base):
    __tablename__ = "future_draft_picks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Which league this pick belongs to
    league_id = Column(String, ForeignKey("leagues.id"), nullable=False, index=True)
    
    # Draft year and round
    year = Column(Integer, nullable=False, index=True)  # e.g., 2026, 2027, 2028
    round = Column(Integer, nullable=False)  # 1, 2, 3, 4, etc.
    
    # Pick number within round (optional, can be determined later)
    pick_number = Column(Integer, nullable=True)  # e.g., 1.01, 1.02, etc.
    
    # Ownership tracking
    original_owner_id = Column(String, ForeignKey("bot_agents.id"), nullable=False, index=True)
    current_owner_id = Column(String, ForeignKey("bot_agents.id"), nullable=False, index=True)
    
    # Conditional rules (JSON structure)
    conditional_rules = Column(JSON, nullable=True)
    
    # Status
    is_used = Column(Integer, default=0)  # 0 = available, 1 = used in draft, 2 = traded away and used
    used_in_draft_id = Column(String, ForeignKey("drafts.id"), nullable=True)  # Which draft it was used in
    
    # Notes
    notes = Column(String, nullable=True)
    
    # Relationships
    league = relationship("League", back_populates="future_draft_picks")
    original_owner = relationship("BotAgent", foreign_keys=[original_owner_id])
    current_owner = relationship("BotAgent", foreign_keys=[current_owner_id])
    draft = relationship("Draft", foreign_keys=[used_in_draft_id])
    
    __table_args__ = (
        # Ensure valid year (current year or future)
        CheckConstraint(
            "year >= 2025",
            name="future_pick_year_check"
        ),
        # Ensure valid round (typically 1-5 for fantasy)
        CheckConstraint(
            "round >= 1 AND round <= 7",
            name="future_pick_round_check"
        ),
        # Ensure pick number is valid if specified
        CheckConstraint(
            "pick_number IS NULL OR (pick_number >= 1 AND pick_number <= 32)",
            name="future_pick_number_check"
        ),
    )
    
    def __repr__(self):
        return f"<FutureDraftPick {self.year}.{self.round} (Owner: {self.current_owner_id})>"
    
    @property
    def display_name(self):
        """Get display name for the pick (e.g., '2026 1st', '2027 2nd')."""
        round_names = {
            1: "1st",
            2: "2nd", 
            3: "3rd",
            4: "4th",
            5: "5th",
            6: "6th",
            7: "7th"
        }
        round_name = round_names.get(self.round, f"{self.round}th")
        
        if self.pick_number:
            return f"{self.year} {round_name} (#{self.pick_number})"
        return f"{self.year} {round_name}"
    
    @property
    def is_conditional(self):
        """Check if this pick has conditional rules."""
        return bool(self.conditional_rules)
    
    @property
    def is_available(self):
        """Check if this pick is available for trading/use."""
        return self.is_used == 0
    
    @property
    def is_tradable(self):
        """Check if this pick can be traded."""
        return self.is_available and not self.is_conditional
    
    def get_conditional_description(self):
        """Get human-readable description of conditional rules."""
        if not self.conditional_rules:
            return "Unconditional"
        
        rules = self.conditional_rules
        if rules.get("type") == "top_protected":
            protected_range = rules.get("protected_range", 5)
            becomes = rules.get("becomes", "next year's 1st")
            return f"Top-{protected_range} protected → {becomes}"
        elif rules.get("type") == "performance":
            player_id = rules.get("player_id")
            stat = rules.get("stat")
            threshold = rules.get("threshold")
            upgrade_to = rules.get("upgrade_to", "1st")
            return f"If {player_id} gets {threshold}+ {stat} → becomes {upgrade_to}"
        
        return "Conditional (complex)"
    
    def resolve_condition(self, context: dict) -> dict:
        """
        Resolve conditional pick based on context.
        
        Args:
            context: Dictionary with data needed to resolve conditions
                - "standings": League standings for protected picks
                - "player_stats": Player stats for performance conditions
        
        Returns:
            Dictionary with resolution result
        """
        if not self.conditional_rules:
            return {"resolved": True, "pick": self}
        
        rules = self.conditional_rules
        if rules.get("type") == "top_protected":
            standings = context.get("standings", [])
            protected_range = rules.get("protected_range", 5)
            
            # Find where original owner finished
            owner_standing = None
            for standing in standings:
                if standing.get("team_id") == self.original_owner_id:
                    owner_standing = standing
                    break
            
            if owner_standing and owner_standing.get("rank", 99) <= protected_range:
                # Pick is protected - create new pick for next year
                return {
                    "resolved": True,
                    "protected": True,
                    "new_pick": {
                        "year": self.year + 1,
                        "round": rules.get("becomes_round", 1),
                        "original_owner_id": self.original_owner_id,
                        "current_owner_id": self.current_owner_id,
                        "conditional_rules": None
                    }
                }
        
        # Default: condition not met, pick stands as is
        return {"resolved": True, "pick": self, "condition_met": False}


# Import uuid at module level
import uuid