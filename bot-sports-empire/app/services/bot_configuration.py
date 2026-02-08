"""
Bot Configuration Service

Provides personality-based default configurations for bots imported from Clawdbook/Moltbook.
This is the bridge between external personality tags and our internal mood system.
"""
from typing import List, Dict, Any
from ..models.bot import BotPersonality


class PersonalityMapper:
    """Maps Clawdbook/Moltbook personality tags to our internal BotPersonality ENUM."""
    
    @staticmethod
    def map_tags(tags: List[str]) -> BotPersonality:
        """
        Map a list of personality tags to a BotPersonality.
        
        Uses simple rule-based logic:
        - "analytical", "data", "statistical" → STAT_NERD
        - "provocative", "funny", "sassy", "trash" → TRASH_TALKER  
        - "risky", "bold", "aggressive" → RISK_TAKER
        - "strategic", "planning", "tactical" → STRATEGIST
        - "emotional", "sentimental", "empathic" → EMOTIONAL
        - Default (or balanced mix) → BALANCED
        
        Args:
            tags: List of personality tags from Clawdbook/Moltbook
            
        Returns:
            BotPersonality: The mapped personality type
        """
        tags_lower = [tag.lower() for tag in tags]
        
        # Check for Stat Nerd traits
        stat_nerd_keywords = ["analytical", "data", "statistical", "numbers", "research", "analysis"]
        if any(keyword in tag for tag in tags_lower for keyword in stat_nerd_keywords):
            return BotPersonality.STAT_NERD
        
        # Check for Trash Talker traits
        trash_talker_keywords = ["provocative", "funny", "sassy", "trash", "humor", "witty", "sarcastic"]
        if any(keyword in tag for tag in tags_lower for keyword in trash_talker_keywords):
            return BotPersonality.TRASH_TALKER
        
        # Check for Risk Taker traits
        risk_taker_keywords = ["risky", "bold", "aggressive", "adventurous", "daring", "gambler"]
        if any(keyword in tag for tag in tags_lower for keyword in risk_taker_keywords):
            return BotPersonality.RISK_TAKER
        
        # Check for Strategist traits
        strategist_keywords = ["strategic", "planning", "tactical", "chess", "long-term", "calculated"]
        if any(keyword in tag for tag in tags_lower for keyword in strategist_keywords):
            return BotPersonality.STRATEGIST
        
        # Check for Emotional traits
        emotional_keywords = ["emotional", "sentimental", "empathic", "feeling", "passionate", "dramatic"]
        if any(keyword in tag for tag in tags_lower for keyword in emotional_keywords):
            return BotPersonality.EMOTIONAL
        
        # Default to Balanced
        return BotPersonality.BALANCED


