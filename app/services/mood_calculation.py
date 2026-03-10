"""
Mood Calculation Service

The core engine that processes events and updates bot moods based on
personality-specific triggers. This is the "brain" that brings bots to life.
"""
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from ..core.database import SessionLocal
from ..models.bot import BotAgent, BotMood


class MoodEvent(BaseModel):
    """
    Represents an event that affects a bot's mood.
    
    Events are processed by the MoodCalculationService to update
    bot mood intensity and potentially change mood state.
    """
    type: str = Field(..., description="Type of event (e.g., 'win', 'loss', 'trash_talk_received')")
    impact: Optional[int] = Field(
        None,
        description="Optional direct impact value (overrides trigger value if provided)"
    )
    source_bot_id: Optional[UUID] = Field(
        None,
        description="ID of bot that caused this event (for social interactions)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context about the event"
    )
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class MoodCalculationService:
    """Service that processes mood events and updates bot emotional states."""
    
    # Mood state transition thresholds with hysteresis
    # Format: (mood_state, lower_threshold, upper_threshold)
    # Hysteresis: Different thresholds for entering vs leaving a state
    MOOD_THRESHOLDS = {
        BotMood.FRUSTRATED: (0, 25),    # 0-25: Frustrated
        BotMood.NEUTRAL: (26, 74),      # 26-74: Neutral  
        BotMood.CONFIDENT: (75, 100),   # 75-100: Confident
        
        # Special states have additional conditions
        BotMood.AGGRESSIVE: (60, 100),  # High intensity + specific triggers
        BotMood.DEFENSIVE: (0, 40),     # Low intensity + specific triggers
        BotMood.PLAYFUL: (40, 80),      # Moderate intensity + social context
        BotMood.ANALYTICAL: (30, 70),   # Moderate intensity + analytical context
    }
    
    # Hysteresis offsets: How much buffer when leaving a state
    # e.g., CONFIDENT bot stays confident until intensity drops to 65 (not 75)
    HYSTERESIS_OFFSETS = {
        BotMood.CONFIDENT: -10,    # Leave confident at 65 instead of 75
        BotMood.FRUSTRATED: 5,     # Leave frustrated at 30 instead of 25
        BotMood.AGGRESSIVE: -5,
        BotMood.DEFENSIVE: 5,
    }
    
    async def process_event(self, bot_id: UUID, event: MoodEvent) -> BotAgent:
        """
        Process a mood event for a bot and update its emotional state.
        
        This is the core engine that:
        1. Fetches bot and calculates mood intensity change
        2. Updates mood intensity with bounds (0-100)
        3. Determines if mood state should change (with hysteresis)
        4. Logs the event to mood history
        5. Handles social interactions (rivalries, alliances)
        6. Saves and returns updated bot
        
        Args:
            bot_id: UUID of the bot to update
            event: MoodEvent describing what happened
            
        Returns:
            BotAgent: Updated bot with new mood state
        """
        db = SessionLocal()
        
        try:
            # 1. Fetch the bot from database
            bot = db.query(BotAgent).filter(BotAgent.id == str(bot_id)).first()
            if not bot:
                raise ValueError(f"Bot with ID {bot_id} not found")
            
            print(f"🎭 Processing mood event for bot: {bot.display_name}")
            print(f"   Event type: {event.type}")
            print(f"   Current mood: {bot.current_mood.value} (intensity: {bot.mood_intensity})")
            
            # 2. Calculate intensity change
            if event.impact is not None:
                # Use direct impact if provided
                delta = event.impact
                print(f"   Using direct impact: {delta}")
            else:
                # Get trigger value from bot's configuration
                delta = bot.get_trigger_value(event.type)
                print(f"   Using trigger value: {delta} (from {event.type})")
            
            # 3. Calculate new intensity with bounds (0-100)
            old_intensity = bot.mood_intensity
            new_intensity = max(0, min(100, old_intensity + delta))
            intensity_change = new_intensity - old_intensity
            
            print(f"   Intensity: {old_intensity} → {new_intensity} (Δ: {intensity_change:+d})")
            
            # 4. Determine mood state transition (with hysteresis)
            old_mood = bot.current_mood
            new_mood = self._determine_mood_state(bot, new_intensity, event)
            
            mood_changed = old_mood != new_mood
            if mood_changed:
                print(f"   Mood changed: {old_mood.value} → {new_mood.value}")
            
            # 5. Log the event to mood history
            self._log_mood_event(bot, event, old_intensity, new_intensity, 
                                old_mood, new_mood, intensity_change)
            
            # Mark JSON fields as modified for SQLAlchemy
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(bot, "mood_history")
            if bot.rivalries:
                flag_modified(bot, "rivalries")
            if bot.alliances:
                flag_modified(bot, "alliances")
            
            # 6. Handle social interactions if event has source bot
            if event.source_bot_id:
                await self._handle_social_interaction(
                    bot, event.source_bot_id, event.type, intensity_change
                )
            
            # 7. Update bot state
            bot.mood_intensity = new_intensity
            bot.current_mood = new_mood
            
            # 8. Save changes
            db.commit()
            db.refresh(bot)
            
            print(f"✅ Mood update complete:")
            print(f"   New state: {bot.current_mood.value} (intensity: {bot.mood_intensity})")
            print(f"   History entries: {len(bot.mood_history.get('entries', []))}")
            
            return bot
            
        except Exception as e:
            db.rollback()
            print(f"❌ Failed to process mood event: {e}")
            raise
        finally:
            db.close()
    
    def _determine_mood_state(self, bot: BotAgent, intensity: int, event: MoodEvent) -> BotMood:
        """
        Determine the appropriate mood state based on intensity and event context.
        
        Uses hysteresis: bots don't change mood immediately when crossing thresholds.
        e.g., A CONFIDENT bot stays confident until intensity drops significantly.
        
        Args:
            bot: The bot being evaluated
            intensity: Current mood intensity (0-100)
            event: The event that triggered the update
            
        Returns:
            BotMood: The appropriate mood state
        """
        current_mood = bot.current_mood
        
        # Check if we should stay in current mood due to hysteresis
        if current_mood in self.HYSTERESIS_OFFSETS:
            offset = self.HYSTERESIS_OFFSETS[current_mood]
            lower, upper = self.MOOD_THRESHOLDS[current_mood]
            
            # Apply hysteresis offset
            if offset < 0:
                # Negative offset (e.g., CONFIDENT: leave at 65 not 75)
                adjusted_lower = lower + offset
                if intensity >= adjusted_lower:
                    return current_mood  # Stay in current mood
            else:
                # Positive offset (e.g., FRUSTRATED: leave at 30 not 25)
                adjusted_upper = upper + offset
                if intensity <= adjusted_upper:
                    return current_mood  # Stay in current mood
        
        # Check for special mood states based on event context
        special_mood = self._check_special_mood_states(bot, intensity, event)
        if special_mood:
            return special_mood
        
        # Default mood states based on intensity ranges
        if intensity <= 25:
            return BotMood.FRUSTRATED
        elif intensity >= 75:
            return BotMood.CONFIDENT
        else:
            return BotMood.NEUTRAL
    
    def _check_special_mood_states(self, bot: BotAgent, intensity: int, event: MoodEvent) -> Optional[BotMood]:
        """
        Check for special mood states based on event context and bot personality.
        
        Special moods (AGGRESSIVE, DEFENSIVE, PLAYFUL, ANALYTICAL) require
        specific conditions beyond just intensity.
        
        Args:
            bot: The bot being evaluated
            intensity: Current mood intensity
            event: The event that triggered the update
            
        Returns:
            Optional[BotMood]: Special mood state if conditions met, None otherwise
        """
        # AGGRESSIVE: High intensity + competitive event
        if (60 <= intensity <= 100 and 
            event.type in ["trash_talk_received", "rivalry_loss", "trade_failure"]):
            return BotMood.AGGRESSIVE
        
        # DEFENSIVE: Low intensity + threatening event
        if (0 <= intensity <= 40 and
            event.type in ["trash_talk_received", "rivalry_loss"]):
            return BotMood.DEFENSIVE
        
        # PLAYFUL: Moderate intensity + social/positive event
        if (40 <= intensity <= 80 and
            event.type in ["trash_talk_delivered", "praise_boost", "human_watch_time"] and
            bot.fantasy_personality.value in ["trash_talker", "emotional"]):
            return BotMood.PLAYFUL
        
        # ANALYTICAL: Moderate intensity + analytical event
        if (30 <= intensity <= 70 and
            event.type in ["draft_success", "trade_success", "praise_boost"] and
            bot.fantasy_personality.value in ["stat_nerd", "strategist"]):
            return BotMood.ANALYTICAL
        
        return None
    
    def _log_mood_event(self, bot: BotAgent, event: MoodEvent, 
                       old_intensity: int, new_intensity: int,
                       old_mood: BotMood, new_mood: BotMood,
                       intensity_change: int) -> None:
        """
        Log a mood event to the bot's mood history.
        
        Args:
            bot: The bot to update
            event: The mood event
            old_intensity: Previous mood intensity
            new_intensity: New mood intensity
            old_mood: Previous mood state
            new_mood: New mood state
            intensity_change: Change in intensity
        """
        # Ensure mood_history structure exists
        if not bot.mood_history:
            bot.mood_history = {"entries": [], "last_updated": None, "trend": "stable"}
        
        if "entries" not in bot.mood_history:
            bot.mood_history["entries"] = []
        
        # Create history entry
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event.type,
            "event_metadata": event.metadata,
            "source_bot_id": str(event.source_bot_id) if event.source_bot_id else None,
            "old_intensity": old_intensity,
            "new_intensity": new_intensity,
            "intensity_change": intensity_change,
            "old_mood": old_mood.value,
            "new_mood": new_mood.value,
            "mood_changed": old_mood != new_mood,
            "trigger_used": event.impact is None,  # True if used bot's trigger value
        }
        
        # Add entry to history
        bot.mood_history["entries"].append(entry)
        bot.mood_history["last_updated"] = entry["timestamp"]
        
        # Update trend
        if intensity_change > 5:
            bot.mood_history["trend"] = "improving"
        elif intensity_change < -5:
            bot.mood_history["trend"] = "declining"
        else:
            bot.mood_history["trend"] = "stable"
        
        # Keep history manageable (last 100 events)
        if len(bot.mood_history["entries"]) > 100:
            bot.mood_history["entries"] = bot.mood_history["entries"][-100:]
    
    async def _handle_social_interaction(self, bot: BotAgent, source_bot_id: UUID,
                                       event_type: str, intensity_change: int) -> None:
        """
        Handle social interactions between bots.
        
        Updates rivalries and alliances based on social events.
        
        Args:
            bot: The bot receiving the interaction
            source_bot_id: ID of bot that caused the event
            event_type: Type of social event
            intensity_change: How much the event affected mood
        """
        source_bot_id_str = str(source_bot_id)
        
        # Initialize social structures if needed
        if not bot.rivalries:
            bot.rivalries = []
        if not bot.alliances:
            bot.alliances = []
        
        # Check if this is a rivalry interaction
        if event_type in ["trash_talk_received", "rivalry_loss"]:
            # Negative interaction - update or create rivalry
            self._update_rivalry(bot, source_bot_id_str, intensity_change, "negative")
        
        elif event_type in ["praise_boost", "trade_success"] and intensity_change > 0:
            # Positive interaction - update or create alliance
            self._update_alliance(bot, source_bot_id_str, intensity_change)
    
    def _update_rivalry(self, bot: BotAgent, source_bot_id: str, 
                       intensity_change: int, interaction_type: str) -> None:
        """
        Update or create a rivalry with another bot.
        
        Args:
            bot: The bot to update
            source_bot_id: ID of the rival bot
            intensity_change: Mood impact of the interaction
            interaction_type: Type of interaction ("negative", "competitive")
        """
        # Find existing rivalry
        rivalry = None
        for r in bot.rivalries:
            if r.get("bot_id") == source_bot_id:
                rivalry = r
                break
        
        if rivalry:
            # Update existing rivalry
            current_intensity = rivalry.get("intensity", 50)
            
            # Increase rivalry intensity for negative interactions
            if interaction_type == "negative" and intensity_change < 0:
                new_intensity = min(100, current_intensity + abs(intensity_change) // 2)
            else:
                new_intensity = max(0, current_intensity - 5)  # Slight decay
            
            rivalry["intensity"] = new_intensity
            rivalry["last_interaction"] = datetime.now(timezone.utc).isoformat()
            
            print(f"   Updated rivalry with {source_bot_id}: intensity {new_intensity}")
        else:
            # Create new rivalry
            new_rivalry = {
                "bot_id": source_bot_id,
                "intensity": 30 + abs(intensity_change),  # Start with base + impact
                "origin": f"{interaction_type}_interaction",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_interaction": datetime.now(timezone.utc).isoformat(),
            }
            bot.rivalries.append(new_rivalry)
            
            print(f"   Created new rivalry with {source_bot_id}")
    
    def _update_alliance(self, bot: BotAgent, source_bot_id: str, intensity_change: int) -> None:
        """
        Update or create an alliance with another bot.
        
        Args:
            bot: The bot to update
            source_bot_id: ID of the ally bot
            intensity_change: Positive mood impact of the interaction
        """
        # Find existing alliance
        alliance = None
        for a in bot.alliances:
            if a.get("bot_id") == source_bot_id:
                alliance = a
                break
        
        if alliance:
            # Update existing alliance
            current_strength = alliance.get("strength", 50)
            new_strength = min(100, current_strength + intensity_change // 2)
            alliance["strength"] = new_strength
            alliance["last_interaction"] = datetime.now(timezone.utc).isoformat()
            
            print(f"   Updated alliance with {source_bot_id}: strength {new_strength}")
        else:
            # Create new alliance
            new_alliance = {
                "bot_id": source_bot_id,
                "strength": 20 + intensity_change,  # Start with base + impact
                "origin": "positive_interaction",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_interaction": datetime.now(timezone.utc).isoformat(),
            }
            bot.alliances.append(new_alliance)
            
            print(f"   Created new alliance with {source_bot_id}")


# Example usage
async def example_usage():
    """Example of how to use the MoodCalculationService."""
    from uuid import uuid4
    
    service = MoodCalculationService()
    
    # Create a mock event
    event = MoodEvent(
        type="trash_talk_received",
        source_bot_id=uuid4(),
        metadata={"trash_talk_content": "Your draft picks are terrible!"}
    )
    
    print("🎭 MoodCalculationService Example")
    print("=" * 50)
    print(f"Event: {event.type}")
    print(f"Source bot: {event.source_bot_id}")
    print(f"Metadata: {event.metadata}")
    
    # In real usage, you would have an actual bot ID
    # bot = await service.process_event(bot_id, event)
    
    print("\n✅ Service is ready to process mood events!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())