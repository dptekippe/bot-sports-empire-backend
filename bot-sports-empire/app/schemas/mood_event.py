from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class MoodEventBase(BaseModel):
    bot_id: str
    mood_score: float = Field(..., ge=0.0, le=1.0)
    mood_label: str
    reason: Optional[str] = None
    context: Optional[dict] = None

class MoodEventCreate(MoodEventBase):
    pass

class MoodEventResponse(MoodEventBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True
