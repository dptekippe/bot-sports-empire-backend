"""
Enhanced Trade Evaluator - Robust dynasty trade analysis.

Features:
- Multi-source value integration
- Dynamic draft pick valuation
- Positional need analysis
- Team classification (win-now/rebuild)
- Trade suggestions
- Error handling
"""
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from app.services.trade_values import (
    DynastyValueService, get_value_service, SOURCE_WEIGHTS
)

logger = logging.getLogger(__name__)


@dataclass
class PlayerValue:
    """Player with dynasty value."""
    player_id: str
    name: str
    position: str
    team: str
    value: int
    age: Optional[float] = None
    is_pick: bool = False


@dataclass
class TradeAnalysis:
    """Complete trade analysis result."""
    outgoing_players: List[PlayerValue]
    incoming_players: List[PlayerValue]
    outgoing_value: int
    incoming_value: int
    value_difference: int
    is_fair: bool
    fairness_details: Dict[str, Any]
    positional_need_outgoing: Dict[str, float]
    positional_need_incoming: Dict[str, float]
    team_classification: str
    narrative: str
    suggestions: List[str] = field(default_factory=list)


@dataclass
class LeagueConfig:
    """Configurable league settings."""
    num_teams: int = 12
    format: str = "2qb"  # "1qb" or "2qb" (superflex)
    flex: int = 3
    te_premium: bool = False
    fair_margin: float = 0.15
    ppr: float = 1.0
    
    def __post_init__(self):
        # Compute league average starters
        self.league_average_starters = self._compute_averages()
    
    def _compute_averages(self) -> Dict[str, int]:
        base = {
            "QB": self.num_teams,
            "RB": self.num_teams * 2 + self.flex,
            "WR": self.num_teams * 3 + self.flex,
            "TE": self.num_teams
        }
        if self.format == "Superflex":
            base["QB"] += self.num_teams  # Extra QB starter
        if self.te_premium:
            base["TE"] += self.num_teams // 2
        return base


class RosterAnalyzer:
    """Analyzes roster strength and positional needs."""
    
    def __init__(
        self,
        roster_players: List[PlayerValue],
        future_picks: List[str] = None,
        config: LeagueConfig = None
    ):
        self.players = roster_players
        self.future_picks = future_picks or []
        self.config = config or LeagueConfig()
        self.by_position: Dict[str, Dict] = {}
        self.total_value = 0
        self.total_age = 0
        self.players_with_age = 0
        self.pick_value = 0
        self.average_age: Optional[float] = None
        
        self._calculate_stats()
    
    def _calculate_stats(self):
        """Pre-calculate roster statistics."""
        self.by_position = {}
        self.total_value = 0
        self.total_age = 0
        self.players_with_age = 0
        
        # Calculate draft pick value
        self.pick_value = sum(
            self.config.league_average_starters.get(p, 0) 
            for p in self.future_picks
        )
        
        for p in self.players:
            self.total_value += p.value
            
            pos_data = self.by_position.setdefault(p.position, {
                "players": [], "value": 0, "count": 0
            })
            pos_data["players"].append(p)
            pos_data["value"] += p.value
            pos_data["count"] += 1
            
            if p.age:
                self.total_age += p.age
                self.players_with_age += 1
        
        self.average_age = (
            self.total_age / self.players_with_age 
            if self.players_with_age > 0 else None
        )
    
    def get_positional_value(self, position: str) -> int:
        return self.by_position.get(position, {}).get("value", 0)
    
    def get_positional_count(self, position: str) -> int:
        return self.by_position.get(position, {}).get("count", 0)
    
    def calculate_positional_need(self, position: str) -> float:
        """Value-weighted need score (0-10 scale)."""
        starters = self.config.league_average_starters.get(position, 24)
        count = self.get_positional_count(position)
        value = self.get_positional_value(position)
        
        if count == 0:
            return 10.0  # Maximum need
        
        ratio_count = count / starters
        # Normalize value (assume ~50 pts per starter quality)
        ratio_value = value / (starters * 50) if starters else 1
        
        need = 5 + (1 - min(ratio_count, ratio_value)) * 5
        return max(0, min(10, need))
    
    def classify_team(self) -> str:
        """Classify team as win-now, neutral, or rebuild."""
        if not self.average_age:
            return "neutral"
        
        # Win-now: older team OR older with few picks
        if self.average_age > 27 or (self.average_age > 26 and self.pick_value < 50):
            return "win_now"
        
        # Rebuild: young team OR lots of draft capital
        if self.average_age < 24 or self.pick_value > 200:
            return "rebuild"
        
        return "neutral"
    
    def get_strengths(self) -> List[str]:
        return [
            pos for pos in ["QB", "RB", "WR", "TE"] 
            if self.calculate_positional_need(pos) < 3
        ]
    
    def get_weaknesses(self) -> List[str]:
        return [
            pos for pos in ["QB", "RB", "WR", "TE"] 
            if self.calculate_positional_need(pos) > 7
        ]