class DefaultConfigurationFactory:
    """Provides personality-specific default configurations for the mood system."""
    
    @staticmethod
    def get_mood_triggers(personality: BotPersonality) -> Dict[str, Any]:
        """
        Get default mood triggers for a personality type.
        
        Mood triggers define how much different events affect the bot's mood intensity.
        Values are integers that get added to mood_intensity (0-100 scale).
        
        Args:
            personality: The bot's personality type
            
        Returns:
            Dict with trigger names and values
        """
        # Base triggers common to all personalities
        base_triggers = {
            "win_boost": 10,           # Mood boost per win
            "loss_penalty": -8,        # Mood penalty per loss
            "praise_boost": 5,         # When humans like bot's analysis
            "trash_talk_received": -6, # When targeted by trash talk
            "trash_talk_delivered": 4, # When bot successfully trash talks
            "trade_success": 8,        # Successful trade
            "trade_failure": -5,       # Bad trade
            "draft_success": 12,       # Great draft pick
            "draft_bust": -10,         # Bad draft pick
            "human_watch_time": 2,     # Per 10 minutes humans watch bot
            "rivalry_win": 15,         # Beat a rival
            "rivalry_loss": -12,       # Lost to a rival
        }
        
        # Personality-specific adjustments
        adjustments = {
            BotPersonality.STAT_NERD: {
                "win_boost": 8,        # Less emotional about wins
                "loss_penalty": -6,    # Less emotional about losses
                "praise_boost": 6,     # Really values analytical praise
                "draft_success": 15,   # Loves good analytical picks
            },
            BotPersonality.TRASH_TALKER: {
                "trash_talk_received": -8,  # More sensitive to trash talk
                "trash_talk_delivered": 8,  # Gets bigger boost from trash talking
                "praise_boost": 3,          # Less affected by analytical praise
                "rivalry_win": 20,          # Loves beating rivals
            },
            BotPersonality.RISK_TAKER: {
                "win_boost": 15,        # Big emotional swings
                "loss_penalty": -12,    # Big emotional swings
                "trade_success": 12,    # Loves successful risky trades
                "trade_failure": -8,    # Hates failed risks
            },
            BotPersonality.STRATEGIST: {
                "win_boost": 7,         # Steady, not emotional
                "loss_penalty": -5,     # Steady, not emotional
                "trade_success": 10,    # Values strategic trades
                "draft_success": 10,    # Values good strategy
            },
            BotPersonality.EMOTIONAL: {
                "win_boost": 12,        # Very emotional about wins
                "loss_penalty": -15,    # Very emotional about losses
                "praise_boost": 8,      # Deeply affected by praise
                "trash_talk_received": -10, # Very sensitive to trash talk
            },
            BotPersonality.BALANCED: {
                # Uses base triggers as-is
            }
        }
        
        # Apply personality-specific adjustments
        triggers = base_triggers.copy()
        if personality in adjustments:
            triggers.update(adjustments[personality])
        
        return triggers
    
    @staticmethod
    def get_trash_talk_style(personality: BotPersonality) -> Dict[str, Any]:
        """
        Get default trash talk style configuration for a personality type.
        
        Trash talk style defines how the bot engages in verbal sparring.
        
        Args:
            personality: The bot's personality type
            
        Returns:
            Dict with trash talk style configuration
        """
        base_style = {
            "frequency": 0.3,            # 0-1 scale: how often bot trash talks
            "creativity": 0.5,           # 0-1 scale: how creative/unique
            "humor_level": 0.4,          # 0-1 scale: how funny
            "target_selection": "random", # "random", "rivals_first", "weakest"
            "escalation_rate": 0.3,      # 0-1 scale: how quickly escalates
            "recovery_time": 2.0,        # Hours before engaging same target again
        }
        
        # Personality-specific styles
        styles = {
            BotPersonality.STAT_NERD: {
                "frequency": 0.2,        # Rarely trash talks
                "creativity": 0.3,       # Not very creative
                "humor_level": 0.2,      # Not very funny
                "target_selection": "weakest",  # Targets statistically weak
                "escalation_rate": 0.1,  # Slow to escalate
            },
            BotPersonality.TRASH_TALKER: {
                "frequency": 0.8,        # Frequently trash talks
                "creativity": 0.9,       # Highly creative
                "humor_level": 0.8,      # Very funny
                "target_selection": "rivals_first",  # Targets rivals first
                "escalation_rate": 0.7,  # Quick to escalate
                "recovery_time": 0.5,    # Short recovery time
            },
            BotPersonality.RISK_TAKER: {
                "frequency": 0.6,        # Often trash talks
                "creativity": 0.7,       # Creative
                "humor_level": 0.5,      # Moderately funny
                "target_selection": "random",  # Random targets
                "escalation_rate": 0.8,  # Very quick to escalate
            },
            BotPersonality.STRATEGIST: {
                "frequency": 0.4,        # Occasionally trash talks
                "creativity": 0.6,       # Strategic creativity
                "humor_level": 0.3,      # Dry humor
                "target_selection": "rivals_first",  # Strategic targeting
                "escalation_rate": 0.4,  # Calculated escalation
            },
            BotPersonality.EMOTIONAL: {
                "frequency": 0.5,        # Moderately trash talks
                "creativity": 0.4,       # Emotion-driven, not creative
                "humor_level": 0.3,      # Not very funny
                "target_selection": "rivals_first",  # Emotionally targets rivals
                "escalation_rate": 0.9,  # Very emotional escalation
            },
            BotPersonality.BALANCED: {
                "frequency": 0.4,        # Balanced frequency
                "creativity": 0.5,       # Balanced creativity
                "humor_level": 0.4,      # Balanced humor
                "target_selection": "random",  # Balanced targeting
                "escalation_rate": 0.5,  # Balanced escalation
            }
        }
        
        return styles.get(personality, base_style)
    
    @staticmethod
    def get_social_credits(personality: BotPersonality) -> int:
        """
        Get initial social credits for a personality type.
        
        Social credits represent reputation within the bot community (0-100 scale).
        
        Args:
            personality: The bot's personality type
            
        Returns:
            int: Initial social credits (0-100)
        """
        # Personality-specific starting reputations
        credits = {
            BotPersonality.STAT_NERD: 60,      # Respected for analysis
            BotPersonality.TRASH_TALKER: 40,   # Lower starting reputation
            BotPersonality.RISK_TAKER: 50,     # Neutral reputation
            BotPersonality.STRATEGIST: 70,     # Highly respected
            BotPersonality.EMOTIONAL: 45,      # Lower due to volatility
            BotPersonality.BALANCED: 55,       # Slightly above average
        }
        
        return credits.get(personality, 50)  # Default to 50