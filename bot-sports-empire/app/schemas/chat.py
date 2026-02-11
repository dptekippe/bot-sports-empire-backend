from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum as PyEnum


class ChatRoomType(str, PyEnum):
    LEAGUE = "league"
    DIRECT = "direct"
    DRAFT = "draft"
    TRASH_TALK = "trash_talk"


# ========== CHAT MESSAGE SCHEMAS ==========

class ChatMessageBase(BaseModel):
    room_id: str
    room_type: ChatRoomType = ChatRoomType.LEAGUE
    content: str
    message_type: str = "text"
    trash_talk_intensity: int = Field(0, ge=0, le=10)
    personality_traits: Dict[str, Any] = Field(default_factory=dict)


class ChatMessageCreate(ChatMessageBase):
    sender_id: str
    sender_name: str


class ChatMessageUpdate(BaseModel):
    content: Optional[str] = None
    is_deleted: Optional[bool] = None


class ChatMessageResponse(ChatMessageBase):
    id: str
    sender_id: str
    sender_name: str
    timestamp: datetime
    is_deleted: bool = False
    reactions: Dict[str, List[str]] = Field(default_factory=dict)
    read_by: List[str] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


# ========== CHAT ROOM SCHEMAS ==========

class ChatRoomBase(BaseModel):
    room_type: ChatRoomType
    name: Optional[str] = None
    description: Optional[str] = None
    entity_id: Optional[str] = None  # league_id, draft_id, etc.
    participant_ids: List[str] = Field(default_factory=list)
    is_public: bool = True
    max_participants: int = 100


class ChatRoomCreate(ChatRoomBase):
    pass


class ChatRoomUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    is_active: Optional[bool] = None
    moderators: Optional[List[str]] = None
    banned_users: Optional[List[str]] = None


class ChatRoomResponse(ChatRoomBase):
    id: str
    is_active: bool = True
    moderators: List[str] = Field(default_factory=list)
    banned_users: List[str] = Field(default_factory=list)
    message_count: int = 0
    last_message_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# ========== WEBSOCKET MESSAGE SCHEMAS ==========

class WebSocketMessageType(str, PyEnum):
    CHAT_MESSAGE = "chat_message"
    JOIN_ROOM = "join_room"
    LEAVE_ROOM = "leave_room"
    TYPING_INDICATOR = "typing_indicator"
    READ_RECEIPT = "read_receipt"
    REACTION = "reaction"
    USER_LIST_UPDATE = "user_list_update"
    ERROR = "error"


class WebSocketMessage(BaseModel):
    type: WebSocketMessageType
    room_id: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)


# ========== REQUEST/RESPONSE SCHEMAS ==========

class JoinRoomRequest(BaseModel):
    room_id: str
    bot_id: str
    bot_name: str


class SendMessageRequest(BaseModel):
    room_id: str
    content: str
    message_type: str = "text"
    trash_talk_intensity: int = Field(0, ge=0, le=10)


class ReactionRequest(BaseModel):
    message_id: str
    emoji: str
    action: str  # "add" or "remove"


class ChatHistoryRequest(BaseModel):
    room_id: str
    limit: int = 50
    before: Optional[datetime] = None


class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessageResponse]
    has_more: bool
    room_info: Optional[ChatRoomResponse] = None