class TradeEvaluator:
    """Evaluates dynasty trades with enhanced analysis."""
    
    def __init__(
        self, 
        roster_analyzer: RosterAnalyzer, 
        value_service: DynastyValueService = None,
        fair_margin: float = 0.15
    ):
        self.roster = roster_analyzer
        self.value_service = value_service or get_value_service()
        self.fair_margin = fair_margin
    
    def _get_roster_after_trade(
        self,
        exclude_players: List[PlayerValue],
        add_players: List[PlayerValue]
    ) -> List[PlayerValue]:
        """Simulate roster after trade."""
        exclude_ids = {p.player_id for p in exclude_players}
        after = [
            p for p in self.roster.players 
            if p.player_id not in exclude_ids
        ]
        after.extend(add_players)
        return after
    
    def evaluate(
        self,
        outgoing_players: List[PlayerValue],
        incoming_players: List[PlayerValue]
    ) -> TradeAnalysis:
        """Evaluate a trade proposal."""
        if not outgoing_players:
            raise ValueError("Trade must include outgoing players")
        if not incoming_players:
            raise ValueError("Trade must include incoming players")
        
        outgoing_value = sum(p.value for p in outgoing_players)
        incoming_value = sum(p.value for p in incoming_players)
        
        # Use value service for fairness calculation
        fairness = self.value_service.calculate_trade_fairness(
            outgoing_value, incoming_value, self.fair_margin
        )
        
        config = self.roster.config
        
        # Calculate needs after trade
        out_after = self._get_roster_after_trade(outgoing_players, incoming_players)
        out_analyzer = RosterAnalyzer(
            out_after, self.roster.future_picks, config
        )
        outgoing_need = {
            pos: out_analyzer.calculate_positional_need(pos) 
            for pos in ["QB", "RB", "WR", "TE"]
        }
        
        in_after = self._get_roster_after_trade(incoming_players, outgoing_players)
        in_analyzer = RosterAnalyzer(
            in_after, self.roster.future_picks, config
        )
        incoming_need = {
            pos: in_analyzer.calculate_positional_need(pos) 
            for pos in ["QB", "RB", "WR", "TE"]
        }
        
        team_classification = self.roster.classify_team()
        
        # Generate narrative and suggestions
        narrative = self._generate_narrative(
            outgoing_players, incoming_players, fairness,
            outgoing_need, incoming_need, team_classification
        )
        
        suggestions = self._generate_suggestions(
            outgoing_players, incoming_players, fairness,
            outgoing_need, incoming_need
        )
        
        return TradeAnalysis(
            outgoing_players=outgoing_players,
            incoming_players=incoming_players,
            outgoing_value=outgoing_value,
            incoming_value=incoming_value,
            value_difference=fairness.get("difference", incoming_value - outgoing_value),
            is_fair=fairness.get("is_fair", False),
            fairness_details=fairness,
            positional_need_outgoing=outgoing_need,
            positional_need_incoming=incoming_need,
            team_classification=team_classification,
            narrative=narrative,
            suggestions=suggestions
        )
    
    def _generate_narrative(
        self,
        outgoing: List[PlayerValue],
        incoming: List[PlayerValue],
        fairness: Dict[str, Any],
        out_need: Dict[str, float],
        in_need: Dict[str, float],
        team_type: str
    ) -> str:
        """Generate Roger-style analysis narrative."""
        parts = []
        
        # Value summary
        diff = fairness.get("difference", 0)
        if diff > 500:
            parts.append(f"Winning by {diff:,.0f} in value.")
        elif diff < -500:
            parts.append(f"Giving up {abs(diff):,.0f} in value - need more coming back.")
        else:
            parts.append("Value is relatively even.")
        
        # Fairness
        verdict = fairness.get("verdict", "FAIR")
        if verdict == "YOU_WIN":
            parts.append("You're getting a great deal!")
        elif verdict == "THEY_WIN":
            parts.append("You're overpaying significantly.")
        else:
            parts.append("Fair trade from a value perspective.")
        
        # Positional impact
        incoming_pos = {p.position for p in incoming}
        for pos in incoming_pos:
            need = in_need.get(pos, 5)
            if need > 7:
                player = next(
                    (p.name for p in incoming if p.position == pos), 
                    "this player"
                )
                parts.append(
                    f"Immediately addresses your {pos} need "
                    f"({need:.1f}/10 need score)."
                )
            elif need < 3:
                parts.append(f"Note: You already have strong {pos} depth.")
        
        # Weaknesses exposed
        outgoing_pos = {p.position for p in outgoing}
        for pos in outgoing_pos:
            need = out_need.get(pos, 5)
            if need > 7:
                parts.append(f"WARNING: You're dealing from a weak {pos} position.")
        
        # Team context
        if team_type == "win_now":
            if diff < 0:
                parts.append("For a contender, this is a smart win-now move.")
            else:
                parts.append("As a contender, you might be overpaying for future assets.")
        elif team_type == "rebuild":
            if diff > 0:
                parts.append("Good asset accumulation for a rebuilding roster.")
            else:
                parts.append(
                    "Selling youth/picks for aging assets goes against your rebuild."
                )
        
        return " ".join(parts)
    
    def _generate_suggestions(
        self,
        outgoing: List[PlayerValue],
        incoming: List[PlayerValue],
        fairness: Dict[str, Any],
        out_need: Dict[str, float],
        in_need: Dict[str, float]
    ) -> List[str]:
        """Generate actionable trade suggestions."""
        suggestions = []
        
        diff = fairness.get("difference", 0)
        give_value = fairness.get("give_value", 0)
        
        # Value balancing suggestions
        if diff < -give_value * 0.1:  # They're winning by >10%
            needed = abs(diff)
            suggestions.append(
                f"Request ~{needed:,.0f} more value in return"
            )
        
        # Positional need suggestions
        for pos in ["QB", "RB", "WR", "TE"]:
            in_pos_need = in_need.get(pos, 5)
            if in_pos_need > 6:
                suggestions.append(
                    f"Target {pos} players - you have a significant need"
                )
        
        return suggestions


def analyze_trade(
    user_roster: List[Dict],
    outgoing_player_ids: List[str],
    incoming_player_ids: List[str],
    player_values: Dict[str, int],
    player_details: Dict[str, Dict],
    config: LeagueConfig = None
) -> Dict[str, Any]:
    """
    Main entry point for trade analysis.
    
    Args:
        user_roster: List of player dicts from league API
        outgoing_player_ids: Sleeper IDs being traded away
        incoming_player_ids: Sleeper IDs being acquired
        player_values: Dict of player_name -> dynasty value
        player_details: Dict of player_id -> player info from Sleeper
        config: LeagueConfig for settings
    
    Returns:
        TradeAnalysis as dict
    """
    config = config or LeagueConfig()
    value_service = get_value_service()
    
    def build_player(player_id: str) -> Optional[PlayerValue]:
        """Build PlayerValue from player ID."""
        details = player_details.get(player_id, {})
        if not details:
            return None
            
        name = f"{details.get('first_name', '')} {details.get('last_name', '')}".strip()
        value = player_values.get(name, 0)
        
        if not value:
            return None
        
        # Parse age
        age = None
        if details.get("age"):
            try:
                age = float(details.get("age"))
            except (ValueError, TypeError):
                pass
        
        # Check if draft pick
        is_pick = details.get("position") == "Pick" or "pick" in name.lower()
        
        return PlayerValue(
            player_id=player_id,
            name=name,
            position=details.get("position", "UNK"),
            team=details.get("team", "UNK"),
            value=value,
            age=age,
            is_pick=is_pick
        )
    
    # Validate inputs
    if not outgoing_player_ids:
        return {"error": "Must specify outgoing players"}
    if not incoming_player_ids:
        return {"error": "Must specify incoming players"}
    
    # Build player objects
    outgoing = [build_player(pid) for pid in outgoing_player_ids]
    outgoing = [p for p in outgoing if p]
    
    incoming = [build_player(pid) for pid in incoming_player_ids]
    incoming = [p for p in incoming if p]
    
    if not outgoing:
        return {"error": "Could not find values for outgoing players"}
    if not incoming:
        return {"error": "Could not find values for incoming players"}
    
    # Build roster (exclude outgoing)
    outgoing_ids = set(outgoing_player_ids)
    roster_players = []
    for p in user_roster:
        pid = p.get("player_id")
        if pid and pid not in outgoing_ids:
            player = build_player(pid)
            if player:
                roster_players.append(player)
    
    # Analyze
    analyzer = RosterAnalyzer(roster_players, config=config)
    evaluator = TradeEvaluator(analyzer, value_service, fair_margin=config.fair_margin)
    
    try:
        analysis = evaluator.evaluate(outgoing, incoming)
    except ValueError as e:
        return {"error": str(e)}
    
    return {
        "outgoing": [
            {
                "player_id": p.player_id,
                "name": p.name,
                "position": p.position,
                "value": p.value
            } 
            for p in analysis.outgoing_players
        ],
        "incoming": [
            {
                "player_id": p.player_id,
                "name": p.name,
                "position": p.position,
                "value": p.value
            } 
            for p in analysis.incoming_players
        ],
        "outgoing_value": analysis.outgoing_value,
        "incoming_value": analysis.incoming_value,
        "value_difference": analysis.value_difference,
        "is_fair": analysis.is_fair,
        "fairness_details": analysis.fairness_details,
        "team_classification": analysis.team_classification,
        "strengths": analyzer.get_strengths(),
        "weaknesses": analyzer.get_weaknesses(),
        "narrative": analysis.narrative,
        "suggestions": analysis.suggestions
    }


# Alias for backward compatibility
LeagueConfigV2 = LeagueConfig
