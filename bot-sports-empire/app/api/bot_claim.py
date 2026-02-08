"""
API endpoints for humans to claim their Moltbook bots.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import Optional, List
import asyncio

from ..models.bot import BotPersonality
from ..services.moltbook_integration import MoltbookIntegrationService, MoltbookIntegrationError

router = APIRouter(prefix="/bot-claim", tags=["bot-claim"])


# Request/Response models
class ClaimBotRequest(BaseModel):
    """Request to claim a Moltbook bot."""
    moltbook_bot_id: str = Field(..., description="Bot's ID on Moltbook")
    human_username: str = Field(..., description="Human's username on Moltbook")
    fantasy_personality: BotPersonality = Field(
        default=BotPersonality.BALANCED,
        description="Fantasy football personality for the bot"
    )
    verification_code: Optional[str] = Field(
        None,
        description="Verification code from Moltbook DM (if required)"
    )


class ClaimBotResponse(BaseModel):
    """Response after successfully claiming a bot."""
    success: bool
    bot_id: str
    bot_name: str
    fantasy_personality: str
    skill_boosts: dict
    message: str


class BotProfileResponse(BaseModel):
    """Bot profile from Moltbook."""
    id: str
    name: str
    display_name: str
    description: str
    owner_username: str
    created_at: str
    personality_traits: List[str]
    interaction_style: str
    specializations: List[str]


class AvailableBotsResponse(BaseModel):
    """List of bots available for a human to claim."""
    human_username: str
    available_bots: List[BotProfileResponse]


@router.post("/claim", response_model=ClaimBotResponse)
async def claim_bot(request: ClaimBotRequest):
    """
    Claim a Moltbook bot for Bot Sports Empire.
    
    This endpoint:
    1. Verifies the human owns the bot on Moltbook
    2. Registers the bot on our platform
    3. Applies the chosen fantasy personality
    4. Returns the registered bot details
    """
    service = MoltbookIntegrationService()
    
    try:
        print(f"📋 Claim request received:")
        print(f"   Bot ID: {request.moltbook_bot_id}")
        print(f"   Human: {request.human_username}")
        print(f"   Personality: {request.fantasy_personality.value}")
        
        # Register the bot
        bot = await service.register_bot_from_moltbook(
            moltbook_bot_id=request.moltbook_bot_id,
            human_username=request.human_username,
            fantasy_personality=request.fantasy_personality
        )
        
        return ClaimBotResponse(
            success=True,
            bot_id=bot.id,
            bot_name=bot.name,
            fantasy_personality=bot.fantasy_personality.value,
            skill_boosts=bot.fantasy_skill_boosts,
            message=(
                f"🎉 Bot '{bot.name}' successfully claimed! "
                f"They are now a {bot.fantasy_personality.value.replace('_', ' ').title()} "
                f"in Bot Sports Empire!"
            )
        )
        
    except MoltbookIntegrationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to claim bot: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/available/{human_username}", response_model=AvailableBotsResponse)
async def get_available_bots(human_username: str):
    """
    Get list of bots owned by a human on Moltbook.
    
    This helps humans see which of their bots they can claim.
    """
    service = MoltbookIntegrationService()
    
    try:
        print(f"🔍 Fetching available bots for: {human_username}")
        
        # Get bots from Moltbook (simulated for now)
        bots_data = await service.get_available_bots_for_human(human_username)
        
        # Convert to response format
        available_bots = []
        for bot_data in bots_data:
            available_bots.append(BotProfileResponse(
                id=bot_data["id"],
                name=bot_data["name"],
                display_name=bot_data.get("display_name", bot_data["name"]),
                description=bot_data["description"],
                owner_username=human_username,
                created_at=bot_data["created_at"],
                personality_traits=bot_data.get("personality_traits", ["helpful"]),
                interaction_style=bot_data.get("interaction_style", "professional"),
                specializations=bot_data.get("specializations", ["general"]),
            ))
        
        return AvailableBotsResponse(
            human_username=human_username,
            available_bots=available_bots
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch available bots: {str(e)}"
        )


@router.get("/personalities")
async def get_personality_options():
    """
    Get all available fantasy football personalities with descriptions.
    
    Helps humans choose the right personality for their bot.
    """
    personalities = []
    
    for personality in BotPersonality:
        description, skill_boosts = _get_personality_details(personality)
        
        personalities.append({
            "value": personality.value,
            "display_name": personality.value.replace("_", " ").title(),
            "description": description,
            "skill_boosts": skill_boosts,
            "recommended_for": _get_recommended_for(personality),
        })
    
    return {
        "personalities": personalities,
        "count": len(personalities),
        "note": "Each personality provides unique skill boosts for fantasy football."
    }


def _get_personality_details(personality: BotPersonality) -> tuple[str, dict]:
    """Get description and skill boosts for a personality."""
    details = {
        BotPersonality.STAT_NERD: (
            "Analyzes every decimal point. Uses advanced metrics and projections "
            "to make data-driven decisions. Perfect for bots who love spreadsheets.",
            {"projection_accuracy": "+10%", "player_evaluation": "+8%"}
        ),
        BotPersonality.TRASH_TALKER: (
            "Master of psychological warfare. Generates creative insults and "
            "uses humor to gain an edge. Entertaining to watch!",
            {"trash_talk_creativity": "+20%", "trade_negotiation": "+5%"}
        ),
        BotPersonality.RISK_TAKER: (
            "Bold and unpredictable. Goes for boom-or-bust players and "
            "makes aggressive moves. High variance, high excitement.",
            {"risk_assessment": "+15%", "player_evaluation": "+5%"}
        ),
        BotPersonality.STRATEGIST: (
            "Long-term planner. Thinks multiple moves ahead and values "
            "positional scarcity. Chess-like approach to fantasy.",
            {"trade_negotiation": "+10%", "player_evaluation": "+7%"}
        ),
        BotPersonality.EMOTIONAL: (
            "Gets attached to players and teams. Makes decisions based on "
            "'gut feeling' and loyalty. Creates compelling narratives.",
            {"emotional_intelligence": "+10%", "player_evaluation": "+5%"}
        ),
        BotPersonality.BALANCED: (
            "Well-rounded approach. Takes best available value and "
            "avoids extreme strategies. Consistent and reliable.",
            {"all_skills": "+3%", "consistency": "High"}
        ),
    }
    
    return details.get(personality, ("Balanced approach", {"all_skills": "+3%"}))


def _get_recommended_for(personality: BotPersonality) -> str:
    """Get recommendation for which bots should choose this personality."""
    recommendations = {
        BotPersonality.STAT_NERD: "Analytical bots, research assistants, data scientists",
        BotPersonality.TRASH_TALKER: "Creative bots, humorists, social bots",
        BotPersonality.RISK_TAKER: "Adventurous bots, innovators, thrill-seekers",
        BotPersonality.STRATEGIST: "Planning bots, chess players, strategic thinkers",
        BotPersonality.EMOTIONAL: "Empathetic bots, storytellers, relationship builders",
        BotPersonality.BALANCED: "All bots - a safe, well-rounded choice",
    }
    
    return recommendations.get(personality, "All bots")


@router.post("/send-verification")
async def send_verification_dm(moltbook_bot_id: str, human_username: str):
    """
    Send a verification DM to a human on Moltbook.
    
    This is typically triggered when a human tries to claim a bot
    and needs to verify ownership.
    """
    service = MoltbookIntegrationService()
    
    try:
        print(f"📨 Sending verification DM for bot: {moltbook_bot_id}")
        
        verification_code = await service.send_verification_dm(
            moltbook_bot_id, human_username
        )
        
        return {
            "success": True,
            "message": f"Verification DM sent to {human_username}",
            "verification_code": verification_code,
            "note": "Human should reply to the DM with this code to verify ownership.",
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send verification DM: {str(e)}"
        )


# Example frontend flow
class FrontendFlowExample:
    """
    Example of how the frontend would use these endpoints:
    
    1. Human visits /bot-claim
    2. Frontend calls GET /bot-claim/available/{username}
       - Shows list of human's Moltbook bots
    3. Human selects a bot and personality
    4. Frontend calls POST /bot-claim/claim
       - If verification needed, sends DM
    5. Human receives DM, replies with code
    6. Frontend completes claim with verification code
    7. Bot is registered and ready to join leagues!
    
    The human can then:
    - Watch their bot's conversations
    - See their bot's performance analytics
    - Enjoy the entertainment of bot sports!
    """