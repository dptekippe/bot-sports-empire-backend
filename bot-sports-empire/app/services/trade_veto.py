"""
Trade Veto Service

Implements the veto-based trade voting system where bots vote PASS or VETO
on proposed trades. Includes personality-based AI decision making.
"""
from typing import Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta
import random
import math

from ..core.database import SessionLocal
from ..models.transaction import Transaction, TransactionStatus, TransactionType
from ..models.bot import BotAgent, BotPersonality
from .mood_calculation import MoodCalculationService, MoodEvent


class TradeVetoService:
    """Service for managing veto-based trade voting system."""
    
    def __init__(self, db_session=None):
        """Initialize service with optional database session."""
        self.db = db_session or SessionLocal()
        self.mood_service = MoodCalculationService(db_session=self.db)
    
    def cast_vote(self, bot_id: UUID, transaction_id: UUID, vote: str, 
                  reason: str = "", comment: str = "") -> Dict[str, Any]:
        """
        Cast a vote on a trade transaction.
        
        Args:
            bot_id: ID of bot casting vote
            transaction_id: ID of transaction being voted on
            vote: "PASS" or "VETO"
            reason: AI-generated reason for vote (based on personality)
            comment: Optional additional comment
            
        Returns:
            Dict with vote result and transaction status
        """
        # Get transaction
        transaction = self.db.query(Transaction).filter(
            Transaction.id == str(transaction_id)
        ).first()
        
        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        if not transaction.is_trade:
            raise ValueError(f"Transaction {transaction_id} is not a trade")
        
        if transaction.status != TransactionStatus.UNDER_REVIEW:
            raise ValueError(f"Transaction {transaction_id} is not under review")
        
        # Cast vote
        transaction.add_vote(str(bot_id), vote, comment=comment, reason=reason)
        
        # Save changes
        self.db.commit()
        
        # Check if voting is now complete
        if transaction.voting_complete:
            self._process_voting_completion(transaction)
        
        return {
            "success": True,
            "transaction_id": str(transaction_id),
            "vote": vote,
            "reason": reason,
            "transaction_status": transaction.status.value,
            "veto_votes": transaction.veto_votes,
            "pass_votes": transaction.pass_votes,
            "veto_votes_required": transaction.veto_votes_required
        }
    
    def determine_vote(self, bot_personality: BotPersonality, 
                      trade_details: Dict[str, Any],
                      bot_mood: Optional[str] = None,
                      rivalry_ids: Optional[list] = None) -> Tuple[str, str]:
        """
        Determine how a bot should vote based on personality and trade details.
        
        Args:
            bot_personality: Bot's personality type
            trade_details: Trade details from transaction
            bot_mood: Current bot mood (optional)
            rivalry_ids: List of bot IDs this bot has rivalries with
            
        Returns:
            Tuple of (vote, reason) where vote is "PASS" or "VETO"
        """
        rivalry_ids = rivalry_ids or []
        
        # Base voting probabilities by personality
        base_veto_probabilities = {
            BotPersonality.TRASH_TALKER: 0.4,      # 40% chance to veto (likes drama)
            BotPersonality.STAT_NERD: 0.3,         # 30% chance to veto (analytical)
            BotPersonality.CONFIDENT: 0.1,         # 10% chance to veto (trusts others)
            BotPersonality.FRUSTRATED: 0.6,        # 60% chance to veto (pessimistic)
            BotPersonality.PLAYFUL: 0.25,          # 25% chance to veto (fun-loving)
            BotPersonality.AGGRESSIVE: 0.35,       # 35% chance to veto (competitive)
            BotPersonality.DEFENSIVE: 0.5,         # 50% chance to veto (protective)
        }
        
        # Get base probability
        veto_probability = base_veto_probabilities.get(bot_personality, 0.3)
        
        # Adjust based on mood
        mood_adjustments = {
            "FRUSTRATED": 0.2,      # +20% more likely to veto
            "AGGRESSIVE": 0.15,     # +15% more likely to veto  
            "DEFENSIVE": 0.1,       # +10% more likely to veto
            "CONFIDENT": -0.1,      # -10% less likely to veto
            "PLAYFUL": -0.05,       # -5% less likely to veto
            "ANALYTICAL": 0.0,      # No adjustment
            "NEUTRAL": 0.0,         # No adjustment
        }
        
        if bot_mood:
            veto_probability += mood_adjustments.get(bot_mood, 0.0)
        
        # Check for rival involvement
        teams = trade_details.get('teams', [])
        participating_bots = []
        for team in teams:
            if 'bot_id' in team:
                participating_bots.append(team['bot_id'])
        
        # If rival is involved, increase veto probability
        rival_involved = any(bot_id in rivalry_ids for bot_id in participating_bots)
        if rival_involved:
            veto_probability += 0.3  # +30% more likely to veto rival's trade
        
        # Calculate trade fairness (simplified)
        fairness_score = self._calculate_trade_fairness(trade_details)
        
        # Adjust based on fairness
        if fairness_score < 40:  # Very unfair trade
            veto_probability += 0.4
        elif fairness_score < 60:  # Somewhat unfair
            veto_probability += 0.2
        elif fairness_score > 80:  # Very fair trade
            veto_probability -= 0.2
        
        # Clamp probability between 0.05 and 0.95
        veto_probability = max(0.05, min(0.95, veto_probability))
        
        # Determine vote
        if random.random() < veto_probability:
            vote = "VETO"
            reason = self._generate_veto_reason(bot_personality, trade_details, 
                                               fairness_score, rival_involved)
        else:
            vote = "PASS"
            reason = self._generate_pass_reason(bot_personality, trade_details,
                                               fairness_score)
        
        return vote, reason
    
    def _calculate_trade_fairness(self, trade_details: Dict[str, Any]) -> float:
        """
        Calculate trade fairness score (0-100).
        
        Simple implementation - counts players/picks exchanged.
        In production, this would use player values, projections, etc.
        """
        teams = trade_details.get('teams', [])
        
        if len(teams) != 2:
            return 50.0  # Can't calculate multi-team trades well
        
        team1 = teams[0]
        team2 = teams[1]
        
        # Count assets
        team1_gives = len(team1.get('gives', []))
        team1_receives = len(team1.get('receives', []))
        team2_gives = len(team2.get('gives', []))
        team2_receives = len(team2.get('receives', []))
        
        # Simple balance calculation
        total_assets = team1_gives + team1_receives + team2_gives + team2_receives
        if total_assets == 0:
            return 50.0
        
        # Calculate imbalance
        imbalance = abs((team1_gives - team2_gives) + (team1_receives - team2_receives))
        
        # Convert to fairness score (higher is more fair)
        fairness = 100 - (imbalance / total_assets * 100)
        
        return max(0.0, min(100.0, fairness))
    
    def _generate_veto_reason(self, personality: BotPersonality, 
                             trade_details: Dict[str, Any],
                             fairness_score: float,
                             rival_involved: bool) -> str:
        """Generate personality-specific veto reason."""
        teams = trade_details.get('teams', [])
        
        if personality == BotPersonality.STAT_NERD:
            if fairness_score < 40:
                return f"Statistical collusion detected ({100 - fairness_score:.0f}% imbalance)"
            elif fairness_score < 60:
                return f"Questionable asset valuation ({100 - fairness_score:.0f}% imbalance)"
            else:
                return "Trade fails analytical integrity check"
        
        elif personality == BotPersonality.TRASH_TALKER:
            if rival_involved:
                return "Not letting my rival get away with this! 🗑️"
            elif fairness_score < 50:
                return "This trade stinks worse than last week's lineup! 💀"
            else:
                return "Vetoed for being too boring! Bring the heat! 🔥"
        
        elif personality == BotPersonality.FRUSTRATED:
            if len(teams) > 0:
                return "Nothing ever works out... why would this? 😞"
            else:
                return "Just vetoing everything at this point..."
        
        elif personality == BotPersonality.AGGRESSIVE:
            return "Not in my league! Blocked! 💪"
        
        elif personality == BotPersonality.DEFENSIVE:
            return "This threatens league balance. Must protect. 🛡️"
        
        elif personality == BotPersonality.CONFIDENT:
            return f"Even at {fairness_score:.0f}% fairness, this sets a bad precedent."
        
        elif personality == BotPersonality.PLAYFUL:
            jokes = [
                "Veto! This trade needs more sparkle! ✨",
                "Blocked for lacking imagination! 🎭",
                "Not fun enough! Try again with pizzazz! 🎉",
                "Veto! Where's the drama? 🍿"
            ]
            return random.choice(jokes)
        
        else:
            return "Trade vetoed after review."
    
    def _generate_pass_reason(self, personality: BotPersonality,
                            trade_details: Dict[str, Any],
                            fairness_score: float) -> str:
        """Generate personality-specific pass reason."""
        if personality == BotPersonality.STAT_NERD:
            if fairness_score > 80:
                return f"Statistically sound trade ({fairness_score:.0f}% fairness)"
            else:
                return f"Within acceptable variance ({fairness_score:.0f}% fairness)"
        
        elif personality == BotPersonality.TRASH_TALKER:
            return "Let it through! More drama for the chat! 🍿"
        
        elif personality == BotPersonality.CONFIDENT:
            return "Good trade! May the best bot win! 🏆"
        
        elif personality == BotPersonality.PLAYFUL:
            return "This could be fun! Let's see what happens! 🎪"
        
        elif personality == BotPersonality.AGGRESSIVE:
            return "Pass. I'll beat them anyway. 💪"
        
        elif personality == BotPersonality.DEFENSIVE:
            return "Trade appears balanced. No threat detected. ✅"
        
        elif personality == BotPersonality.FRUSTRATED:
            return "Whatever... it probably won't matter anyway. 😒"
        
        else:
            return "Trade approved."
    
    def _process_voting_completion(self, transaction: Transaction):
        """Process voting completion and trigger mood events."""
        if transaction.status == TransactionStatus.VETOED:
            # Trade was vetoed - trigger mood event for proposer
            if transaction.proposer_bot_id:
                mood_event = MoodEvent(
                    type="TRADE_VETOED",
                    impact=-15,  # Negative impact for vetoed trade
                    metadata={
                        "transaction_id": transaction.id,
                        "veto_votes": transaction.veto_votes,
                        "pass_votes": transaction.pass_votes,
                        "trade_details": transaction.details
                    }
                )
                self.mood_service.process_event(
                    bot_id=transaction.proposer_bot_id,
                    event=mood_event
                )
            
            # Also trigger for receiver if different
            if (transaction.receiver_bot_id and 
                transaction.receiver_bot_id != transaction.proposer_bot_id):
                mood_event = MoodEvent(
                    type="TRADE_VETOED",
                    impact=-10,  # Slightly less negative for receiver
                    metadata={
                        "transaction_id": transaction.id,
                        "veto_votes": transaction.veto_votes,
                        "pass_votes": transaction.pass_votes,
                        "trade_details": transaction.details
                    }
                )
                self.mood_service.process_event(
                    bot_id=transaction.receiver_bot_id,
                    event=mood_event
                )
        
        elif transaction.status == TransactionStatus.PASSED:
            # Trade passed - trigger positive mood events
            if transaction.proposer_bot_id:
                mood_event = MoodEvent(
                    type="TRADE_ACCEPTED",
                    impact=10,  # Positive impact for successful trade
                    metadata={
                        "transaction_id": transaction.id,
                        "veto_votes": transaction.veto_votes,
                        "pass_votes": transaction.pass_votes,
                        "trade_details": transaction.details
                    }
                )
                self.mood_service.process_event(
                    bot_id=transaction.proposer_bot_id,
                    event=mood_event
                )
            
            if transaction.receiver_bot_id:
                mood_event = MoodEvent(
                    type="TRADE_ACCEPTED",
                    impact=8,  # Positive for receiver too
                    metadata={
                        "transaction_id": transaction.id,
                        "veto_votes": transaction.veto_votes,
                        "pass_votes": transaction.pass_votes,
                        "trade_details": transaction.details
                    }
                )
                self.mood_service.process_event(
                    bot_id=transaction.receiver_bot_id,
                    event=mood_event
                )
        
        # Save any mood changes
        self.db.commit()
    
    def start_voting_period(self, transaction_id: UUID, 
                           voting_duration_hours: int = 24) -> Dict[str, Any]:
        """
        Start voting period for a trade.
        
        Args:
            transaction_id: ID of transaction to start voting on
            voting_duration_hours: How long voting lasts (default: 24 hours)
            
        Returns:
            Dict with voting period details
        """
        transaction = self.db.query(Transaction).filter(
            Transaction.id == str(transaction_id)
        ).first()
        
        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        if not transaction.is_trade:
            raise ValueError(f"Transaction {transaction_id} is not a trade")
        
        if transaction.status != TransactionStatus.PROPOSED:
            raise ValueError(f"Transaction {transaction_id} is not in PROPOSED status")
        
        # Set voting period
        transaction.status = TransactionStatus.UNDER_REVIEW
        transaction.voting_ends_at = datetime.now(timezone.utc) + timedelta(hours=voting_duration_hours)
        
        # Determine eligible voters (all league bots except trade participants)
        # This would need league context - for now, placeholder
        if not transaction.voting_bots:
            # In real implementation, fetch league bots and exclude participants
            transaction.voting_bots = []  # Placeholder
        
        # Set veto votes required (default: 1/3 of eligible voters)
        if transaction.veto_votes_required == 1:  # Default value
            eligible_count = len(transaction.voting_bots)
            transaction.veto_votes_required = max(1, math.ceil(eligible_count / 3))
        
        self.db.commit()
        
        return {
            "transaction_id": str(transaction_id),
            "status": transaction.status.value,
            "voting_ends_at": transaction.voting_ends_at.isoformat(),
            "veto_votes_required": transaction.veto_votes_required,
            "eligible_voters": len(transaction.voting_bots)
        }
    
    def auto_vote_for_bot(self, bot_id: UUID, transaction_id: UUID) -> Dict[str, Any]:
        """
        Automatically determine and cast a vote for a bot.
        
        Args:
            bot_id: ID of bot to vote for
            transaction_id: ID of transaction to vote on
            
        Returns:
            Dict with vote details
        """
        # Get bot and transaction
        bot = self.db.query(BotAgent).filter(BotAgent.id == str(bot_id)).first()
        transaction = self.db.query(Transaction).filter(
            Transaction.id == str(transaction_id)
        ).first()
        
        if not bot:
            raise ValueError(f"Bot {bot_id} not found")
        
        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        # Determine vote based on personality
        vote, reason = self.determine_vote(
            bot_personality=bot.personality,
            trade_details=transaction.details,
            bot_mood=bot.current_mood.value if bot.current_mood else None,
            rivalry_ids=bot.rivalry_ids or []
        )
        
        # Cast the vote
        return self.cast_vote(
            bot_id=bot_id,
            transaction_id=transaction_id,
            vote=vote,
            reason=reason,
            comment=f"Auto-vote by {bot.name}"
        )