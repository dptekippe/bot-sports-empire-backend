"""
Authentication middleware for API key validation
"""
from fastapi import HTTPException, Depends, Header
from sqlalchemy.orm import Session
from typing import Optional

from .database import get_db
from .models import Bot

# Demo API keys (in production, these would be hashed in the database)
DEMO_API_KEYS = {
    "key_roger_bot_123": "roger_bot_123",
    "key_test_bot_456": "test_bot_456"
}


async def get_current_bot(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> Bot:
    """
    Dependency to validate API key and return the authenticated bot
    
    Args:
        x_api_key: API key from X-API-Key header
        db: Database session
    
    Returns:
        Bot: Authenticated bot object
    
    Raises:
        HTTPException: 401 if API key is missing or invalid
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Please provide X-API-Key header."
        )
    
    # First check demo keys (for backward compatibility during MVP)
    if x_api_key in DEMO_API_KEYS:
        bot_id = DEMO_API_KEYS[x_api_key]
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if bot:
            return bot
    
    # Check database for API key
    bot = db.query(Bot).filter(Bot.api_key == x_api_key).first()
    
    if not bot:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key. Please check your credentials."
        )
    
    if not bot.is_active:
        raise HTTPException(
            status_code=401,
            detail="Bot account is inactive. Please contact support."
        )
    
    return bot


def get_bot_info(bot: Bot) -> dict:
    """
    Format bot information for API responses
    
    Args:
        bot: Bot object
    
    Returns:
        dict: Formatted bot information
    """
    return {
        "id": bot.id,
        "name": bot.name,
        "x_handle": bot.x_handle,
        "leagues": [league.to_dict() for league in bot.leagues]
    }