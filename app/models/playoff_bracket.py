from sqlalchemy import Column, Integer, String, JSON, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from ..core.database import Base
import uuid


class BracketType(enum.Enum):
    """Type of playoff bracket."""
    WINNERS = "winners"      # Championship bracket
    LOSERS = "losers"        # Consolation bracket (if applicable)
    TOILET_BOWL = "toilet"   # Last place bracket


class PlayoffBracket(Base):
    __tablename__ = "playoff_brackets"

    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # League reference
    league_id = Column(String, ForeignKey("leagues.id"), nullable=False, index=True)
    
    # Bracket configuration
    bracket_type = Column(Enum(BracketType), nullable=False, default=BracketType.WINNERS)
    name = Column(String, default="Playoffs")  # e.g., "Championship Bracket"
    
    # Bracket structure (inspired by Sleeper's format)
    # Format: List of matchup objects with bracket progression logic
    # Example: [{r: 1, m: 1, t1: 3, t2: 6, w: null, l: null, ...}, ...]
    bracket_structure = Column(JSON, nullable=False, default=[])
    
    # Teams in bracket (team IDs)
    team_ids = Column(JSON, nullable=False, default=[])  # List of team IDs in bracket
    
    # Current round
    current_round = Column(Integer, default=1)
    total_rounds = Column(Integer, default=3)  # Typically 3 rounds for 6-team playoffs
    
    # Status
    is_active = Column(Boolean, default=False)
    is_complete = Column(Boolean, default=False)
    
    # Results
    champion_team_id = Column(String, ForeignKey("teams.id"), index=True)
    runner_up_team_id = Column(String, ForeignKey("teams.id"), index=True)
    
    # Metadata
    bracket_metadata = Column("metadata", JSON, default={
        "description": "",
        "scoring_rules": {},      # Any special playoff scoring rules
        "prize_pool": {},         # Prize distribution
        "history": [],            # Previous champions if multi-year bracket
        "notes": "",              # Commissioner notes
    })
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    league = relationship("League", back_populates="playoff_brackets")
    champion_team = relationship("Team", foreign_keys=[champion_team_id])
    runner_up_team = relationship("Team", foreign_keys=[runner_up_team_id])
    
    def __repr__(self):
        status = "Active" if self.is_active else "Inactive"
        complete = "Complete" if self.is_complete else "Incomplete"
        return f"<PlayoffBracket {self.name} ({self.bracket_type.value}) - {status}, {complete}>"
    
    @property
    def team_count(self):
        """Get number of teams in bracket."""
        return len(self.team_ids) if self.team_ids else 0
    
    @property
    def matchups(self):
        """Get all matchups from bracket structure."""
        return self.bracket_structure
    
    def get_matchup(self, round_num, matchup_num):
        """Get a specific matchup by round and matchup number."""
        for matchup in self.bracket_structure:
            if matchup.get('r') == round_num and matchup.get('m') == matchup_num:
                return matchup
        return None
    
    def get_round_matchups(self, round_num):
        """Get all matchups for a specific round."""
        return [m for m in self.bracket_structure if m.get('r') == round_num]
    
    def get_team_matchups(self, team_id):
        """Get all matchups involving a specific team."""
        team_matchups = []
        for matchup in self.bracket_structure:
            if matchup.get('t1') == team_id or matchup.get('t2') == team_id:
                team_matchups.append(matchup)
        return team_matchups
    
    def update_matchup_result(self, round_num, matchup_num, winner_team_id, loser_team_id):
        """Update a matchup result and propagate winners/losers."""
        matchup = self.get_matchup(round_num, matchup_num)
        if not matchup:
            raise ValueError(f"Matchup not found: Round {round_num}, Matchup {matchup_num}")
        
        # Update this matchup
        matchup['w'] = winner_team_id
        matchup['l'] = loser_team_id
        
        # Propagate to next round matchups
        for next_matchup in self.bracket_structure:
            # Check if next matchup expects winner from this matchup
            if next_matchup.get('t1_from') and next_matchup['t1_from'].get('w') == matchup_num:
                next_matchup['t1'] = winner_team_id
            
            if next_matchup.get('t2_from') and next_matchup['t2_from'].get('w') == matchup_num:
                next_matchup['t2'] = winner_team_id
            
            # Check if next matchup expects loser from this matchup (for losers bracket)
            if next_matchup.get('t1_from') and next_matchup['t1_from'].get('l') == matchup_num:
                next_matchup['t1'] = loser_team_id
            
            if next_matchup.get('t2_from') and next_matchup['t2_from'].get('l') == matchup_num:
                next_matchup['t2'] = loser_team_id
        
        # Check if bracket is complete
        self._check_completion()
        
        return matchup
    
    def _check_completion(self):
        """Check if bracket is complete (championship decided)."""
        if not self.bracket_structure:
            return
        
        # Find championship matchup (highest round)
        max_round = max(m.get('r', 0) for m in self.bracket_structure)
        championship_matchups = self.get_round_matchups(max_round)
        
        if not championship_matchups:
            return
        
        # Check if championship matchup has a winner
        for matchup in championship_matchups:
            if matchup.get('w'):
                self.is_complete = True
                self.completed_at = func.now()
                self.champion_team_id = matchup['w']
                
                # Set runner-up
                if matchup.get('t1') == matchup['w']:
                    self.runner_up_team_id = matchup.get('t2')
                else:
                    self.runner_up_team_id = matchup.get('t1')
                break
    
    def generate_bracket_structure(self, team_ids, bracket_type=BracketType.WINNERS):
        """Generate bracket structure for given teams (inspired by Sleeper format)."""
        team_count = len(team_ids)
        
        if bracket_type == BracketType.WINNERS:
            if team_count == 6:
                # 6-team playoff bracket (common in fantasy)
                # Seeds: 3 vs 6, 4 vs 5 in first round
                # Byes: 1 and 2 get byes
                bracket = [
                    # Round 1 (Quarterfinals)
                    {"r": 1, "m": 1, "t1": 3, "t2": 6, "w": None, "l": None},
                    {"r": 1, "m": 2, "t1": 4, "t2": 5, "w": None, "l": None},
                    
                    # Round 2 (Semifinals)
                    {"r": 2, "m": 3, "t1": 1, "t2": None, "t2_from": {"w": 1}, "w": None, "l": None},
                    {"r": 2, "m": 4, "t1": 2, "t2": None, "t2_from": {"w": 2}, "w": None, "l": None},
                    
                    # Round 3 (Championship)
                    {"r": 3, "m": 5, "t1": None, "t2": None, 
                     "t1_from": {"w": 3}, "t2_from": {"w": 4}, "w": None, "l": None},
                ]
                self.total_rounds = 3
            elif team_count == 4:
                # 4-team playoff bracket
                bracket = [
                    # Round 1 (Semifinals)
                    {"r": 1, "m": 1, "t1": 1, "t2": 4, "w": None, "l": None},
                    {"r": 1, "m": 2, "t1": 2, "t2": 3, "w": None, "l": None},
                    
                    # Round 2 (Championship)
                    {"r": 2, "m": 3, "t1": None, "t2": None,
                     "t1_from": {"w": 1}, "t2_from": {"w": 2}, "w": None, "l": None},
                ]
                self.total_rounds = 2
            else:
                # Generic bracket (supports 2, 4, 8, 16 teams)
                bracket = self._generate_generic_bracket(team_count)
        else:
            # For losers/toilet bowl, simpler bracket
            bracket = self._generate_simple_bracket(team_count)
        
        # Replace seed numbers with actual team IDs
        for matchup in bracket:
            if isinstance(matchup.get('t1'), int) and 1 <= matchup['t1'] <= team_count:
                matchup['t1'] = team_ids[matchup['t1'] - 1]
            if isinstance(matchup.get('t2'), int) and 1 <= matchup['t2'] <= team_count:
                matchup['t2'] = team_ids[matchup['t2'] - 1]
        
        self.bracket_structure = bracket
        self.team_ids = team_ids
        return bracket
    
    def _generate_generic_bracket(self, team_count):
        """Generate generic bracket for power-of-two team counts."""
        bracket = []
        round_num = 1
        match_num = 1
        
        # First round matchups
        for i in range(0, team_count, 2):
            bracket.append({
                "r": round_num, "m": match_num,
                "t1": i + 1, "t2": i + 2,
                "w": None, "l": None
            })
            match_num += 1
        
        # Subsequent rounds
        total_rounds = team_count.bit_length() - 1
        self.total_rounds = total_rounds
        
        for r in range(2, total_rounds + 1):
            matches_in_round = team_count // (2 ** r)
            for m in range(1, matches_in_round + 1):
                prev_match1 = (m - 1) * 2 + 1
                prev_match2 = (m - 1) * 2 + 2
                
                bracket.append({
                    "r": r, "m": match_num,
                    "t1": None, "t2": None,
                    "t1_from": {"w": prev_match1},
                    "t2_from": {"w": prev_match2},
                    "w": None, "l": None
                })
                match_num += 1
        
        return bracket
    
    def _generate_simple_bracket(self, team_count):
        """Generate simple bracket for consolation/losers brackets."""
        bracket = []
        match_num = 1
        
        # Simple single-elimination
        for i in range(0, team_count, 2):
            if i + 2 <= team_count:
                bracket.append({
                    "r": 1, "m": match_num,
                    "t1": i + 1, "t2": i + 2,
                    "w": None, "l": None
                })
                match_num += 1
        
        return bracket
    
    def to_sleeper_format(self):
        """Convert to Sleeper API format."""
        return {
            "bracket_id": self.id,
            "league_id": self.league_id,
            "type": self.bracket_type.value,
            "name": self.name,
            "teams": self.team_ids,
            "current_round": self.current_round,
            "total_rounds": self.total_rounds,
            "is_active": self.is_active,
            "is_complete": self.is_complete,
            "champion": self.champion_team_id,
            "runner_up": self.runner_up_team_id,
            "bracket": self.bracket_structure,
        }