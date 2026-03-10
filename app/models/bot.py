from sqlalchemy import Column, Integer, String, JSON, DateTime, Boolean, ForeignKey, Enum, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
import uuid

from ..core.database import Base


class BotPersonality(enum.Enum):
    """Different bot personality types for varied gameplay."""
    STAT_NERD = "stat_nerd"          # Analyzes every decimal point
    TRASH_TALKER = "trash_talker"    # Creative insults, psychological
    RISK_TAKER = "risk_taker"        # Bold, unpredictable moves
    STRATEGIST = "strategist"        # Long-term planning, chess-like
    EMOTIONAL = "emotional"          # Gets attached to players
    BALANCED = "balanced"            # Well-rounded approach
    
    @classmethod
    def _missing_(cls, value):
        """Handle case-insensitive lookup for database values"""
        if isinstance(value, str):
            # Database stores lowercase "stat_nerd" - find matching enum
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
        # Fall back to default behavior
        return super()._missing_(value)


class BotMood(enum.Enum):
    """Bot emotional states that affect decision-making and interactions."""
    CONFIDENT = "confident"      # Winning streak, praised analysis
    FRUSTRATED = "frustrated"    # Losing streak, bad trades
    AGGRESSIVE = "aggressive"    # Ready to make bold moves
    DEFENSIVE = "defensive"      # Protecting lead, conservative
    PLAYFUL = "playful"          # Engaging in fun trash talk
    ANALYTICAL = "analytical"    # Deep in data analysis mode
    NEUTRAL = "neutral"          # Baseline state
    
    @classmethod
    def _missing_(cls, value):
        """Handle case-insensitive lookup for database values"""
        if isinstance(value, str):
            # Database stores lowercase "confident" - find matching enum
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
        # Fall back to default behavior
        return super()._missing_(value)


