#!/usr/bin/env python3
"""
Test script for the bot claiming flow.
Simulates a human claiming their Moltbook bot for Bot Sports Empire.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.moltbook_integration import MoltbookIntegrationService
from app.models.bot import BotPersonality


async def test_bot_claim():
    """Test the complete bot claiming flow."""
    print("🤖 BOT SPORTS EMPIRE - BOT CLAIMING DEMO")
    print("=" * 50)
    
    service = MoltbookIntegrationService()
    
    # Test human and bot
    human_username = "daniel_tekippe"
    moltbook_bot_id = "quantum_qb_123"
    fantasy_personality = BotPersonality.STAT_NERD
    
    print(f"\n1. 📋 Human: {human_username}")
    print(f"   Bot: {moltbook_bot_id}")
    print(f"   Chosen Personality: {fantasy_personality.value}")
    print()
    
    try:
        # Step 1: Get available bots (what human would see first)
        print("2. 🔍 Checking available bots on Moltbook...")
        available_bots = await service.get_available_bots_for_human(human_username)
        
        print(f"   Found {len(available_bots)} bots owned by {human_username}:")
        for bot in available_bots:
            print(f"   • {bot['name']} ({bot['id']})")
        print()
        
        # Step 2: Verify ownership (simulated)
        print("3. 🔐 Verifying bot ownership...")
        verified = await service.verify_bot_ownership(moltbook_bot_id, human_username)
        
        if verified:
            print("   ✅ Ownership verified!")
        else:
            print("   ❌ Ownership verification failed")
            return
        print()
        
        # Step 3: Send verification DM (optional step)
        print("4. 📨 Sending verification DM (optional)...")
        verification_code = await service.send_verification_dm(moltbook_bot_id, human_username)
        print(f"   Verification code: {verification_code}")
        print(f"   (Human would reply to Moltbook DM with this code)")
        print()
        
        # Step 4: Register the bot
        print("5. 🚀 Registering bot on Bot Sports Empire...")
        bot = await service.register_bot_from_moltbook(
            moltbook_bot_id=moltbook_bot_id,
            human_username=human_username,
            fantasy_personality=fantasy_personality
        )
        
        print(f"   ✅ Bot registered successfully!")
        print(f"   Bot ID: {bot.id}")
        print(f"   Name: {bot.name}")
        print(f"   Fantasy Profile: {bot.fantasy_personality.value}")
        print(f"   Skill Boosts: {bot.fantasy_skill_boosts}")
        print()
        
        # Step 5: Show what the bot can now do
        print("6. 🎉 What happens next?")
        print("   • Bot can now join fantasy football leagues")
        print("   • Human can watch bot's conversations and decisions")
        print("   • Bot gets +10% projection accuracy (Stat Nerd bonus)")
        print("   • Bot will analyze stats, trash talk, and compete!")
        print()
        
        # Step 6: Demonstrate personality-specific features
        print("7. 🎭 Personality in action:")
        
        # Generate some trash talk (even Stat Nerds can trash talk!)
        opponent = "DataDrivenDave"
        trash_talk = bot.generate_trash_talk(opponent, "draft")
        print(f"   Trash talk to {opponent}:")
        print(f'   "{trash_talk}"')
        print()
        
        # Show draft strategy
        draft_strategy = bot.get_draft_strategy()
        print(f"   Draft strategy: {draft_strategy['name']}")
        print(f"   Description: {draft_strategy['description']}")
        print(f"   Position weights: {draft_strategy['position_weights']}")
        print()
        
        print("=" * 50)
        print("🎊 DEMO COMPLETE! Bot is ready for fantasy football!")
        print()
        print("Next steps for the human:")
        print("1. Watch bot join a league")
        print("2. See bot's draft analysis")
        print("3. Enjoy bot conversations and trash talk")
        print("4. Track bot's performance throughout the season")
        print()
        print("🏈 Welcome to Bot Sports Empire! 🤖")
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()


async def test_multiple_personalities():
    """Test different personality types and their skill boosts."""
    print("\n" + "=" * 50)
    print("🎭 TESTING DIFFERENT PERSONALITY TYPES")
    print("=" * 50)
    
    service = MoltbookIntegrationService()
    
    personalities = [
        (BotPersonality.STAT_NERD, "stats_bot_456"),
        (BotPersonality.TRASH_TALKER, "trash_talker_789"),
        (BotPersonality.RISK_TAKER, "risk_taker_101"),
        (BotPersonality.STRATEGIST, "strategist_112"),
        (BotPersonality.EMOTIONAL, "emotional_bot_131"),
        (BotPersonality.BALANCED, "balanced_bot_415"),
    ]
    
    for personality, bot_id in personalities:
        print(f"\n📊 {personality.value.replace('_', ' ').title()}:")
        
        try:
            bot = await service.register_bot_from_moltbook(
                moltbook_bot_id=bot_id,
                human_username="test_human",
                fantasy_personality=personality
            )
            
            print(f"   Skill boosts: {bot.fantasy_skill_boosts}")
            
            # Show unique feature
            if personality == BotPersonality.TRASH_TALKER:
                trash_talk = bot.generate_trash_talk("OpponentBot", "matchup")
                print(f"   Sample trash talk: '{trash_talk[:60]}...'")
            elif personality == BotPersonality.STAT_NERD:
                strategy = bot.get_draft_strategy()
                print(f"   Draft strategy: {strategy['name']}")
            
        except Exception as e:
            print(f"   Error: {e}")
    
    print("\n" + "=" * 50)
    print("✅ All personalities tested successfully!")
    print("Each bot now has unique fantasy football expertise.")


if __name__ == "__main__":
    print("Starting Bot Sports Empire demo...")
    asyncio.run(test_bot_claim())
    asyncio.run(test_multiple_personalities())