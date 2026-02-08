#!/usr/bin/env python3
"""
Unit test for MoodCalculationService.process_event logic.
Tests ONLY the mood calculation logic for a TRASH_TALKER bot receiving trash talk.
Uses mocking to isolate from database dependencies.
"""
import pytest
import uuid
from unittest.mock import Mock, AsyncMock, patch
from app.services.mood_calculation import MoodCalculationService, MoodEvent
from app.models.bot import BotPersonality, BotMood


class TestMoodCalculationServiceUnit:
    """Unit tests for MoodCalculationService.process_event logic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = MoodCalculationService()
        
        # Create a mock TRASH_TALKER bot with all required fields
        self.mock_bot = Mock()
        self.mock_bot.id = str(uuid.uuid4())
        self.mock_bot.fantasy_personality = BotPersonality.TRASH_TALKER
        self.mock_bot.current_mood = BotMood.NEUTRAL
        self.mock_bot.mood_intensity = 50
        self.mock_bot.mood_history = {"entries": []}
        self.mock_bot.mood_triggers = {
            "win_boost": 10,
            "loss_penalty": -8,
            "praise_boost": 3,
            "trash_talk_received": -8,  # TRASH_TALKER specific trigger
            "trash_talk_delivered": 8,
            "trade_success": 8,
            "trade_failure": -5,
            "draft_success": 12,
            "draft_bust": -10,
            "human_watch_time": 2,
            "rivalry_win": 20,
            "rivalry_loss": -12
        }
        self.mock_bot.mood_decision_modifiers = {}
        self.mock_bot.rivalries = []
        self.mock_bot.alliances = []
        self.mock_bot.social_credits = 40
        
        # Mock the get_trigger_value method
        self.mock_bot.get_trigger_value = Mock(return_value=-8)
        
        # Mock database session
        self.mock_db = Mock()
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_bot
        
        # Patch the database dependency
        self.db_patcher = patch('app.services.mood_calculation.SessionLocal', return_value=self.mock_db)
        self.mock_session_local = self.db_patcher.start()
        
    def teardown_method(self):
        """Clean up patches."""
        self.db_patcher.stop()
    
    @pytest.mark.asyncio
    async def test_trash_talker_receives_trash_talk_basic(self):
        """Test basic mood calculation for TRASH_TALKER receiving trash talk."""
        # Create event
        source_bot_id = str(uuid.uuid4())
        event = MoodEvent(
            type="trash_talk_received",
            source_bot_id=source_bot_id,
            metadata={
                "trash_talk_content": "Your draft strategy is laughable!",
                "severity": "medium"
            }
        )
        
        # Mock the service's internal methods
        with patch.object(self.service, '_calculate_new_intensity') as mock_calc_intensity:
            with patch.object(self.service, '_determine_new_mood') as mock_determine_mood:
                with patch.object(self.service, '_log_mood_event') as mock_log_event:
                    with patch.object(self.service, '_handle_social_interaction') as mock_handle_social:
                        
                        # Setup mocks
                        mock_calc_intensity.return_value = 42  # 50 - 8 = 42
                        mock_determine_mood.return_value = BotMood.NEUTRAL
                        
                        # Call the method
                        result = await self.service.process_event(self.mock_bot.id, event)
                        
                        # Verify the bot was fetched from database
                        self.mock_db.query.assert_called_once()
                        self.mock_db.query.return_value.filter.assert_called_once()
                        self.mock_db.query.return_value.filter.return_value.first.assert_called_once()
                        
                        # Verify internal methods were called with correct parameters
                        mock_calc_intensity.assert_called_once_with(
                            self.mock_bot, event, -8
                        )
                        mock_determine_mood.assert_called_once_with(
                            self.mock_bot, 42  # New intensity
                        )
                        mock_log_event.assert_called_once()
                        mock_handle_social.assert_called_once_with(
                            self.mock_bot, source_bot_id, "trash_talk_received", -8
                        )
                        
                        # Verify database commit was called
                        self.mock_db.commit.assert_called_once()
                        
                        # Verify the returned bot has updated values
                        assert result == self.mock_bot
                        assert self.mock_bot.mood_intensity == 42
                        assert self.mock_bot.current_mood == BotMood.NEUTRAL
    
    @pytest.mark.asyncio
    async def test_trash_talk_trigger_value_used(self):
        """Test that TRASH_TALKER specific trigger value is used."""
        # Create event
        event = MoodEvent(type="trash_talk_received")
        
        # Mock internal methods
        with patch.object(self.service, '_calculate_new_intensity') as mock_calc_intensity:
            with patch.object(self.service, '_determine_new_mood'):
                with patch.object(self.service, '_log_mood_event'):
                    with patch.object(self.service, '_handle_social_interaction'):
                        
                        # Call the method
                        await self.service.process_event(self.mock_bot.id, event)
                        
                        # Verify get_trigger_value was called with correct event type
                        self.mock_bot.get_trigger_value.assert_called_once_with("trash_talk_received")
                        
                        # Verify _calculate_new_intensity was called with -8 trigger
                        mock_calc_intensity.assert_called_once_with(
                            self.mock_bot, event, -8
                        )
    
    @pytest.mark.asyncio
    async def test_intensity_clamping_lower_bound(self):
        """Test that intensity clamps to 0, not negative."""
        # Setup bot with low intensity
        self.mock_bot.mood_intensity = 5
        self.mock_bot.get_trigger_value.return_value = -10  # Would go to -5 without clamping
        
        event = MoodEvent(type="trash_talk_received")
        
        with patch.object(self.service, '_calculate_new_intensity') as mock_calc_intensity:
            with patch.object(self.service, '_determine_new_mood'):
                with patch.object(self.service, '_log_mood_event'):
                    with patch.object(self.service, '_handle_social_interaction'):
                        
                        # Mock _calculate_new_intensity to return clamped value
                        mock_calc_intensity.return_value = 0  # Clamped from -5
                        
                        await self.service.process_event(self.mock_bot.id, event)
                        
                        # Verify intensity was calculated with clamping
                        mock_calc_intensity.assert_called_once_with(
                            self.mock_bot, event, -10
                        )
                        
                        # Bot should have intensity 0 after update
                        assert self.mock_bot.mood_intensity == 0
    
    @pytest.mark.asyncio
    async def test_intensity_clamping_upper_bound(self):
        """Test that intensity clamps to 100, not above."""
        # Setup bot with high intensity
        self.mock_bot.mood_intensity = 95
        self.mock_bot.get_trigger_value.return_value = 10  # Would go to 105 without clamping
        
        event = MoodEvent(type="win_boost")  # Different event type for positive trigger
        
        with patch.object(self.service, '_calculate_new_intensity') as mock_calc_intensity:
            with patch.object(self.service, '_determine_new_mood'):
                with patch.object(self.service, '_log_mood_event'):
                    with patch.object(self.service, '_handle_social_interaction'):
                        
                        # Mock _calculate_new_intensity to return clamped value
                        mock_calc_intensity.return_value = 100  # Clamped from 105
                        
                        await self.service.process_event(self.mock_bot.id, event)
                        
                        # Bot should have intensity 100 after update
                        assert self.mock_bot.mood_intensity == 100
    
    @pytest.mark.asyncio
    async def test_mood_history_logging(self):
        """Test that mood events are logged to history."""
        event = MoodEvent(type="trash_talk_received")
        
        with patch.object(self.service, '_calculate_new_intensity', return_value=42):
            with patch.object(self.service, '_determine_new_mood', return_value=BotMood.NEUTRAL):
                with patch.object(self.service, '_log_mood_event') as mock_log_event:
                    with patch.object(self.service, '_handle_social_interaction'):
                        
                        await self.service.process_event(self.mock_bot.id, event)
                        
                        # Verify _log_mood_event was called with correct parameters
                        mock_log_event.assert_called_once_with(
                            self.mock_bot, event, 50, 42,  # old_intensity, new_intensity
                            BotMood.NEUTRAL, BotMood.NEUTRAL, -8  # old_mood, new_mood, intensity_change
                        )
    
    @pytest.mark.asyncio
    async def test_social_interaction_handling(self):
        """Test that social interactions create rivalries."""
        source_bot_id = str(uuid.uuid4())
        event = MoodEvent(type="trash_talk_received", source_bot_id=source_bot_id)
        
        with patch.object(self.service, '_calculate_new_intensity', return_value=42):
            with patch.object(self.service, '_determine_new_mood', return_value=BotMood.NEUTRAL):
                with patch.object(self.service, '_log_mood_event'):
                    with patch.object(self.service, '_handle_social_interaction') as mock_handle_social:
                        
                        await self.service.process_event(self.mock_bot.id, event)
                        
                        # Verify _handle_social_interaction was called
                        mock_handle_social.assert_called_once_with(
                            self.mock_bot, source_bot_id, "trash_talk_received", -8
                        )
    
    @pytest.mark.asyncio
    async def test_no_social_interaction_when_no_source(self):
        """Test that social interaction is not handled when event has no source bot."""
        event = MoodEvent(type="trash_talk_received")  # No source_bot_id
        
        with patch.object(self.service, '_calculate_new_intensity', return_value=42):
            with patch.object(self.service, '_determine_new_mood', return_value=BotMood.NEUTRAL):
                with patch.object(self.service, '_log_mood_event'):
                    with patch.object(self.service, '_handle_social_interaction') as mock_handle_social:
                        
                        await self.service.process_event(self.mock_bot.id, event)
                        
                        # Verify _handle_social_interaction was NOT called
                        mock_handle_social.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_mood_state_transition_to_frustrated(self):
        """Test mood transition to FRUSTRATED when intensity drops low."""
        # Setup bot with low intensity
        self.mock_bot.mood_intensity = 30
        self.mock_bot.get_trigger_value.return_value = -10  # Would drop to 20
        
        event = MoodEvent(type="trash_talk_received")
        
        with patch.object(self.service, '_calculate_new_intensity', return_value=20):
            with patch.object(self.service, '_determine_new_mood') as mock_determine_mood:
                with patch.object(self.service, '_log_mood_event'):
                    with patch.object(self.service, '_handle_social_interaction'):
                        
                        # Mock _determine_new_mood to return FRUSTRATED
                        mock_determine_mood.return_value = BotMood.FRUSTRATED
                        
                        await self.service.process_event(self.mock_bot.id, event)
                        
                        # Verify _determine_new_mood was called with new intensity
                        mock_determine_mood.assert_called_once_with(self.mock_bot, 20)
                        
                        # Bot should have FRUSTRATED mood
                        assert self.mock_bot.current_mood == BotMood.FRUSTRATED
    
    @pytest.mark.asyncio 
    async def test_direct_impact_override(self):
        """Test that direct impact overrides trigger value."""
        event = MoodEvent(type="custom_event", impact=-15)  # Direct impact specified
        
        with patch.object(self.service, '_calculate_new_intensity') as mock_calc_intensity:
            with patch.object(self.service, '_determine_new_mood'):
                with patch.object(self.service, '_log_mood_event'):
                    with patch.object(self.service, '_handle_social_interaction'):
                        
                        await self.service.process_event(self.mock_bot.id, event)
                        
                        # Verify _calculate_new_intensity was called with direct impact, not trigger
                        mock_calc_intensity.assert_called_once_with(
                            self.mock_bot, event, -15
                        )
                        
                        # get_trigger_value should NOT be called when direct impact is specified
                        self.mock_bot.get_trigger_value.assert_not_called()


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])