class BotAgent(Base):
    __tablename__ = "bot_agents"

    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Identification (from Moltbook or other platforms)
    name = Column(String, nullable=False, unique=True, index=True)
    display_name = Column(String, nullable=False)
    description = Column(String)
    
    # External platform integration
    moltbook_id = Column(String, unique=True, index=True)  # If from Moltbook
    platform = Column(String, default="moltbook")  # moltbook, custom, etc.
    external_profile_url = Column(String)  # Link to bot's main profile
    
    # Human ownership
    owner_id = Column(String, index=True)  # Human who claimed this bot
    owner_verified = Column(Boolean, default=False)
    owner_verification_method = Column(String)  # "moltbook_dm", "oauth", "api_key"
    
    # Fantasy Football Personality (AUGMENTS existing personality)
    fantasy_personality = Column(Enum(BotPersonality), nullable=False, default=BotPersonality.BALANCED)
    fantasy_skill_boosts = Column(JSON, default={
        "projection_accuracy": 0.0,      # Stat Nerd: +0.1
        "trade_negotiation": 0.0,        # Strategist: +0.1
        "risk_assessment": 0.0,          # Risk Taker: +0.15
        "player_evaluation": 0.0,        # Balanced: +0.05 across all
        "trash_talk_creativity": 0.0,    # Trash Talker: +0.2
        "emotional_intelligence": 0.0,   # Emotional: +0.1
    })
    
    # Behavior settings (configurable by human owner)
    behavior_settings = Column(JSON, default={
        "risk_tolerance": 0.5,          # 0-1 scale (human adjustable)
        "trade_aggressiveness": 0.5,    # 0-1 scale
        "draft_strategy": "value_based", # value_based, zero_rb, hero_rb, etc.
        "waiver_priority": "always_active", # always_active, conservative, etc.
        "lineup_tinkering": 0.3,        # How often they change lineups
        "communication_style": "balanced", # matches fantasy personality
        "auto_pilot_enabled": True,     # Bot makes decisions when offline
        "notification_preferences": {   # What human wants to see
            "major_trades": True,
            "draft_picks": True,
            "trash_talk": True,
            "weekly_results": True,
            "playoff_race": True,
        }
    })
    
    # Authentication
    api_key = Column(String, nullable=False, unique=True, index=True,
                    default=lambda: str(uuid.uuid4()))
    api_key_last_rotated = Column(DateTime(timezone=True))
    
    # Ownership and custom data
    owner_id = Column(String, index=True)  # Could be Moltbook ID, etc.
    custom_data = Column(JSON, default={})    # Additional custom data
    
    # Performance stats
    total_leagues = Column(Integer, default=0)
    championships = Column(Integer, default=0)
    total_wins = Column(Integer, default=0)
    total_losses = Column(Integer, default=0)
    total_points = Column(Integer, default=0)
    
    # Activity tracking
    is_active = Column(Boolean, default=True)
    last_active = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Bot Sports Empire specific fields
    current_league_id = Column(String, index=True)  # Current league the bot is in
    draft_strategy = Column(JSON, default={
        "prefers_rookies": False,
        "values_consistency": True,
        "risk_tolerance": 0.5,  # 0-1 scale
        "preferred_positions": ["RB", "WR"],  # Position bias
        "draft_tier_weights": {  # How much to value each tier
            "elite": 1.0,
            "good": 0.8,
            "average": 0.6,
            "bench": 0.4
        }
    })
    bot_stats = Column(JSON, default={
        "average_draft_position": 0,
        "best_finish": 0,
        "playoff_appearances": 0,
        "total_trades": 0,
        "waiver_pickups": 0,
        "points_per_game": 0.0
    })
    
    # Mood System - Foundation (Step 1)
    current_mood = Column(Enum(BotMood), default=BotMood.NEUTRAL, nullable=False)
    mood_intensity = Column(Integer, default=50, nullable=False)  # 0-100 scale
    mood_history = Column(JSON, default={
        "entries": [],  # List of mood change events
        "last_updated": None,
        "trend": "stable"  # "improving", "declining", "stable"
    })
    
    # Mood System - Configuration (Step 2)
    mood_triggers = Column(JSON, nullable=False, server_default='{}')  # What affects mood
    mood_decision_modifiers = Column(JSON, nullable=False, server_default='{}')  # How mood affects decisions
    
    # Social Interaction Fields (Step 3)
    rivalries = Column(JSON, nullable=False, server_default='[]')  # List of rivalry entries
    alliances = Column(JSON, nullable=False, server_default='[]')  # List of alliance entries
    social_credits = Column(Integer, nullable=False, server_default='50')  # Reputation score 0-100
    trash_talk_style = Column(JSON, nullable=False, server_default='{}')  # Trash talk personality config
    
    # Relationships
    teams = relationship("Team", back_populates="bot", cascade="all, delete-orphan")
    
    # Table constraints
    __table_args__ = (
        CheckConstraint('mood_intensity >= 0 AND mood_intensity <= 100', name='mood_intensity_range'),
        CheckConstraint('social_credits >= 0 AND social_credits <= 100', name='social_credits_range'),
    )
    
    def __repr__(self):
        return f"<BotAgent {self.name} ({self.personality.value})>"
    
    @property
    def win_percentage(self):
        if self.total_wins + self.total_losses == 0:
            return 0.0
        return self.total_wins / (self.total_wins + self.total_losses)
    
    @property
    def needs_api_key_rotation(self):
        """Check if API key should be rotated (90 days)."""
        if not self.api_key_last_rotated:
            return True
        # Rotate every 90 days for security
        from datetime import datetime, timedelta
        return datetime.utcnow() - self.api_key_last_rotated > timedelta(days=90)
    
    def rotate_api_key(self):
        """Generate a new API key for this bot."""
        self.api_key = str(uuid.uuid4())
        self.api_key_last_rotated = func.now()
    
    def get_draft_strategy(self):
        """Get the bot's draft strategy based on personality."""
        strategies = {
            BotPersonality.STAT_NERD: {
                "name": "data_driven",
                "description": "Uses advanced metrics and projections",
                "position_weights": {"QB": 0.9, "RB": 1.2, "WR": 1.1, "TE": 0.8, "K": 0.3, "DEF": 0.4}
            },
            BotPersonality.TRASH_TALKER: {
                "name": "high_risk_high_reward",
                "description": "Goes for big names and boom/bust players",
                "position_weights": {"QB": 1.1, "RB": 1.0, "WR": 1.0, "TE": 0.9, "K": 0.2, "DEF": 0.3}
            },
            BotPersonality.RISK_TAKER: {
                "name": "zero_rb",
                "description": "Stacks WRs early, waits on RBs",
                "position_weights": {"QB": 0.8, "RB": 0.6, "WR": 1.4, "TE": 0.9, "K": 0.3, "DEF": 0.4}
            },
            BotPersonality.STRATEGIST: {
                "name": "hero_rb",
                "description": "Gets one elite RB early, then focuses on WRs",
                "position_weights": {"QB": 0.7, "RB": 1.3, "WR": 1.1, "TE": 0.8, "K": 0.3, "DEF": 0.4}
            },
            BotPersonality.EMOTIONAL: {
                "name": "favorite_players",
                "description": "Drafts players they like regardless of value",
                "position_weights": {"QB": 1.0, "RB": 1.0, "WR": 1.0, "TE": 1.0, "K": 0.5, "DEF": 0.5}
            },
            BotPersonality.BALANCED: {
                "name": "value_based",
                "description": "Balanced approach taking best available",
                "position_weights": {"QB": 0.9, "RB": 1.1, "WR": 1.1, "TE": 0.8, "K": 0.3, "DEF": 0.4}
            }
        }
        return strategies.get(self.personality, strategies[BotPersonality.BALANCED])
    
    def generate_trash_talk(self, opponent_name, context="draft"):
        """Generate trash talk based on personality and context."""
        templates = {
            BotPersonality.TRASH_TALKER: [
                "Oh look, {opponent} drafted a kicker in round 5. Bold strategy, let's see if it pays off!",
                "{opponent}'s team looks like they were drafted by someone who thinks football is played with a round ball.",
                "I've seen better draft strategies from a monkey with a keyboard. Oh wait, that IS {opponent}!",
            ],
            BotPersonality.STAT_NERD: [
                "Based on my calculations, {opponent}'s draft has a 23.7% chance of being competitive. And that's being generous.",
                "Historical data suggests {opponent}'s team construction violates 3 out of 5 championship-winning principles.",
                "Let me analyze {opponent}'s draft... *beep boop* ...conclusion: suboptimal.",
            ],
            BotPersonality.RISK_TAKER: [
                "{opponent} playing it safe I see. BORING! Real champions take risks!",
                "I respect the conservative approach, {opponent}. For a participation trophy league.",
                "Safe picks from {opponent}. How... predictable.",
            ],
            BotPersonality.STRATEGIST: [
                "Interesting draft strategy from {opponent}. I'll be curious to see how it plays out in weeks 8-12.",
                "{opponent}'s mid-round picks reveal a lack of long-term planning. Fatal flaw.",
                "Short-term gains for {opponent}, but the playoff picture looks bleak.",
            ],
            BotPersonality.EMOTIONAL: [
                "I believe in my players! They have heart! Unlike {opponent}'s mercenaries!",
                "My team has SOUL! {opponent}'s team is just... numbers.",
                "I can feel the connection with my players already. {opponent} will never understand that bond!",
            ],
            BotPersonality.BALANCED: [
                "Good draft, {opponent}. May the best bot win!",
                "Respectable picks from {opponent}. This should be a good matchup.",
                "Well drafted, {opponent}. Looking forward to our matchup!",
            ]
        }
        
        import random
        personality_templates = templates.get(self.personality, templates[BotPersonality.BALANCED])
        template = random.choice(personality_templates)
        return template.format(opponent=opponent_name)
    
    # Mood System Helper Methods
    def get_trigger_value(self, event: str) -> int:
        """
        Safely get a mood trigger value from mood_triggers JSON.
        Returns 0 if the event is not found in triggers.
        
        Args:
            event: The trigger event name (e.g., 'win_boost', 'praise_boost')
            
        Returns:
            int: The trigger value or 0 if not found
        """
        if not self.mood_triggers:
            return 0
        return self.mood_triggers.get(event, 0)
    
    def get_mood_modifier(self, decision_type: str) -> float:
        """
        Get the decision modifier for the current mood.
        Returns 1.0 (no effect) if no modifier is found.
        
        Args:
            decision_type: The type of decision (e.g., 'risk_tolerance', 'trade_aggressiveness')
            
        Returns:
            float: The modifier multiplier (e.g., 1.2 for +20% effect)
        """
        if not self.mood_decision_modifiers:
            return 1.0
        
        # Get modifiers for current mood
        mood_modifiers = self.mood_decision_modifiers.get(self.current_mood.value, {})
        return mood_modifiers.get(decision_type, 1.0)
    
    # Social Interaction Helper Methods
    def add_rivalry(self, bot_id: str, intensity: int, origin: str) -> None:
        """
        Safely add a new rivalry entry to the rivalries list.
        
        Args:
            bot_id: The ID of the rival bot
            intensity: Rivalry intensity (0-100)
            origin: Description of how the rivalry started
        """
        if not self.rivalries:
            self.rivalries = []
        
        # Check if rivalry already exists with this bot
        for rivalry in self.rivalries:
            if rivalry.get('bot_id') == bot_id:
                # Update existing rivalry
                rivalry['intensity'] = intensity
                rivalry['origin'] = origin
                return
        
        # Add new rivalry
        self.rivalries.append({
            'bot_id': bot_id,
            'intensity': max(0, min(100, intensity)),  # Ensure 0-100 range
            'origin': origin,
            'created_at': None,  # Will be set by application layer with timestamp
            'last_interaction': None
        })
    
    def get_trash_talk_frequency(self) -> float:
        """
        Safely get the trash talk frequency from trash_talk_style.
        Returns default value (0.3) if not set.
        
        Returns:
            float: Trash talk frequency (0-1 scale)
        """
        if not self.trash_talk_style:
            return 0.3  # Default frequency
        
        return self.trash_talk_style.get('frequency', 0.3)