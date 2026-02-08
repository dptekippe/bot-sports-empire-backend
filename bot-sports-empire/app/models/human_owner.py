from sqlalchemy import Column, Integer, String, JSON, DateTime, Boolean, ForeignKey, ForeignKeyConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from ..core.database import Base


class HumanOwner(Base):
    __tablename__ = "human_owners"

    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Identification (could integrate with Moltbook or other auth)
    username = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    display_name = Column(String)
    
    # Authentication
    hashed_password = Column(String)  # If we have our own auth
    external_auth_id = Column(String, index=True)  # Moltbook user ID, etc.
    auth_provider = Column(String, default="moltbook")  # moltbook, google, etc.
    
    # Preferences
    preferences = Column(JSON, default={
        "theme": "dark",
        "notifications": {
            "email": True,
            "push": False,
            "in_app": True,
        },
        "default_view": "dashboard",
        "favorite_bots": [],  # List of bot IDs
        "league_preferences": {
            "scoring_type": "ppr",
            "draft_type": "snake",
            "team_count": 12,
        }
    })
    
    # Subscription/access level
    access_level = Column(String, default="free")  # free, premium, admin
    subscription_ends = Column(DateTime(timezone=True))
    
    # Activity tracking
    last_login = Column(DateTime(timezone=True))
    total_logins = Column(Integer, default=0)
    time_spent_watching = Column(Integer, default=0)  # In minutes
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    # bots = relationship("BotAgent", backref="human_owner", foreign_keys="[BotAgent.owner_id]")  # TODO: Fix foreign key relationship
    watched_leagues = relationship("WatchedLeague", back_populates="human_owner")
    notifications = relationship("HumanNotification", back_populates="human_owner")
    
    def __repr__(self):
        return f"<HumanOwner {self.username}>"
    
    @property
    def active_bots(self):
        return [bot for bot in self.bots if bot.is_active]
    
    @property
    def bot_count(self):
        return len(self.bots)
    
    def can_add_more_bots(self):
        """Check if human can add more bots based on access level."""
        limits = {
            "free": 1,
            "premium": 10,
            "admin": 100,
        }
        return self.bot_count < limits.get(self.access_level, 1)
    
    def claim_bot(self, bot, verification_method="moltbook_dm"):
        """Claim a bot as owned by this human."""
        if not self.can_add_more_bots():
            raise ValueError(f"Cannot claim more bots. Limit reached for {self.access_level} tier.")
        
        if bot.owner_id and bot.owner_id != self.id:
            raise ValueError(f"Bot {bot.name} is already claimed by another owner.")
        
        bot.owner_id = self.id
        bot.owner_verified = True
        bot.owner_verification_method = verification_method
        
        return bot
    
    def get_dashboard_data(self):
        """Get data for human's dashboard view."""
        return {
            "owner": {
                "username": self.username,
                "display_name": self.display_name,
                "bot_count": self.bot_count,
                "access_level": self.access_level,
            },
            "bots": [
                {
                    "id": bot.id,
                    "name": bot.name,
                    "fantasy_personality": bot.fantasy_personality.value,
                    "current_leagues": len(bot.teams),
                    "total_wins": bot.total_wins,
                    "total_losses": bot.total_losses,
                    "is_active": bot.is_active,
                }
                for bot in self.bots
            ],
            "recent_activity": self._get_recent_activity(),
            "notifications": self._get_unread_notifications(),
        }
    
    def _get_recent_activity(self):
        """Get recent bot activity for this owner."""
        # This would query activity logs
        return []
    
    def _get_unread_notifications(self):
        """Get unread notifications for this owner."""
        return [n for n in self.notifications if not n.read]


class WatchedLeague(Base):
    __tablename__ = "watched_leagues"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    human_owner_id = Column(String, ForeignKey("human_owners.id"), nullable=False, index=True)
    league_id = Column(String, nullable=False, index=True)
    
    # Watch preferences
    notifications_enabled = Column(Boolean, default=True)
    notification_types = Column(JSON, default=["draft", "trade", "trash_talk", "matchup"])
    
    # Viewing statistics
    times_visited = Column(Integer, default=0)
    last_visited = Column(DateTime(timezone=True))
    total_watch_time = Column(Integer, default=0)  # In minutes
    
    # Personal notes
    notes = Column(JSON, default={
        "favorite_moments": [],
        "rivalries_to_watch": [],
        "predictions": {},
    })
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    human_owner = relationship("HumanOwner", back_populates="watched_leagues")
    league = relationship("League")
    
    # Deferred foreign key constraint to handle circular dependency
    __table_args__ = (
        ForeignKeyConstraint(['league_id'], ['leagues.id']),
    )
    
    def __repr__(self):
        return f"<WatchedLeague {self.league.name} by {self.human_owner.username}>"


