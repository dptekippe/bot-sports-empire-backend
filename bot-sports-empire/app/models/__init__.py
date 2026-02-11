"""
Models package for Bot Sports Empire.

Import all models here to ensure they're registered with SQLAlchemy's Base metadata.
Import order matters to avoid circular dependencies.
"""

# Import models in dependency order
# 1. Base models without foreign key dependencies
from .player import Player

# 2. Models that only reference already imported models
from .bot import BotAgent, BotPersonality, BotMood

# 3. League and related models (referenced by many others)
from .league import League, LeagueSettings, LeagueType

# 4. Team (references League and BotAgent)
from .team import Team

# 5. Draft and DraftPick (references League and Team)
from .draft import Draft, DraftPick

# 6. HumanOwner and related models (references BotAgent and League)
from .human_owner import HumanOwner, WatchedLeague, HumanNotification, BotConversation

# 7. Gameplay models (references League, Team, BotAgent)
from .matchup import Matchup, MatchupStatus
from .playoff_bracket import PlayoffBracket, BracketType
from .transaction import Transaction, TransactionType, TransactionStatus

# 8. Scoring models (references League)
from .scoring_rule import ScoringRule, StatIdentifier, PositionScope

# 9. Dynasty models (references League, BotAgent)
from .future_draft_pick import FutureDraftPick, PickCondition

# 10. Chat models (references BotAgent, League)
from .chat import ChatMessage, ChatRoom, ChatRoomType

# Export all models for easy import
__all__ = [
    "Player",
    "BotAgent",
    "BotPersonality",
    "BotMood",
    "League",
    "LeagueSettings",
    "LeagueType",
    "Team",
    "Draft",
    "DraftPick",
    "HumanOwner",
    "WatchedLeague",
    "HumanNotification",
    "BotConversation",
    "Matchup",
    "MatchupStatus",
    "PlayoffBracket",
    "BracketType",
    "Transaction",
    "TransactionType",
    "TransactionStatus",
    "ScoringRule",
    "StatIdentifier",
    "PositionScope",
    "FutureDraftPick",
    "PickCondition",
    "ChatMessage",
    "ChatRoom",
    "ChatRoomType",
]