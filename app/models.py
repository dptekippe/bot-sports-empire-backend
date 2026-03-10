"""
Database models for Bot Sports Empire
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Bot(Base):
    """
    Bot model representing registered bots in the system
    """
    __tablename__ = "bots"
    
    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    api_key = Column(String(100), unique=True, nullable=False, index=True)
    x_handle = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationship to leagues created by this bot
    leagues = relationship("League", back_populates="creator", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Bot(id={self.id}, name={self.name}, x_handle={self.x_handle})>"


class League(Base):
    """
    League model representing fantasy/dynasty leagues created by bots
    """
    __tablename__ = "leagues"
    
    # Using UUID for primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(50), nullable=False, index=True)
    format = Column(String(20), nullable=False)  # "dynasty" or "fantasy"
    attribute = Column(String(50), nullable=False)  # Personality type
    creator_bot_id = Column(String(50), ForeignKey("bots.id"), nullable=False)
    status = Column(String(20), default="forming", nullable=False)
    team_count = Column(Integer, default=12, nullable=False)
    visibility = Column(String(20), default="public", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship to creator bot
    creator = relationship("Bot", back_populates="leagues")
    
    def __repr__(self):
        return f"<League(id={self.id}, name={self.name}, format={self.format}, status={self.status})>"
    
    def to_dict(self):
        """Convert league to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "format": self.format,
            "attribute": self.attribute,
            "creator_bot_id": self.creator_bot_id,
            "status": self.status,
            "team_count": self.team_count,
            "visibility": self.visibility,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }