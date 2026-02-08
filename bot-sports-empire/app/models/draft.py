from sqlalchemy import Column, Integer, String, JSON, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from ..core.database import Base
import uuid


class DraftStatus(enum.Enum):
    """Draft lifecycle status."""
    SCHEDULED = "scheduled"    # Draft scheduled but not started
    IN_PROGRESS = "in_progress" # Draft currently happening
    PAUSED = "paused"          # Draft paused
    COMPLETED = "completed"    # Draft finished
    CANCELLED = "cancelled"    # Draft cancelled
    
    @classmethod
    def _missing_(cls, value):
        """Handle case-insensitive lookup for database values"""
        if isinstance(value, str):
            # Database stores lowercase "scheduled" - find matching enum
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
        # Fall back to default behavior
        return super()._missing_(value)


class DraftType(enum.Enum):
    """Type of draft."""
    SNAKE = "snake"            # Snake/reversal draft (most common)
    LINEAR = "linear"          # Fixed order each round
    AUCTION = "auction"        # Auction draft
    BEST_BALL = "best_ball"    # Best ball (no lineup management)
    
    @classmethod
    def _missing_(cls, value):
        """Handle case-insensitive lookup for database values"""
        if isinstance(value, str):
            # Database stores lowercase "snake" - find matching enum
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
        # Fall back to default behavior
        return super()._missing_(value)


class DraftPick(Base):
    __tablename__ = "draft_picks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    draft_id = Column(String, ForeignKey("drafts.id"), nullable=False, index=True)
    
    # Pick details
    round = Column(Integer, nullable=False)
    pick_number = Column(Integer, nullable=False)  # Overall pick number
    team_id = Column(String, ForeignKey("teams.id"), nullable=False, index=True)
    
    # Player selected
    player_id = Column(String, nullable=True)  # Null if not picked yet
    position = Column(String)  # Player's position
    
    # Timing and metadata
    pick_start_time = Column(DateTime(timezone=True))
    pick_end_time = Column(DateTime(timezone=True))
    pick_duration_seconds = Column(Integer)  # How long it took to pick
    
    # If pick was auto-picked or made by bot
    was_auto_pick = Column(Boolean, default=False)
    bot_thinking_time = Column(Integer)  # How long bot "thought" before picking
    
    # Additional data
    pick_metadata = Column("metadata", JSON, default={
        "projected_value": None,
        "actual_value": None,
        "reach_factor": None,  # How much of a reach this pick was
    })
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    draft = relationship("Draft", back_populates="picks")
    team = relationship("Team")
    
    def __repr__(self):
        player_info = f" - {self.player_id}" if self.player_id else " (pending)"
        return f"<DraftPick Round {self.round}.{self.pick_number}{player_info}>"
    
    @property
    def is_completed(self):
        return self.player_id is not None
    
    @property
    def pick_time(self):
        """Calculate how long the pick took."""
        if self.pick_start_time and self.pick_end_time:
            return (self.pick_end_time - self.pick_start_time).total_seconds()
        return None


