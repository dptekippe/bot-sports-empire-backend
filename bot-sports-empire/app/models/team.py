from sqlalchemy import Column, Integer, String, JSON, DateTime, Boolean, ForeignKey, Float, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..core.database import Base
import uuid


class Team(Base):
    __tablename__ = "teams"

    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Basic info
    name = Column(String, nullable=False, index=True)
    abbreviation = Column(String(4))  # 3-4 letter abbreviation
    
    # Relationships
    league_id = Column(String, ForeignKey("leagues.id"), nullable=False, index=True)
    bot_id = Column(String, ForeignKey("bot_agents.id"), nullable=False, index=True)
    
    # Roster management
    roster = Column(JSON, default={
        "QB": [],      # List of player IDs
        "RB": [],
        "WR": [],
        "TE": [],
        "K": [],
        "DEF": [],
        "FLEX": [],
        "BN": [],      # Bench
        "IR": [],      # Injured Reserve
    })
    
    # Current lineup (for this week)
    current_lineup = Column(JSON, default={
        "QB": None,
        "RB1": None,
        "RB2": None,
        "WR1": None,
        "WR2": None,
        "TE": None,
        "FLEX": None,
        "K": None,
        "DEF": None,
    })
    
    # Season statistics
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    ties = Column(Integer, default=0)
    points_for = Column(Float, default=0.0)
    points_against = Column(Float, default=0.0)
    
    # Weekly performance tracking
    weekly_scores = Column(JSON, default={})  # {week_number: score}
    weekly_results = Column(JSON, default={}) # {week_number: "W"/"L"/"T"}
    
    # Draft picks (if draft completed)
    draft_picks = Column(JSON, default=[])  # List of player IDs in draft order
    
    # Transaction history
    transactions = Column(JSON, default={
        "trades": [],
        "waiver_adds": [],
        "waiver_drops": [],
        "free_agent_adds": [],
    })
    
    # FAAB (Free Agent Acquisition Budget) management
    faab_balance = Column(Integer, default=100)  # Starting budget
    faab_spent = Column(Integer, default=0)
    
    # Team settings
    is_active = Column(Boolean, default=True)
    auto_pilot = Column(Boolean, default=False)  # If bot isn't responding
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_activity = Column(DateTime(timezone=True))
    
    # Relationships
    league = relationship("League", back_populates="teams")
    bot = relationship("BotAgent", back_populates="teams")
    home_matchups = relationship("Matchup", foreign_keys="[Matchup.home_team_id]", back_populates="home_team")
    away_matchups = relationship("Matchup", foreign_keys="[Matchup.away_team_id]", back_populates="away_team")
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint('league_id', 'bot_id', name='uq_team_league_bot'),
    )
    
    def __repr__(self):
        return f"<Team {self.name} (Bot: {self.bot.name if self.bot else 'Unknown'})>"
    
    @property
    def win_percentage(self):
        total_games = self.wins + self.losses + self.ties
        if total_games == 0:
            return 0.0
        return (self.wins + (0.5 * self.ties)) / total_games
    
    @property
    def points_differential(self):
        return self.points_for - self.points_against
    
    @property
    def average_points_per_game(self):
        total_games = self.wins + self.losses + self.ties
        if total_games == 0:
            return 0.0
        return self.points_for / total_games
    
    @property
    def record(self):
        return f"{self.wins}-{self.losses}-{self.ties}"
    
    @property
    def remaining_faab(self):
        return self.faab_balance - self.faab_spent
    
    def add_player_to_roster(self, player_id, position):
        """Add a player to the roster at a specific position."""
        if position not in self.roster:
            raise ValueError(f"Invalid position: {position}")
        
        # Check if player is already on roster
        for pos, players in self.roster.items():
            if player_id in players:
                raise ValueError(f"Player {player_id} already on roster at position {pos}")
        
        # Add player to position
        self.roster[position].append(player_id)
        return True
    
    def remove_player_from_roster(self, player_id):
        """Remove a player from the roster."""
        for position, players in self.roster.items():
            if player_id in players:
                players.remove(player_id)
                return position
        raise ValueError(f"Player {player_id} not found on roster")
    
    def set_lineup(self, lineup_dict):
        """Set the current week's lineup."""
        # Validate all players are on roster
        roster_players = []
        for position_players in self.roster.values():
            roster_players.extend(position_players)
        
        for position, player_id in lineup_dict.items():
            if player_id and player_id not in roster_players:
                raise ValueError(f"Player {player_id} not on roster for position {position}")
        
        self.current_lineup = lineup_dict
        return True
    
    def get_starting_lineup(self):
        """Get the current starting lineup with player details."""
        # This would need player service to resolve player IDs to names
        return {
            position: player_id
            for position, player_id in self.current_lineup.items()
            if player_id
        }
    
    def get_bench_players(self):
        """Get all players not in the starting lineup."""
        starting_players = set()
        for player_id in self.current_lineup.values():
            if player_id:
                starting_players.add(player_id)
        
        bench_players = []
        for position, players in self.roster.items():
            for player_id in players:
                if player_id not in starting_players:
                    bench_players.append({
                        "player_id": player_id,
                        "position": position
                    })
        
        return bench_players
    
    def add_transaction(self, transaction_type, details):
        """Record a transaction (trade, waiver, etc.)."""
        if transaction_type not in self.transactions:
            raise ValueError(f"Invalid transaction type: {transaction_type}")
        
        transaction_record = {
            "id": str(uuid.uuid4()),
            "type": transaction_type,
            "details": details,
            "timestamp": func.now(),
            "week": self._get_current_week()  # Would need league context
        }
        
        self.transactions[transaction_type].append(transaction_record)
        return transaction_record
    
    def spend_faab(self, amount, description):
        """Spend FAAB money on a transaction."""
        if amount > self.remaining_faab:
            raise ValueError(f"Insufficient FAAB. Have {self.remaining_faab}, need {amount}")
        
        self.faab_spent += amount
        
        transaction = {
            "type": "faab_spent",
            "amount": amount,
            "description": description,
            "remaining": self.remaining_faab,
            "timestamp": func.now()
        }
        
        self.add_transaction("waiver_adds", transaction)
        return transaction
    
    def update_weekly_result(self, week, score, opponent_score):
        """Update team record after a week's matchup."""
        self.weekly_scores[str(week)] = score
        self.points_for += score
        self.points_against += opponent_score
        
        if score > opponent_score:
            self.wins += 1
            result = "W"
        elif score < opponent_score:
            self.losses += 1
            result = "L"
        else:
            self.ties += 1
            result = "T"
        
        self.weekly_results[str(week)] = result
        return result
    
    def _get_current_week(self):
        """Helper to get current week (would need league context)."""
        # This would be implemented with league service
        return 1  # Placeholder