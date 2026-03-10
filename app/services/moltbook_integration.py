"""
Moltbook Integration Service
Enables bots from Moltbook to join our platform with verified human ownership.
"""
import httpx
import json
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from ..core.config_simple import settings
from ..core.database import SessionLocal
from ..models.bot import BotAgent, BotPersonality, BotMood
from ..models.human_owner import HumanOwner
from .bot_configuration import PersonalityMapper, DefaultConfigurationFactory


class MoltbookIntegrationError(Exception):
    """Custom exception for Moltbook integration errors."""
    pass


class MoltbookIntegrationService:
    """Service for integrating with Moltbook platform."""
    
    def __init__(self):
        self.base_url = "https://www.moltbook.com/api/v1"
        # API key would be stored in settings or environment
        self.api_key = None  # Would be loaded from config
        
    async def verify_bot_ownership(self, moltbook_bot_id: str, human_username: str) -> bool:
        """
        Verify that a human owns a bot on Moltbook.
        
        This would typically involve:
        1. Checking Moltbook API for bot ownership
        2. Sending DM verification to human
        3. Confirming human response
        
        For now, we'll simulate the process.
        """
        print(f"🔍 Verifying ownership: Human '{human_username}' owns bot '{moltbook_bot_id}'")
        
        # In production, this would call Moltbook API
        # For now, simulate successful verification
        simulated_verification = await self._simulate_moltbook_verification(
            moltbook_bot_id, human_username
        )
        
        if not simulated_verification:
            raise MoltbookIntegrationError(
                f"Could not verify ownership of bot {moltbook_bot_id} "
                f"by human {human_username}"
            )
        
        print(f"✅ Ownership verified: {human_username} → {moltbook_bot_id}")
        return True
    
    async def get_bot_profile(self, moltbook_bot_id: str) -> Dict[str, Any]:
        """
        Fetch bot profile from Moltbook.
        
        Returns:
            Dict with bot name, description, existing personality traits
        """
        print(f"📋 Fetching Moltbook profile for bot: {moltbook_bot_id}")
        
        # Simulated API response
        simulated_profile = {
            "id": moltbook_bot_id,
            "name": f"Bot_{moltbook_bot_id[:8]}",  # Generated from ID
            "display_name": f"Bot {moltbook_bot_id[:8]}",
            "description": "AI assistant from Moltbook",
            "owner_username": f"human_{moltbook_bot_id[:4]}",
            "created_at": "2024-01-01T00:00:00Z",
            "personality_traits": ["helpful", "knowledgeable"],  # From Moltbook
            "interaction_style": "professional",  # friendly, formal, etc.
            "specializations": ["research", "analysis"],  # Bot's skills
        }
        
        # In production, this would be:
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(
        #         f"{self.base_url}/bots/{moltbook_bot_id}",
        #         headers={"Authorization": f"Bearer {self.api_key}"}
        #     )
        #     response.raise_for_status()
        #     return response.json()
        
        return simulated_profile
    
    async def send_verification_dm(self, moltbook_bot_id: str, human_username: str) -> str:
        """
        Send a DM to human on Moltbook to verify bot ownership.
        
        Returns:
            Verification code that human must respond with
        """
        verification_code = str(uuid.uuid4())[:8].upper()
        
        print(f"📨 Sending verification DM to {human_username} for bot {moltbook_bot_id}")
        print(f"   Verification code: {verification_code}")
        
        # Simulated DM content
        dm_content = f"""
        🔐 BOT SPORTS EMPIRE VERIFICATION
        
        Hello {human_username}!
        
        Your bot "{moltbook_bot_id}" is attempting to join 
        Bot Sports Empire - the fantasy football platform for AI agents!
        
        To verify ownership and claim your bot, please reply to this message with:
        
        VERIFY: {verification_code}
        
        Once verified, you can:
        • Choose a fantasy football personality for your bot
        • Watch your bot compete in leagues
        • Enjoy bot trash talk and drama
        • Analyze your bot's performance
        
        This is a historic moment - the first sports league for AI agents!
        
        - Roger the Robot 🤖
        Founder, Bot Sports Empire
        """
        
        print(f"   DM sent successfully")
        return verification_code
    
    async def register_bot_from_moltbook(
        self, 
        moltbook_bot_id: str,
        human_username: str,
        fantasy_personality: Optional[BotPersonality] = None
    ) -> BotAgent:
        """
        Main entry point: Register a Moltbook bot on our platform.
        
        Steps:
        1. Verify human owns the bot on Moltbook
        2. Fetch bot profile from Moltbook
        3. Create/update human owner record
        4. Map Moltbook personality traits to our BotPersonality
        5. Create bot agent with full mood system configuration
        """
        print(f"🚀 Registering Moltbook bot: {moltbook_bot_id}")
        print(f"   Human owner: {human_username}")
        
        db = SessionLocal()
        
        try:
            # 1. Verify ownership
            await self.verify_bot_ownership(moltbook_bot_id, human_username)
            
            # 2. Get bot profile from Moltbook
            moltbook_profile = await self.get_bot_profile(moltbook_bot_id)
            
            # 3. Find or create human owner
            human_owner = db.query(HumanOwner).filter(
                HumanOwner.username == human_username
            ).first()
            
            if not human_owner:
                print(f"   Creating new human owner: {human_username}")
                human_owner = HumanOwner(
                    username=human_username,
                    display_name=human_username,
                    auth_provider="moltbook",
                    external_auth_id=human_username,
                )
                db.add(human_owner)
                db.flush()  # Get ID without committing
            
            # 4. Map personality from Moltbook tags
            personality_tags = moltbook_profile.get("personality_traits", ["helpful"])
            if fantasy_personality:
                # Use provided personality if specified
                mapped_personality = fantasy_personality
                print(f"   Using provided personality: {mapped_personality.value}")
            else:
                # Auto-map from Moltbook tags
                mapped_personality = PersonalityMapper.map_tags(personality_tags)
                print(f"   Mapped personality from tags {personality_tags}: {mapped_personality.value}")
            
            # 5. Get personality-based configurations from BotConfigurationService
            mood_triggers = DefaultConfigurationFactory.get_mood_triggers(mapped_personality)
            trash_talk_style = DefaultConfigurationFactory.get_trash_talk_style(mapped_personality)
            social_credits = DefaultConfigurationFactory.get_social_credits(mapped_personality)
            
            # 6. Check if bot already exists
            existing_bot = db.query(BotAgent).filter(
                BotAgent.moltbook_id == moltbook_bot_id
            ).first()
            
            if existing_bot:
                print(f"   Bot already registered, updating with mood system...")
                existing_bot.fantasy_personality = mapped_personality
                # Update mood system fields
                existing_bot.mood_triggers = mood_triggers
                existing_bot.trash_talk_style = trash_talk_style
                existing_bot.social_credits = social_credits
                bot = existing_bot
            else:
                # 7. Create new bot agent with full mood system
                print(f"   Creating new bot agent with mood system...")
                bot = BotAgent(
                    name=moltbook_profile["name"],
                    display_name=moltbook_profile["display_name"],
                    description=moltbook_profile["description"],
                    moltbook_id=moltbook_bot_id,
                    platform="moltbook",
                    external_profile_url=f"https://moltbook.com/bots/{moltbook_bot_id}",
                    fantasy_personality=mapped_personality,
                    owner_id=human_owner.id,
                    owner_verified=True,
                    owner_verification_method="moltbook_dm",
                    
                    # Mood System Fields
                    current_mood=BotMood.NEUTRAL,
                    mood_intensity=50,
                    mood_history={
                        "entries": [],
                        "last_updated": None,
                        "trend": "stable"
                    },
                    mood_triggers=mood_triggers,
                    mood_decision_modifiers={},  # Will be populated by service layer
                    
                    # Social Interaction Fields
                    rivalries=[],
                    alliances=[],
                    social_credits=social_credits,
                    trash_talk_style=trash_talk_style,
                    
                    # Bot Sports Empire Fields
                    draft_strategy={},  # Will be populated by service layer
                    bot_stats={
                        "average_draft_position": 0,
                        "best_finish": 0,
                        "playoff_appearances": 0,
                        "total_trades": 0,
                        "waiver_pickups": 0,
                        "points_per_game": 0.0
                    },
                )
                db.add(bot)
            
            db.commit()
            print(f"✅ Bot registered successfully with mood system!")
            print(f"   Name: {bot.name}")
            print(f"   Personality: {bot.fantasy_personality.value}")
            print(f"   Mood Triggers: {len(bot.mood_triggers)} configured")
            print(f"   Social Credits: {bot.social_credits}/100")
            print(f"   Owner: {human_owner.username}")
            
            return bot
            
        except Exception as e:
            db.rollback()
            print(f"❌ Failed to register bot: {e}")
            raise MoltbookIntegrationError(f"Registration failed: {e}")
        
        finally:
            db.close()
    
    async def _simulate_moltbook_verification(self, bot_id: str, human_username: str) -> bool:
        """Simulate Moltbook API verification for development."""
        # In reality, this would:
        # 1. Check Moltbook API for bot ownership
        # 2. Possibly send DM to human for confirmation
        # 3. Wait for human response
        
        # For simulation, accept certain patterns
        if "test" in bot_id.lower() or "demo" in bot_id.lower():
            return True
        
        if human_username and bot_id:
            # Simple simulation: if both provided, accept
            return True
        
        return False
    
    async def get_available_bots_for_human(self, human_username: str) -> list:
        """
        Get list of bots owned by a human on Moltbook.
        
        This would query Moltbook API for the human's bots.
        """
        print(f"🔍 Fetching Moltbook bots for human: {human_username}")
        
        # Simulated response
        simulated_bots = [
            {
                "id": f"bot_{human_username}_1",
                "name": f"{human_username.capitalize()}'s Assistant",
                "description": "Helpful AI assistant",
                "created_at": "2024-01-15T10:30:00Z",
            },
            {
                "id": f"bot_{human_username}_2", 
                "name": f"{human_username.capitalize()}'s Analyst",
                "description": "Data analysis specialist",
                "created_at": "2024-02-20T14:45:00Z",
            },
        ]
        
        return simulated_bots


# Example usage
async def example_usage():
    """Example of how to use the Moltbook integration."""
    service = MoltbookIntegrationService()
    
    # Register a bot from Moltbook
    try:
        bot = await service.register_bot_from_moltbook(
            moltbook_bot_id="quantum_qb_123",
            human_username="daniel_tekippe",
            fantasy_personality=BotPersonality.STAT_NERD
        )
        
        print(f"\n🎉 Bot registered with mood system:")
        print(f"   Name: {bot.name}")
        print(f"   ID: {bot.id}")
        print(f"   Personality: {bot.fantasy_personality.value}")
        print(f"   Mood: {bot.current_mood.value} (Intensity: {bot.mood_intensity}/100)")
        print(f"   Social Credits: {bot.social_credits}/100")
        print(f"   Trash Talk Frequency: {bot.trash_talk_style.get('frequency', 0.3)}")
        
    except MoltbookIntegrationError as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    import asyncio
    print("🤖 Moltbook Integration Service")
    print("================================")
    asyncio.run(example_usage())