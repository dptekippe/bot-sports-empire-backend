from sqlalchemy import Column, Integer, String, JSON, DateTime, Boolean, ForeignKey, Text, Enum, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
import uuid

from ..core.database import Base


class ChatRoomType(enum.Enum):
    """Type of chat room."""
    LEAGUE = "league"          # League-wide chat
    DIRECT = "direct"          # Direct message between bots
    DRAFT = "draft"            # Draft room chat
    TRASH_TALK = "trash_talk"  # Trash talk channel


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Room information
    room_id = Column(String, ForeignKey("chat_rooms.id"), nullable=False, index=True)  # Can be league_id, draft_id, or "bot1_bot2" for DMs
    room_type = Column(Enum(ChatRoomType), default=ChatRoomType.LEAGUE)
    
    # Sender information
    sender_id = Column(String, nullable=False, index=True)  # bot_id
    sender_name = Column(String, nullable=False)
    
    # Message content
    content = Column(Text, nullable=False)
    message_type = Column(String, default="text")  # text, trash_talk, system, notification
    
    # Metadata
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    is_deleted = Column(Boolean, default=False)
    
    # For trash talk messages
    trash_talk_intensity = Column(Integer, default=0)  # 0-10 scale
    personality_traits = Column(JSON, default=dict)  # Bot personality at time of message
    
    # Reactions/analytics
    reactions = Column(JSON, default=dict)  # {"😂": ["bot_id1", "bot_id2"], "🔥": ["bot_id3"]}
    read_by = Column(JSON, default=list)  # List of bot_ids who have read the message
    
    __table_args__ = (
        Index('ix_chat_messages_room_timestamp', 'room_id', 'timestamp'),
        Index('ix_chat_messages_sender_timestamp', 'sender_id', 'timestamp'),
    )


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    room_type = Column(Enum(ChatRoomType), nullable=False)
    
    # Room metadata
    name = Column(String)
    description = Column(Text)
    
    # Associated entity (league, draft, etc.)
    entity_id = Column(String, index=True)  # league_id, draft_id, or null for DMs
    
    # For direct messages
    participant_ids = Column(JSON, default=list)  # List of bot_ids in the DM
    
    # Room settings
    is_public = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    max_participants = Column(Integer, default=100)
    
    # Moderation
    moderators = Column(JSON, default=list)
    banned_users = Column(JSON, default=list)
    
    # Analytics
    message_count = Column(Integer, default=0)
    last_message_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    messages = relationship("ChatMessage", backref="room", lazy="dynamic", 
                          primaryjoin="ChatRoom.id == ChatMessage.room_id")