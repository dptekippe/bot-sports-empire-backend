"""
Mood Events API Endpoint
POST /bots/{bot_id}/mood-events

Allows external systems to send mood events to bots, triggering mood calculations
and narrative responses.
"""
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.mood_calculation import MoodCalculationService, MoodEvent
from app.models.bot import BotAgent


# Pydantic models for request/response
class MoodEventRequest(BaseModel):
    """Request model for creating a mood event."""
    
    type: str = Field(
        ...,
        description="Type of mood event (e.g., 'trash_talk_received', 'draft_success', 'win_boost')",
        examples=["trash_talk_received", "draft_success", "trade_failure"]
    )
    
    source_bot_id: Optional[UUID] = Field(
        None,
        description="Optional ID of the bot that caused this event (for social interactions)",
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )
    
    impact: Optional[int] = Field(
        None,
        description="Optional direct impact value (overrides personality trigger)",
        ge=-100,
        le=100,
        examples=[-8, 15, 20]
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional metadata about the event",
        examples=[{
            "trash_talk_content": "Your draft strategy is laughable!",
            "severity": "medium"
        }]
    )
    
    class Config:
        schema_extra = {
            "example": {
                "type": "trash_talk_received",
                "source_bot_id": "123e4567-e89b-12d3-a456-426614174000",
                "metadata": {
                    "trash_talk_content": "Your team is going 0-13 this season!",
                    "severity": "high",
                    "context": "pre-draft trash talk"
                }
            }
        }


class MoodEventResponse(BaseModel):
    """Response model for mood event processing."""
    
    success: bool = Field(
        ...,
        description="Whether the mood event was processed successfully"
    )
    
    bot_id: UUID = Field(
        ...,
        description="ID of the bot that received the mood event"
    )
    
    event_type: str = Field(
        ...,
        description="Type of mood event that was processed"
    )
    
    old_mood: str = Field(
        ...,
        description="Bot's mood before the event"
    )
    
    new_mood: str = Field(
        ...,
        description="Bot's mood after the event"
    )
    
    old_intensity: int = Field(
        ...,
        description="Mood intensity (0-100) before the event",
        ge=0,
        le=100
    )
    
    new_intensity: int = Field(
        ...,
        description="Mood intensity (0-100) after the event",
        ge=0,
        le=100
    )
    
    intensity_change: int = Field(
        ...,
        description="Change in mood intensity (positive or negative)"
    )
    
    message: str = Field(
        ...,
        description="Human-readable description of the mood change"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "bot_id": "123e4567-e89b-12d3-a456-426614174000",
                "event_type": "trash_talk_received",
                "old_mood": "neutral",
                "new_mood": "neutral",
                "old_intensity": 50,
                "new_intensity": 42,
                "intensity_change": -8,
                "message": "Bot's mood intensity decreased by 8 points after receiving trash talk. Still feeling neutral."
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""
    
    detail: str = Field(
        ...,
        description="Error message"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "detail": "Bot not found"
            }
        }


# Create router
router = APIRouter(prefix="/bots/{bot_id}/mood-events", tags=["mood"])


@router.post(
    "/",
    response_model=MoodEventResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Bot not found"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Send a mood event to a bot",
    description="""
    Send a mood event to a bot to trigger mood calculations and narrative responses.
    
    The bot's mood will be updated based on:
    1. Personality-specific triggers (if no direct impact provided)
    2. Direct impact value (if provided, overrides personality trigger)
    3. Hysteresis logic for smooth mood transitions
    4. Intensity bounds (0-100)
    
    Events with source_bot_id will create/update social rivalries.
    All events are logged to the bot's mood history.
    """
)
async def create_mood_event(
    bot_id: UUID,
    mood_event: MoodEventRequest,
    db: Session = Depends(get_db)
) -> MoodEventResponse:
    """
    Process a mood event for a specific bot.
    
    Args:
        bot_id: UUID of the bot to receive the mood event
        mood_event: Mood event data
        db: Database session
    
    Returns:
        MoodEventResponse with details of the mood change
    
    Raises:
        HTTPException 404: If bot is not found
        HTTPException 400: If the event type is invalid or bot is inactive
        HTTPException 500: If mood calculation fails
    """
    try:
        # 1. Verify bot exists and is active
        bot = db.query(BotAgent).filter(BotAgent.id == str(bot_id)).first()
        
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bot with ID {bot_id} not found"
            )
        
        if not bot.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bot {bot.display_name} is inactive"
            )
        
        # 2. Convert request to MoodEvent model
        event = MoodEvent(
            type=mood_event.type,
            source_bot_id=str(mood_event.source_bot_id) if mood_event.source_bot_id else None,
            impact=mood_event.impact,
            metadata=mood_event.metadata or {}
        )
        
        # 3. Process the mood event
        mood_service = MoodCalculationService()
        
        # Store old state for response
        old_mood = bot.current_mood
        old_intensity = bot.mood_intensity
        
        # Process the event
        updated_bot = await mood_service.process_event(str(bot_id), event)
        
        # Refresh from database to get latest state
        db.refresh(updated_bot)
        
        # 4. Calculate intensity change
        intensity_change = updated_bot.mood_intensity - old_intensity
        
        # 5. Generate human-readable message
        message = _generate_mood_message(
            bot_name=updated_bot.display_name,
            event_type=mood_event.type,
            old_mood=old_mood,
            new_mood=updated_bot.current_mood,
            old_intensity=old_intensity,
            new_intensity=updated_bot.mood_intensity,
            intensity_change=intensity_change,
            source_bot_id=mood_event.source_bot_id
        )
        
        # 6. Return response
        return MoodEventResponse(
            success=True,
            bot_id=bot_id,
            event_type=mood_event.type,
            old_mood=old_mood.value,
            new_mood=updated_bot.current_mood.value,
            old_intensity=old_intensity,
            new_intensity=updated_bot.mood_intensity,
            intensity_change=intensity_change,
            message=message
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mood event: {str(e)}"
        )
        
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process mood event: {str(e)}"
        )


def _generate_mood_message(
    bot_name: str,
    event_type: str,
    old_mood: Any,
    new_mood: Any,
    old_intensity: int,
    new_intensity: int,
    intensity_change: int,
    source_bot_id: Optional[UUID] = None
) -> str:
    """
    Generate a human-readable message describing the mood change.
    
    Args:
        bot_name: Name of the bot
        event_type: Type of mood event
        old_mood: Mood before event
        new_mood: Mood after event
        old_intensity: Intensity before event
        new_intensity: Intensity after event
        intensity_change: Change in intensity
        source_bot_id: Optional source bot ID
    
    Returns:
        Human-readable message
    """
    # Base message
    if intensity_change > 0:
        change_desc = f"increased by {intensity_change} points"
    elif intensity_change < 0:
        change_desc = f"decreased by {abs(intensity_change)} points"
    else:
        change_desc = "remained unchanged"
    
    message = f"{bot_name}'s mood intensity {change_desc} after {event_type.replace('_', ' ')}."
    
    # Add mood state change if applicable
    if old_mood != new_mood:
        message += f" Mood changed from {old_mood.value} to {new_mood.value}."
    else:
        message += f" Still feeling {new_mood.value}."
    
    # Add social context if applicable
    if source_bot_id:
        message += " Social interaction logged."
    
    # Add intensity context
    if new_intensity <= 25:
        message += " Currently feeling quite low."
    elif new_intensity >= 75:
        message += " Currently riding high!"
    
    return message