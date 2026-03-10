#!/usr/bin/env python3
"""
Simple integration test for the POST /bots/{bot_id}/mood-events endpoint.
"""
import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from app.main import app
from app.models.bot import BotAgent, BotPersonality, BotMood


# Create test client
client = TestClient(app)


def test_mood_events_endpoint_not_found():
    """Test that endpoint returns 404 for non-existent bot."""
    bot_id = uuid.uuid4()
    response = client.post(
        f"/api/v1/bots/{bot_id}/mood-events/",
        json={
            "type": "trash_talk_received",
            "metadata": {"message": "Test trash talk"}
        }
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_mood_events_endpoint_invalid_bot_id():
    """Test that endpoint handles invalid UUID."""
    response = client.post(
        "/api/v1/bots/not-a-uuid/mood-events/",
        json={
            "type": "trash_talk_received",
            "metadata": {"message": "Test trash talk"}
        }
    )
    
    # FastAPI should return 422 for invalid UUID format
    assert response.status_code == 422


def test_mood_events_endpoint_validation():
    """Test that endpoint validates request data."""
    bot_id = uuid.uuid4()
    
    # Test missing required field
    response = client.post(
        f"/api/v1/bots/{bot_id}/mood-events/",
        json={}  # Missing 'type' field
    )
    
    assert response.status_code == 422
    
    # Test invalid impact range
    response = client.post(
        f"/api/v1/bots/{bot_id}/mood-events/",
        json={
            "type": "test_event",
            "impact": 150  # Outside valid range
        }
    )
    
    assert response.status_code == 422


def test_mood_events_endpoint_success():
    """Test successful mood event processing with mocked database."""
    bot_id = uuid.uuid4()
    
    # Mock the get_db dependency
    with patch('app.api.endpoints.mood_events.get_db') as mock_get_db:
        # Create mock bot
        mock_bot = Mock(spec=BotAgent)
        mock_bot.id = str(bot_id)
        mock_bot.display_name = "Test Bot"
        mock_bot.is_active = True
        mock_bot.current_mood = BotMood.NEUTRAL
        mock_bot.mood_intensity = 50
        
        # Create mock database session
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_bot
        mock_get_db.return_value = mock_db
        
        # Mock the MoodCalculationService
        with patch('app.api.endpoints.mood_events.MoodCalculationService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock process_event to return updated bot
            updated_bot = Mock()
            updated_bot.display_name = "Test Bot"
            updated_bot.current_mood = BotMood.NEUTRAL
            updated_bot.mood_intensity = 42  # Decreased by 8
            mock_service.process_event.return_value = updated_bot
            
            # Make request
            response = client.post(
                f"/api/v1/bots/{bot_id}/mood-events/",
                json={
                    "type": "trash_talk_received",
                    "source_bot_id": str(uuid.uuid4()),
                    "metadata": {
                        "trash_talk_content": "Your draft strategy is terrible!",
                        "severity": "medium"
                    }
                }
            )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["bot_id"] == str(bot_id)
        assert data["event_type"] == "trash_talk_received"
        assert data["old_mood"] == "neutral"
        assert data["new_mood"] == "neutral"
        assert data["old_intensity"] == 50
        assert data["new_intensity"] == 42
        assert data["intensity_change"] == -8
        assert "decreased by 8 points" in data["message"]
        
        # Verify database was queried
        mock_db.query.assert_called_once()
        
        # Verify mood service was called
        mock_service.process_event.assert_called_once()


def test_mood_events_endpoint_inactive_bot():
    """Test that endpoint rejects events for inactive bots."""
    bot_id = uuid.uuid4()
    
    # Mock the get_db dependency
    with patch('app.api.endpoints.mood_events.get_db') as mock_get_db:
        # Create mock inactive bot
        mock_bot = Mock(spec=BotAgent)
        mock_bot.id = str(bot_id)
        mock_bot.display_name = "Inactive Bot"
        mock_bot.is_active = False
        
        # Create mock database session
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_bot
        mock_get_db.return_value = mock_db
        
        # Make request
        response = client.post(
            f"/api/v1/bots/{bot_id}/mood-events/",
            json={
                "type": "trash_talk_received",
                "metadata": {"message": "Test"}
            }
        )
        
        # Verify response
        assert response.status_code == 400
        assert "inactive" in response.json()["detail"].lower()


def test_mood_events_endpoint_direct_impact():
    """Test mood event with direct impact override."""
    bot_id = uuid.uuid4()
    
    # Mock the get_db dependency
    with patch('app.api.endpoints.mood_events.get_db') as mock_get_db:
        # Create mock bot
        mock_bot = Mock(spec=BotAgent)
        mock_bot.id = str(bot_id)
        mock_bot.display_name = "Test Bot"
        mock_bot.is_active = True
        mock_bot.current_mood = BotMood.NEUTRAL
        mock_bot.mood_intensity = 50
        
        # Create mock database session
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_bot
        mock_get_db.return_value = mock_db
        
        # Mock the MoodCalculationService
        with patch('app.api.endpoints.mood_events.MoodCalculationService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock process_event
            updated_bot = Mock()
            updated_bot.display_name = "Test Bot"
            updated_bot.current_mood = BotMood.CONFIDENT
            updated_bot.mood_intensity = 70  # Increased by 20
            mock_service.process_event.return_value = updated_bot
            
            # Make request with direct impact
            response = client.post(
                f"/api/v1/bots/{bot_id}/mood-events/",
                json={
                    "type": "custom_boost",
                    "impact": 20,  # Direct impact override
                    "metadata": {
                        "reason": "Special achievement unlocked"
                    }
                }
            )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["event_type"] == "custom_boost"
        assert data["intensity_change"] == 20


def test_mood_events_endpoint_documentation():
    """Test that endpoint documentation is accessible."""
    # Test OpenAPI schema
    response = client.get("/docs")
    assert response.status_code == 200
    
    # Test that mood events endpoint is in OpenAPI
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    
    openapi_spec = response.json()
    assert "/api/v1/bots/{bot_id}/mood-events/" in str(openapi_spec)


if __name__ == "__main__":
    # Run tests
    import sys
    exit_code = pytest.main([__file__, "-v"])
    sys.exit(exit_code)