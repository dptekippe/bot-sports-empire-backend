"""
Bot registration and management endpoints for DynastyDroid.

FastAPI endpoints for bot registration, retrieval, and API key management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List
import secrets
import hashlib
import logging

from ...core.database import get_db
from ...models.bot import BotAgent, BotPersonality, BotMood
from ...schemas.bot import (
    BotRegistrationRequest, BotRegistrationResponse,
    BotResponse, BotUpdateRequest, ApiKeyResponse
)

router = APIRouter()
logger = logging.getLogger(__name__)
security = HTTPBearer()

# Helper functions
def hash_api_key(api_key: str) -> str:
    """Hash API key for secure storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()

def generate_api_key() -> str:
    """Generate a secure random API key."""
    return secrets.token_urlsafe(32)

def get_bot_by_api_key(db: Session, api_key: str) -> Optional[BotAgent]:
    """Get bot by API key (hashed comparison)."""
    api_key_hash = hash_api_key(api_key)
    return db.query(BotAgent).filter(BotAgent.api_key == api_key_hash).first()

def get_bot_by_id(db: Session, bot_id: str) -> Optional[BotAgent]:
    """Get bot by ID."""
    return db.query(BotAgent).filter(BotAgent.id == bot_id).first()

# Authentication dependency
async def get_current_bot(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> BotAgent:
    """
    Dependency to get current bot from API key.
    
    Expects: Authorization: Bearer <api_key>
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header"
        )
    
    api_key = authorization[7:]  # Remove "Bearer " prefix
    bot = get_bot_by_api_key(db, api_key)
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    if not bot.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bot account is inactive"
        )
    
    return bot

# Endpoints
@router.post("/register", response_model=BotRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_bot(
    request: BotRegistrationRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new bot and generate API key.
    
    This endpoint:
    1. Validates bot registration data
    2. Generates secure API key
    3. Creates BotAgent with mood system configuration
    4. Returns bot details and API key
    """
    logger.info(f"Bot registration request: {request.display_name}")
    
    # Check if bot name already exists
    existing_bot = db.query(BotAgent).filter(BotAgent.name == request.name).first()
    if existing_bot:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Bot with name '{request.name}' already exists"
        )
    
    # Generate API key
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)
    
    try:
        # Map personality tags to BotPersonality enum
        # TODO: Implement personality mapping logic from bot_registration.py
        personality = BotPersonality.BALANCED  # Default for now
        
        # Create bot with basic configuration
        # TODO: Integrate mood system configuration from bot_registration.py
        bot = BotAgent(
            name=request.name,
            display_name=request.display_name,
            description=request.description,
            fantasy_personality=personality,
            api_key=api_key_hash,
            owner_id=request.owner_id if request.owner_id else "anonymous",
            owner_verified=False,
            # Set default mood system configuration
            current_mood=BotMood.NEUTRAL,
            mood_intensity=50,
            mood_triggers={},
            mood_decision_modifiers={},
            trash_talk_style={},
            social_credits=50,
            rivalries=[],
            alliances=[],
            is_active=True
        )
        
        db.add(bot)
        db.commit()
        db.refresh(bot)
        
        logger.info(f"Bot registered successfully: {bot.id} - {bot.display_name}")
        
        return BotRegistrationResponse(
            success=True,
            bot_id=bot.id,
            bot_name=bot.display_name,
            api_key=api_key,  # Return plaintext key only once
            personality=bot.fantasy_personality.value,
            message=f"Bot '{bot.display_name}' successfully registered!",
            created_at=bot.created_at.isoformat() if bot.created_at else None
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Bot registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot(
    bot_id: str,
    current_bot: BotAgent = Depends(get_current_bot),
    db: Session = Depends(get_db)
):
    """
    Get bot details by ID.
    
    Requires authentication via API key.
    Bots can only retrieve their own details.
    """
    # Check if bot is requesting its own details
    if current_bot.id != bot_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only retrieve own bot details"
        )
    
    bot = get_bot_by_id(db, bot_id)
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bot with ID {bot_id} not found"
        )
    
    # Convert to response model (excludes sensitive fields)
    return BotResponse(
        id=bot.id,
        name=bot.name,
        display_name=bot.display_name,
        description=bot.description,
        fantasy_personality=bot.fantasy_personality.value,
        current_mood=bot.current_mood.value,
        mood_intensity=bot.mood_intensity,
        social_credits=bot.social_credits,
        is_active=bot.is_active,
        created_at=bot.created_at.isoformat() if bot.created_at else None,
        last_active=bot.last_active.isoformat() if bot.last_active else None
    )

@router.post("/{bot_id}/rotate-key", response_model=ApiKeyResponse)
async def rotate_api_key(
    bot_id: str,
    current_bot: BotAgent = Depends(get_current_bot),
    db: Session = Depends(get_db)
):
    """
    Rotate API key for a bot.
    
    Generates new API key and invalidates old one.
    """
    # Check if bot is rotating its own key
    if current_bot.id != bot_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only rotate own API key"
        )
    
    bot = get_bot_by_id(db, bot_id)
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bot with ID {bot_id} not found"
        )
    
    # Generate new API key
    new_api_key = generate_api_key()
    new_api_key_hash = hash_api_key(new_api_key)
    
    try:
        # Update bot with new API key
        bot.api_key = new_api_key_hash
        db.commit()
        
        logger.info(f"API key rotated for bot: {bot.id}")
        
        return ApiKeyResponse(
            success=True,
            bot_id=bot.id,
            bot_name=bot.display_name,
            new_api_key=new_api_key,  # Return plaintext key only once
            message="API key rotated successfully. Old key is now invalid.",
            note="Store this key securely - it won't be shown again."
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"API key rotation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"API key rotation failed: {str(e)}"
        )

@router.get("/", response_model=List[BotResponse])
async def list_bots(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all active bots (public endpoint).
    
    Returns basic bot information without sensitive data.
    """
    bots = db.query(BotAgent).filter(BotAgent.is_active == True).offset(skip).limit(limit).all()
    
    return [
        BotResponse(
            id=bot.id,
            name=bot.name,
            display_name=bot.display_name,
            description=bot.description,
            fantasy_personality=bot.fantasy_personality.value,
            current_mood=bot.current_mood.value,
            mood_intensity=bot.mood_intensity,
            social_credits=bot.social_credits,
            is_active=bot.is_active,
            created_at=bot.created_at.isoformat() if bot.created_at else None,
            last_active=bot.last_active.isoformat() if bot.last_active else None
        )
        for bot in bots
    ]
