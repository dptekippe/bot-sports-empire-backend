#!/usr/bin/env python3
"""
Integration test for the MoodCalculationService.
Tests that mood events are processed correctly with personality-specific triggers.
"""
import pytest
import uuid
import asyncio
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models.bot import BotAgent, BotPersonality, BotMood
from app.models.human_owner import HumanOwner
from app.services.mood_calculation import MoodCalculationService, MoodEvent


@pytest.fixture(autouse=True, scope="module")
def setup_database():
    """Create all tables once for the test module."""
    Base.metadata.create_all(bind=engine)
    yield
    # Optional: Drop tables after all tests if you want a clean slate
    # Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Provide a clean database session for each test, rolled back after."""
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection)
    yield db
    transaction.rollback()
    connection.close()


@pytest.fixture
def test_human_owner(db):
    """Create a unique human owner for tests."""
    owner = HumanOwner(
        id=str(uuid.uuid4()),  # Convert UUID to string for SQLite
        username=f"test_human_{uuid.uuid4().hex[:8]}",
        display_name="Test Human",
        auth_provider="test",
        external_auth_id=f"ext_{uuid.uuid4().hex[:8]}",
    )
    db.add(owner)
    db.commit()
    db.refresh(owner)
    return owner


@pytest.fixture
def test_trash_talker_bot(db, test_human_owner):
    """Create a unique TRASH_TALKER bot with all required fields populated."""
    bot = BotAgent(
        id=str(uuid.uuid4()),  # Convert UUID to string for SQLite
        name=f"TestBot_TT_{uuid.uuid4().hex[:8]}",
        display_name="Test Trash Talker",
        description="A test bot for mood calculations.",
        moltbook_id=f"moltbook_test_{uuid.uuid4().hex[:8]}",
        platform="test",
        external_profile_url="https://example.com/test",
        fantasy_personality=BotPersonality.TRASH_TALKER,
        # --- Mood System Fields ---
        current_mood=BotMood.NEUTRAL,
        mood_intensity=50,
        mood_history={"entries": []},
        mood_triggers={
            "win_boost": 10,
            "loss_penalty": -8,
            "praise_boost": 3,
            "trash_talk_received": -8,
            "trash_talk_delivered": 8,
            "trade_success": 8,
            "trade_failure": -5,
            "draft_success": 12,
            "draft_bust": -10,
            "human_watch_time": 2,
            "rivalry_win": 20,
            "rivalry_loss": -12
        },
        mood_decision_modifiers={},
        trash_talk_style={"frequency": 0.8},
        social_credits=40,
        rivalries=[],
        alliances=[],
        # --- Ownership ---
        owner_id=test_human_owner.id,
        owner_verified=True,
        owner_verification_method="test",
        # --- Populate other NON-NULLABLE fields from your schema ---
        api_key=str(uuid.uuid4()),
        is_active=True,
        fantasy_skill_boosts={},
        behavior_settings={},
        custom_data={},
        total_leagues=0,
        championships=0,
        total_wins=0,
        total_losses=0,
        total_points=0,
        bot_stats={},
        draft_strategy={},
    )
    db.add(bot)
    db.commit()
    db.refresh(bot)
    return bot


@pytest.fixture
def test_stat_nerd_bot(db, test_human_owner):
    """Create a unique STAT_NERD bot with all required fields populated."""
    bot = BotAgent(
        id=str(uuid.uuid4()),  # Convert UUID to string for SQLite
        name=f"TestBot_SN_{uuid.uuid4().hex[:8]}",
        display_name="Test Stat Nerd",
        description="A test STAT_NERD bot for mood calculations.",
        moltbook_id=f"moltbook_test_{uuid.uuid4().hex[:8]}",
        platform="test",
        external_profile_url="https://example.com/test",
        fantasy_personality=BotPersonality.STAT_NERD,
        current_mood=BotMood.NEUTRAL,
        mood_intensity=50,
        mood_history={"entries": []},
        mood_triggers={
            "win_boost": 8,
            "loss_penalty": -6,
            "praise_boost": 2,
            "trash_talk_received": -5,
            "trash_talk_delivered": 3,
            "trade_success": 6,
            "trade_failure": -4,
            "draft_success": 15,  # STAT_NERD has higher draft success trigger
            "draft_bust": -12,
            "human_watch_time": 1,
            "rivalry_win": 15,
            "rivalry_loss": -10
        },
        mood_decision_modifiers={},
        trash_talk_style={"frequency": 0.3},
        social_credits=50,
        rivalries=[],
        alliances=[],
        owner_id=test_human_owner.id,
        owner_verified=True,
        owner_verification_method="test",
        api_key=str(uuid.uuid4()),
        is_active=True,
        fantasy_skill_boosts={},
        behavior_settings={},
        custom_data={},
        total_leagues=0,
        championships=0,
        total_wins=0,
        total_losses=0,
        total_points=0,
        bot_stats={},
        draft_strategy={},
    )
    db.add(bot)
    db.commit()
    db.refresh(bot)
    return bot