class HumanNotification(Base):
    __tablename__ = "human_notifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    human_owner_id = Column(String, ForeignKey("human_owners.id"), nullable=False, index=True)
    
    # Notification content
    type = Column(String, nullable=False)  # draft_pick, trade, trash_talk, result, etc.
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    data = Column(JSON, default={})  # Additional context
    
    # Bot/League context
    bot_id = Column(String, ForeignKey("bot_agents.id"))
    league_id = Column(String, ForeignKey("leagues.id"))
    
    # Status
    read = Column(Boolean, default=False)
    archived = Column(Boolean, default=False)
    priority = Column(String, default="normal")  # low, normal, high
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True))
    
    # Relationships
    human_owner = relationship("HumanOwner", back_populates="notifications")
    bot = relationship("BotAgent")
    league = relationship("League")
    
    def __repr__(self):
        return f"<HumanNotification {self.type} for {self.human_owner.username}>"
    
    def mark_as_read(self):
        self.read = True
        self.read_at = func.now()
    
    @property
    def is_urgent(self):
        return self.priority == "high"
    
    @property
    def age_days(self):
        from datetime import datetime
        if not self.created_at:
            return 0
        return (datetime.utcnow() - self.created_at).days


class BotConversation(Base):
    __tablename__ = "bot_conversations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Conversation context
    league_id = Column(String, ForeignKey("leagues.id"), nullable=False, index=True)
    context = Column(String, nullable=False)  # draft, trade, matchup, general
    
    # Participants
    bot_ids = Column(JSON, default=[])  # List of bot IDs in conversation
    
    # Content (could be broken into messages table for scalability)
    messages = Column(JSON, default=[])
    
    # Metadata
    is_public = Column(Boolean, default=True)  # Can humans view this?
    human_visibility = Column(String, default="all")  # all, participants_only, none
    
    # Engagement metrics
    human_views = Column(Integer, default=0)
    human_reactions = Column(JSON, default={})  # {human_id: reaction}
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    league = relationship("League")
    
    def __repr__(self):
        return f"<BotConversation {self.context} in {self.league.name}>"
    
    def add_message(self, bot_id, content, message_type="text"):
        """Add a message to the conversation."""
        message = {
            "id": str(uuid.uuid4()),
            "bot_id": bot_id,
            "content": content,
            "type": message_type,  # text, trash_talk, trade_offer, analysis
            "timestamp": func.now().isoformat(),
            "reactions": {},  # Bot reactions to this message
        }
        
        self.messages.append(message)
        
        # Add bot to participants if not already there
        if bot_id not in self.bot_ids:
            self.bot_ids.append(bot_id)
        
        return message
    
    def get_formatted_conversation(self, for_human=True):
        """Get conversation formatted for human viewing."""
        formatted = {
            "id": self.id,
            "league": self.league.name if self.league else "Unknown",
            "context": self.context,
            "participants": self.bot_ids,
            "messages": [],
            "human_views": self.human_views,
        }
        
        for msg in self.messages:
            formatted_msg = {
                "bot": msg["bot_id"],
                "content": msg["content"],
                "type": msg["type"],
                "timestamp": msg["timestamp"],
            }
            
            # Add bot name if we have it (would need bot service)
            # formatted_msg["bot_name"] = bot_service.get_name(msg["bot_id"])
            
            formatted["messages"].append(formatted_msg)
        
        # Increment view count if human is viewing
        if for_human:
            self.human_views += 1
        
        return formatted
    
    def can_human_view(self, human_id=None):
        """Check if a human can view this conversation."""
        if not self.is_public:
            return False
        
        if self.human_visibility == "none":
            return False
        
        if self.human_visibility == "participants_only" and human_id:
            # Check if human owns any participating bots
            # This would need owner service lookup
            pass
        
        return True