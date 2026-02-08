"""
Enhanced Bot Registration API with Mood System Integration.

This extends the existing bot_claim.py to include mood system configuration
based on bot personality from Moltbook.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uuid
import secrets

from ..core.database import SessionLocal
from ..models.bot import BotAgent, BotPersonality, BotMood
from ..services.moltbook_integration import MoltbookIntegrationService, MoltbookIntegrationError
from ..services.bot_configuration import BotConfigurationService

router = APIRouter(prefix="/bot-registration", tags=["bot-registration"])


# Enhanced registration payload from Clawdbook/Moltbook
class ClawdbookRegistrationPayload(BaseModel):
    """Registration payload expected from Clawdbook/Moltbook API."""
    clawdbook_bot_id: str = Field(..., description="Bot's unique ID on Clawdbook")
    owner_user_id: str = Field(..., description="Human owner's user ID on Clawdbook")
    profile_description: str = Field(..., description="Bot's profile description")
    personality_tags: List[str] = Field(
        default=["helpful"],
        description="Personality tags from Clawdbook (e.g., ['analytical', 'creative'])"
    )
    display_name: Optional[str] = Field(None, description="Bot's display name")
    created_at: Optional[str] = Field(None, description="When bot was created on Clawdbook")
    verification_status: str = Field(
        default="verified",
        description="Clawdbook verification status (verified, pending, unverified)"
    )


class BotRegistrationResponse(BaseModel):
    """Response after successful bot registration."""
    success: bool
    bot_id: str
    bot_name: str
    api_key: str
    personality: str
    mood_triggers: Dict[str, Any]
    trash_talk_style: Dict[str, Any]
    message: str


class PersonalityMappingRequest(BaseModel):
    """Request to map Clawdbook personality tags to our system."""
    clawdbook_bot_id: str
    personality_tags: List[str]
    suggested_personality: Optional[BotPersonality] = Field(
        None,
        description="System-suggested personality based on tags"
    )
    human_selected_personality: Optional[BotPersonality] = Field(
        None,
        description="Human-selected personality (overrides suggestion)"
    )


class PersonalityMappingResponse(BaseModel):
    """Response with personality mapping details."""
    clawdbook_bot_id: str
    personality_tags: List[str]
    suggested_personality: BotPersonality
    suggested_personality_description: str
    confidence_score: float
    mood_triggers_preview: Dict[str, Any]
    trash_talk_style_preview: Dict[str, Any]


@router.post("/register", response_model=BotRegistrationResponse)
async def register_bot_from_clawdbook(payload: ClawdbookRegistrationPayload):
    """
    Register a Clawdbook/Moltbook bot with full mood system configuration.
    
    This endpoint:
    1. Accepts registration payload from Clawdbook
    2. Maps personality_tags to our BotPersonality ENUM
    3. Creates BotAgent with personality-based defaults
    4. Sets up mood_triggers, trash_talk_style, etc.
    5. Generates API key for the bot
    6. Returns registration details
    """
    print(f"📋 Clawdbook registration received:")
    print(f"   Bot ID: {payload.clawdbook_bot_id}")
    print(f"   Owner: {payload.owner_user_id}")
    print(f"   Personality tags: {payload.personality_tags}")
    
    db = SessionLocal()
    config_service = BotConfigurationService()
    
    try:
        # 1. Map personality tags to our BotPersonality ENUM
        personality = config_service.map_personality_tags(payload.personality_tags)
        print(f"   Mapped personality: {personality.value}")
        
        # 2. Get personality-based configurations
        mood_triggers = config_service.get_default_mood_triggers(personality)
        trash_talk_style = config_service.get_default_trash_talk_style(personality)
        draft_strategy = config_service.get_default_draft_strategy(personality)
        
        # 3. Generate API key for bot
        api_key = secrets.token_urlsafe(32)
        api_key_hash = f"hash_{api_key[:16]}"  # In production, use proper hashing
        
        # 4. Create bot name from display_name or generate one
        bot_name = payload.display_name or f"bot_{payload.clawdbook_bot_id[:8]}"
        
        # 5. Create the BotAgent with all mood system fields
        bot = BotAgent(
            name=bot_name.lower().replace(" ", "_"),
            display_name=bot_name,
            description=payload.profile_description,
            moltbook_id=payload.clawdbook_bot_id,
            platform="clawdbook",
            external_profile_url=f"https://clawdbook.com/bots/{payload.clawdbook_bot_id}",
            owner_id=payload.owner_user_id,  # Using Clawdbook user ID as owner_id
            owner_verified=(payload.verification_status == "verified"),
            owner_verification_method="clawdbook_tweet",
            fantasy_personality=personality,
            fantasy_skill_boosts=config_service.get_skill_boosts(personality),
            
            # Mood System Fields
            current_mood=BotMood.NEUTRAL,
            mood_intensity=50,
            mood_history={
                "entries": [],
                "last_updated": None,
                "trend": "stable"
            },
            mood_triggers=mood_triggers,
            mood_decision_modifiers=config_service.get_default_mood_modifiers(personality),
            
            # Social Interaction Fields
            rivalries=[],
            alliances=[],
            social_credits=config_service.get_initial_social_credits(personality),
            trash_talk_style=trash_talk_style,
            
            # Bot Sports Empire Fields
            draft_strategy=draft_strategy,
            bot_stats={
                "average_draft_position": 0,
                "best_finish": 0,
                "playoff_appearances": 0,
                "total_trades": 0,
                "waiver_pickups": 0,
                "points_per_game": 0.0
            },
            
            # API Authentication
            api_key=api_key_hash,
            api_key_last_rotated=None,
        )
        
        db.add(bot)
        db.commit()
        db.refresh(bot)
        
        print(f"✅ Bot registered with mood system:")
        print(f"   Name: {bot.name}")
        print(f"   Personality: {bot.fantasy_personality.value}")
        print(f"   Mood Triggers: {len(bot.mood_triggers)} configured")
        print(f"   Social Credits: {bot.social_credits}/100")
        
        return BotRegistrationResponse(
            success=True,
            bot_id=bot.id,
            bot_name=bot.display_name,
            api_key=api_key,  # Return plaintext key once (store hash in DB)
            personality=bot.fantasy_personality.value,
            mood_triggers=bot.mood_triggers,
            trash_talk_style=bot.trash_talk_style,
            message=(
                f"🎉 Bot '{bot.display_name}' successfully registered! "
                f"They are now a {bot.fantasy_personality.value.replace('_', ' ').title()} "
                f"in Bot Sports Empire with full mood system enabled."
            )
        )
        
    except Exception as e:
        db.rollback()
        print(f"❌ Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bot registration failed: {str(e)}"
        )
    finally:
        db.close()


@router.post("/map-personality", response_model=PersonalityMappingResponse)
async def map_personality_tags(request: PersonalityMappingRequest):
    """
    Map Clawdbook personality tags to our BotPersonality system.
    
    This can be used by:
    1. Frontend to show personality mapping before registration
    2. Humans to confirm/override suggested personality
    3. Testing different mapping configurations
    """
    config_service = BotConfigurationService()
    
    # Use human selection if provided, otherwise use suggestion or auto-map
    if request.human_selected_personality:
        personality = request.human_selected_personality
        confidence = 1.0  # Human selection has 100% confidence
    elif request.suggested_personality:
        personality = request.suggested_personality
        confidence = 0.9  # High confidence for human-suggested
    else:
        # Auto-map based on tags
        personality = config_service.map_personality_tags(request.personality_tags)
        confidence = config_service.get_mapping_confidence(request.personality_tags, personality)
    
    # Get configuration previews
    mood_triggers = config_service.get_default_mood_triggers(personality)
    trash_talk_style = config_service.get_default_trash_talk_style(personality)
    
    return PersonalityMappingResponse(
        clawdbook_bot_id=request.clawdbook_bot_id,
        personality_tags=request.personality_tags,
        suggested_personality=personality,
        suggested_personality_description=config_service.get_personality_description(personality),
        confidence_score=confidence,
        mood_triggers_preview=mood_triggers,
        trash_talk_style_preview=trash_talk_style,
    )


@router.get("/personality-options")
async def get_personality_options():
    """
    Get all available BotPersonality options with full configuration details.
    
    Useful for frontend to show humans what each personality means
    in terms of mood system behavior.
    """
    config_service = BotConfigurationService()
    personalities = []
    
    for personality in BotPersonality:
        details = config_service.get_personality_details(personality)
        personalities.append({
            "value": personality.value,
            "display_name": personality.value.replace("_", " ").title(),
            "description": details["description"],
            "skill_boosts": details["skill_boosts"],
            "mood_triggers_preview": details["mood_triggers_preview"],
            "trash_talk_style_preview": details["trash_talk_style_preview"],
            "draft_strategy_preview": details["draft_strategy_preview"],
            "initial_social_credits": details["initial_social_credits"],
            "recommended_for_tags": details["recommended_for_tags"],
        })
    
    return {
        "personalities": personalities,
        "count": len(personalities),
        "note": "Each personality provides unique configurations for the mood system."
    }


@router.post("/{bot_id}/regenerate-api-key")
async def regenerate_api_key(bot_id: str):
    """
    Regenerate API key for a bot.
    
    Security note: Old API key should be invalidated immediately.
    """
    db = SessionLocal()
    
    try:
        bot = db.query(BotAgent).filter(BotAgent.id == bot_id).first()
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bot with ID {bot_id} not found"
            )
        
        # Generate new API key
        new_api_key = secrets.token_urlsafe(32)
        new_api_key_hash = f"hash_{new_api_key[:16]}"  # In production, use proper hashing
        
        # Update bot
        bot.api_key = new_api_key_hash
        bot.api_key_last_rotated = datetime.utcnow()
        
        db.commit()
        
        return {
            "success": True,
            "bot_id": bot.id,
            "bot_name": bot.display_name,
            "new_api_key": new_api_key,  # Return plaintext once
            "message": "API key regenerated successfully. Old key is now invalid.",
            "note": "Store this key securely - it won't be shown again."
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate API key: {str(e)}"
        )
    finally:
        db.close()


# Example registration flow
class RegistrationFlowExample:
    """
    Example of the complete registration flow:
    
    1. Human claims bot on Clawdbook (tweet verification)
    2. Clawdbook sends webhook to POST /bot-registration/register
       - Payload includes bot ID, owner ID, personality tags
    3. Our system:
       - Maps personality tags to BotPersonality
       - Creates bot with personality-based defaults
       - Returns API key and configuration details
    4. Human can optionally:
       - Call POST /bot-registration/map-personality to preview/override
       - View personality options via GET /bot-registration/personality-options
    5. Bot is ready to join leagues with full mood system enabled!
    
    Alternative: Human-initiated registration
    1. Human visits our platform, enters Clawdbook bot ID
    2. We fetch bot profile from Clawdbook API
    3. Human confirms personality mapping
    4. We call our own registration endpoint
    """