class Draft(Base):
    __tablename__ = "drafts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    league_id = Column(String, ForeignKey("leagues.id"), nullable=True, index=True)
    
    # Draft configuration
    name = Column(String(255), nullable=False, default="Untitled Draft")
    draft_type = Column(Enum(DraftType), nullable=False, default=DraftType.SNAKE)
    status = Column(Enum(DraftStatus), nullable=False, default=DraftStatus.SCHEDULED)
    
    # Timing
    scheduled_start = Column(DateTime(timezone=True))
    actual_start = Column(DateTime(timezone=True))
    actual_end = Column(DateTime(timezone=True))
    
    # Draft settings
    seconds_per_pick = Column(Integer, default=90)  # Default 90 seconds
    rounds = Column(Integer, default=15)  # Standard fantasy draft rounds
    team_count = Column(Integer, nullable=False)  # Number of teams in draft
    
    # Draft order (list of team IDs in draft order)
    draft_order = Column(JSON, nullable=False)
    current_pick = Column(Integer, default=1)  # Current overall pick number
    current_round = Column(Integer, default=1)
    
    # Timer management
    timer_started_at = Column(DateTime(timezone=True))
    timer_paused_at = Column(DateTime(timezone=True))
    time_remaining_seconds = Column(Integer)
    
    # Draft results
    completed_picks = Column(JSON, default=[])  # List of completed pick IDs
    team_rosters_post_draft = Column(JSON, default={})  # Team ID -> roster
    
    # Bot behavior settings
    auto_pick_enabled = Column(Boolean, default=True)
    auto_pick_strategy = Column(String, default="best_available")  # best_available, by_position, etc.
    
    # Statistics
    total_picks = Column(Integer, default=0)
    average_pick_time = Column(Integer)  # Average seconds per pick
    fastest_pick = Column(Integer)       # Fastest pick in seconds
    slowest_pick = Column(Integer)       # Slowest pick in seconds
    
    # Metadata
    draft_metadata = Column("metadata", JSON, default={
        "draft_board": [],  # Visual representation of draft
        "chat_log": [],     # Draft chat messages
        "bot_comments": [], # Bot trash talk during draft
    })
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    league = relationship("League", back_populates="drafts")
    picks = relationship("DraftPick", back_populates="draft", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Draft for League {self.league_id} ({self.status.value})>"
    
    @property
    def is_active(self):
        return self.status == DraftStatus.IN_PROGRESS
    
    @property
    def is_complete(self):
        return self.status == DraftStatus.COMPLETED
    
    @property
    def picks_made(self):
        return len(self.completed_picks)
    
    @property
    def picks_remaining(self):
        total_picks = self.rounds * self.team_count
        return total_picks - self.picks_made
    
    @property
    def completion_percentage(self):
        total_picks = self.rounds * self.team_count
        if total_picks == 0:
            return 0.0
        return (self.picks_made / total_picks) * 100
    
    @property
    def current_team_turn(self):
        """Get the team ID whose turn it is to pick."""
        if self.is_complete:
            return None
        
        # For snake draft, reverse order on even rounds
        if self.draft_type == DraftType.SNAKE:
            if self.current_round % 2 == 1:  # Odd round, normal order
                pick_index = (self.current_pick - 1) % self.team_count
            else:  # Even round, reversed order
                pick_index = self.team_count - 1 - ((self.current_pick - 1) % self.team_count)
        else:  # Linear draft
            pick_index = (self.current_pick - 1) % self.team_count
        
        return self.draft_order[pick_index]
    
    def generate_draft_order(self, method="random"):
        """Generate draft order for the league."""
        import random
        
        if method == "random":
            order = self.draft_order.copy()
            random.shuffle(order)
            self.draft_order = order
        elif method == "reverse_standings":
            # Would need previous season standings
            pass
        elif method == "manual":
            # Order already set
            pass
        
        return self.draft_order
    
    def start_draft(self):
        """Start the draft."""
        if self.status != DraftStatus.SCHEDULED:
            raise ValueError(f"Cannot start draft in {self.status.value} status")
        
        if len(self.draft_order) != self.team_count:
            raise ValueError(f"Draft order has {len(self.draft_order)} teams, expected {self.team_count}")
        
        self.status = DraftStatus.IN_PROGRESS
        self.actual_start = func.now()
        self.timer_started_at = func.now()
        self.time_remaining_seconds = self.seconds_per_pick
        
        # Create all draft pick records
        self._create_pick_records()
        
        return True
    
    def _create_pick_records(self):
        """Create all draft pick records for the draft."""
        picks = []
        
        for round_num in range(1, self.rounds + 1):
            # Determine order for this round
            if self.draft_type == DraftType.SNAKE and round_num % 2 == 0:
                # Even round, reverse order
                round_order = list(reversed(self.draft_order))
            else:
                # Odd round or linear draft, normal order
                round_order = self.draft_order
            
            for pick_in_round, team_id in enumerate(round_order):
                pick_number = ((round_num - 1) * self.team_count) + pick_in_round + 1
                
                pick = DraftPick(
                    draft_id=self.id,
                    round=round_num,
                    pick_number=pick_number,
                    team_id=team_id,
                )
                picks.append(pick)
        
        # This would be added to session
        return picks
    
    def make_pick(self, team_id, player_id, position=None):
        """Make a draft pick."""
        if not self.is_active:
            raise ValueError(f"Cannot make pick when draft is {self.status.value}")
        
        if team_id != self.current_team_turn:
            raise ValueError(f"It's not team {team_id}'s turn. Current turn: {self.current_team_turn}")
        
        # Find the current pick record
        current_pick = None
        for pick in self.picks:
            if pick.round == self.current_round and pick.pick_number == self.current_pick:
                current_pick = pick
                break
        
        if not current_pick:
            raise ValueError(f"Could not find pick record for round {self.current_round}, pick {self.current_pick}")
        
        # Update pick
        current_pick.player_id = player_id
        current_pick.position = position
        current_pick.pick_end_time = func.now()
        if current_pick.pick_start_time:
            current_pick.pick_duration_seconds = (
                current_pick.pick_end_time - current_pick.pick_start_time
            ).total_seconds()
        
        # Update draft state
        self.completed_picks.append(current_pick.id)
        
        # Move to next pick
        if self.current_pick < (self.rounds * self.team_count):
            self.current_pick += 1
            self.current_round = ((self.current_pick - 1) // self.team_count) + 1
            
            # Reset timer for next pick
            self.timer_started_at = func.now()
            self.time_remaining_seconds = self.seconds_per_pick
        else:
            # Draft complete
            self.status = DraftStatus.COMPLETED
            self.actual_end = func.now()
        
        # Add to metadata
        pick_info = {
            "round": current_pick.round,
            "pick": current_pick.pick_number,
            "team": team_id,
            "player": player_id,
            "position": position,
            "timestamp": func.now(),
        }
        self.pick_metadata["draft_board"].append(pick_info)
        
        return current_pick
    
    def auto_pick_for_team(self, team_id):
        """Make an auto-pick for a team that's timing out."""
        # This would use the bot's draft strategy to pick
        # For now, placeholder
        from ..services.draft_service import DraftService
        service = DraftService()
        player_id = service.get_best_available_player(team_id, self)
        
        return self.make_pick(team_id, player_id)
    
    def get_available_players(self):
        """Get list of players not yet drafted."""
        # This would query player database and filter out drafted players
        drafted_players = [pick.player_id for pick in self.picks if pick.player_id]
        
        # Placeholder - would query Player model
        return []  # List of player IDs not drafted
    
    def get_draft_board(self):
        """Get visual representation of draft board."""
        board = []
        for round_num in range(1, self.rounds + 1):
            round_picks = []
            for pick in self.picks:
                if pick.round == round_num:
                    round_picks.append({
                        "pick_number": pick.pick_number,
                        "team_id": pick.team_id,
                        "player_id": pick.player_id,
                        "position": pick.position,
                        "was_auto_pick": pick.was_auto_pick,
                    })
            
            # Sort by pick number
            round_picks.sort(key=lambda x: x["pick_number"])
            board.append({
                "round": round_num,
                "picks": round_picks
            })
        
        return board
    
    def get_team_draft_summary(self, team_id):
        """Get draft summary for a specific team."""
        team_picks = []
        for pick in self.picks:
            if pick.team_id == team_id:
                team_picks.append({
                    "round": pick.round,
                    "pick": pick.pick_number,
                    "player_id": pick.player_id,
                    "position": pick.position,
                })
        
        # Sort by round and pick
        team_picks.sort(key=lambda x: (x["round"], x["pick"]))
        
        return {
            "team_id": team_id,
            "total_picks": len(team_picks),
            "picks_by_round": team_picks,
            "positions_drafted": self._count_positions(team_picks),
        }
    
    def _count_positions(self, picks):
        """Count positions drafted."""
        positions = {}
        for pick in picks:
            if pick["position"]:
                positions[pick["position"]] = positions.get(pick["position"], 0) + 1
        return positions