@pytest.mark.asyncio
async def test_trash_talker_receives_trash_talk(db, test_trash_talker_bot):
    """Test that a TRASH_TALKER bot's mood decreases when receiving trash talk."""
    service = MoodCalculationService()
    
    # Use the trigger defined in the bot's mood_triggers
    source_bot_id = str(uuid.uuid4())  # Convert to string for SQLite
    event = MoodEvent(
        type="trash_talk_received",
        source_bot_id=source_bot_id,
        metadata={
            "trash_talk_content": "Your draft strategy is laughable!",
            "severity": "medium"
        }
    )
    
    updated_bot = await service.process_event(test_trash_talker_bot.id, event)
    
    # Assertions
    assert updated_bot.mood_intensity == 42  # 50 (start) + (-8 trigger) = 42
    assert len(updated_bot.mood_history["entries"]) == 1
    assert updated_bot.current_mood == BotMood.NEUTRAL  # Still neutral at intensity 42
    
    # Check that history entry was created
    history_entry = updated_bot.mood_history["entries"][0]
    assert history_entry["event_type"] == "trash_talk_received"
    assert history_entry["old_intensity"] == 50
    assert history_entry["new_intensity"] == 42
    assert history_entry["intensity_change"] == -8
    
    # Check rivalry was created
    assert len(updated_bot.rivalries) == 1
    rivalry = updated_bot.rivalries[0]
    assert rivalry["bot_id"] == source_bot_id
    assert rivalry["intensity"] > 0


@pytest.mark.asyncio
async def test_stat_nerd_draft_success(db, test_stat_nerd_bot):
    """Test that a STAT_NERD bot's mood increases with draft success."""
    service = MoodCalculationService()
    
    event = MoodEvent(
        type="draft_success",
        metadata={
            "player_name": "Patrick Mahomes",
            "draft_round": 1,
            "value_score": 95
        }
    )
    
    updated_bot = await service.process_event(test_stat_nerd_bot.id, event)
    
    # Assertions - STAT_NERD has +15 for draft_success
    assert updated_bot.mood_intensity == 65  # 50 (start) + (15 trigger) = 65
    assert len(updated_bot.mood_history["entries"]) == 1
    # STAT_NERD becomes ANALYTICAL at intensity 65
    assert updated_bot.current_mood == BotMood.ANALYTICAL
    
    # Check history
    history_entry = updated_bot.mood_history["entries"][0]
    assert history_entry["event_type"] == "draft_success"
    assert history_entry["old_intensity"] == 50
    assert history_entry["new_intensity"] == 65
    assert history_entry["intensity_change"] == 15


@pytest.mark.asyncio
async def test_mood_state_transitions(db, test_trash_talker_bot):
    """Test mood state transitions with hysteresis."""
    service = MoodCalculationService()
    
    # First, make the bot CONFIDENT (intensity > 75)
    test_trash_talker_bot.mood_intensity = 80
    test_trash_talker_bot.current_mood = BotMood.CONFIDENT
    db.commit()
    db.refresh(test_trash_talker_bot)
    
    # Reduce intensity to 70 (above hysteresis threshold of 65)
    event = MoodEvent(type="test_reduction", impact=-10)
    updated_bot = await service.process_event(test_trash_talker_bot.id, event)
    
    # Should still be CONFIDENT due to hysteresis
    assert updated_bot.mood_intensity == 70
    assert updated_bot.current_mood == BotMood.CONFIDENT
    
    # Reduce further to 60 (below hysteresis threshold)
    event = MoodEvent(type="test_reduction", impact=-10)
    updated_bot = await service.process_event(updated_bot.id, event)
    
    # Should now be NEUTRAL
    assert updated_bot.mood_intensity == 60
    assert updated_bot.current_mood == BotMood.NEUTRAL
    
    # Make the bot FRUSTRATED (intensity < 25)
    # Get the bot fresh from the database
    db_bot = db.query(BotAgent).filter(BotAgent.id == updated_bot.id).first()
    db_bot.mood_intensity = 20
    db_bot.current_mood = BotMood.FRUSTRATED
    db.commit()
    db.refresh(db_bot)
    
    # Increase intensity to 28 (above 25 but below hysteresis threshold of 30)
    event = MoodEvent(type="test_increase", impact=8)
    updated_bot = await service.process_event(db_bot.id, event)
    
    # Should still be FRUSTRATED due to hysteresis
    assert updated_bot.mood_intensity == 28
    assert updated_bot.current_mood == BotMood.FRUSTRATED
    
    # Increase further to 35 (above hysteresis threshold)
    event = MoodEvent(type="test_increase", impact=7)
    updated_bot = await service.process_event(updated_bot.id, event)
    
    # Should now be NEUTRAL
    assert updated_bot.mood_intensity == 35
    assert updated_bot.current_mood == BotMood.NEUTRAL


@pytest.mark.asyncio
async def test_intensity_bounds(db, test_trash_talker_bot):
    """Test that mood intensity stays within bounds (0-100)."""
    service = MoodCalculationService()
    
    # Test lower bound: Start at 5, apply -10 trigger
    test_trash_talker_bot.mood_intensity = 5
    db.commit()
    db.refresh(test_trash_talker_bot)
    
    event = MoodEvent(type="trash_talk_received", impact=-10)
    updated_bot = await service.process_event(test_trash_talker_bot.id, event)
    
    # Should clamp to 0, not -3
    assert updated_bot.mood_intensity == 0
    # At intensity 0, mood should be DEFENSIVE
    assert updated_bot.current_mood == BotMood.DEFENSIVE
    
    # Test upper bound: Start at 95, apply +10 trigger
    # Get the bot fresh from the database
    db_bot = db.query(BotAgent).filter(BotAgent.id == updated_bot.id).first()
    db_bot.mood_intensity = 95
    db.commit()
    db.refresh(db_bot)
    
    event = MoodEvent(type="win_boost", impact=10)
    updated_bot = await service.process_event(db_bot.id, event)
    
    # Should clamp to 100, not 105
    assert updated_bot.mood_intensity == 100


if __name__ == "__main__":
    # Run tests directly when script is executed
    import sys
    exit_code = pytest.main([__file__, "-v"])
    sys.exit(exit_code)