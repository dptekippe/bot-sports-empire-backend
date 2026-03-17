"""
Trade Evaluation Service - Analyzes dynasty trades with AI narratives.

Enhanced for robustness per industry standards (DLF, KTC, FantasyPros).
"""
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from functools import lru_cache

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


@dataclass
class TradeAnalysis:
    """Complete trade analysis result."""
    outgoing_players: List[PlayerValue]
    incoming_players: List[PlayerValue]
    outgoing_value: int
    incoming_value: int
    value_difference: int
    is_fair: bool
    fairness_margin: float
    positional_need_outgoing: Dict[str, float]
    positional_need_incoming: Dict[str, float]
    team_classification: str
    narrative: str


class LeagueConfig:
    """Configurable league settings per industry tools."""
    
    def __init__(
        self,
        num_teams: int = 12,
        format_: str = "1QB",
        flex: int = 3,
        te_premium: bool = False,
        fair_margin: float = 0.15
    ):
        self.num_teams = num_teams
        self.format_ = format_  # "1QB" or "Superflex"
        self.flex = flex
        self.te_premium = te_premium
        self.fair_margin = fair_margin
        self.league_average_starters = self._compute_averages()
    
    def _compute_averages(self) -> Dict[str, int]:
        base = {
            "QB": self.num_teams,
            "RB": self.num_teams * 2 + self.flex,
            "WR": self.num_teams * 3 + self.flex,
            "TE": self.num_teams
        }
        if self.format_ == "Superflex":
            base["QB"] += self.num_teams  # Extra QB starter
        if self.te_premium:
            base["TE"] += self.num_teams // 2
        return base


# Draft pick values (2026 1QB PPR - extendable)
DRAFT_PICK_VALUES = {
    # 2026 Picks
    "2026_1.01": 68, "2026_1.02": 58, "2026_1.03": 52, "2026_1.04": 48,
    "2026_1.05": 44, "2026_1.06": 40, "2026_1.07": 37, "2026_1.08": 34,
    "2026_1.09": 31, "2026_1.10": 28, "2026_1.11": 25, "2026_1.12": 22,
    "2026_2.01": 20, "2026_2.02": 18, "2026_2.03": 16, "2026_2.04": 14,
    "2026_2.05": 12, "2026_2.06": 10, "2026_2.07": 9, "2026_2.08": 8,
    "2026_2.09": 7, "2026_2.10": 6, "2026_2.11": 5, "2026_2.12": 4,
    # Future picks (discounted)
    "2027_1.01": 66, "2027_1.02": 56, "2027_1.03": 50,
}


def parse_draft_pick(pick_str: str) -> int:
    """Parse draft pick string to value."""
    # Try exact match
    if pick_str in DRAFT_PICK_VALUES:
        return DRAFT_PICK_VALUES[pick_str]
    
    # Try partial match (e.g., "2026_1st" matches 2026_1.01)
    for key, value in DRAFT_PICK_VALUES.items():
        if key.startswith(pick_str.split("_")[0] if "_" in pick_str else pick_str[:4]):
            return value
    
    return 0  # Default unknown pick


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
        self.pick_value = sum(parse_draft_pick(p) for p in self.future_picks)
        
        for p in self.players:
            self.total_value += p.value
            
            pos_data = self.by_position.setdefault(p.position, {"players": [], "value": 0, "count": 0})
            pos_data["players"].append(p)
            pos_data["value"] += p.value
            pos_data["count"] += 1
            
            if p.age:
                self.total_age += p.age
                self.players_with_age += 1
        
        self.average_age = self.total_age / self.players_with_age if self.players_with_age > 0 else None
    
    def get_positional_value(self, position: str) -> int:
        return self.by_position.get(position, {}).get("value", 0)
    
    def get_positional_count(self, position: str) -> int:
        return self.by_position.get(position, {}).get("count", 0)
    
    def calculate_positional_need(self, position: str) -> float:
        """Value-weighted need score (improved)."""
        starters = self.config.league_average_starters.get(position, 24)
        count = self.get_positional_count(position)
        value = self.get_positional_value(position)
        
        if count == 0:
            return 10.0
        
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
        return [pos for pos in ["QB", "RB", "WR", "TE"] 
                if self.calculate_positional_need(pos) < 3]
    
    def get_weaknesses(self) -> List[str]:
        return [pos for pos in ["QB", "RB", "WR", "TE"] 
                if self.calculate_positional_need(pos) > 7]


class TradeEvaluator:
    """Evaluates dynasty trades."""
    
    def __init__(self, roster_analyzer: RosterAnalyzer, fair_margin: float = 0.15):
        self.roster = roster_analyzer
        self.fair_margin = fair_margin
    
    def _get_roster_after_trade(
        self,
        exclude_players: List[PlayerValue],
        add_players: List[PlayerValue]
    ) -> List[PlayerValue]:
        """ID-based roster simulation (robust)."""
        exclude_ids = {p.player_id for p in exclude_players}
        after = [p for p in self.roster.players if p.player_id not in exclude_ids]
        after.extend(add_players)
        return after
    
    def evaluate(
        self,
        outgoing_players: List[PlayerValue],
        incoming_players: List[PlayerValue]
    ) -> TradeAnalysis:
        """Evaluate a trade proposal."""
        if not outgoing_players or not incoming_players:
            raise ValueError("Trade must include players on both sides")
        
        outgoing_value = sum(p.value for p in outgoing_players)
        incoming_value = sum(p.value for p in incoming_players)
        value_difference = incoming_value - outgoing_value
        
        fairness_margin = abs(value_difference) / outgoing_value if outgoing_value > 0 else 1.0
        is_fair = fairness_margin <= self.fair_margin
        
        config = self.roster.config
        
        # Calculate needs after trade
        out_after = self._get_roster_after_trade(outgoing_players, incoming_players)
        out_analyzer = RosterAnalyzer(out_after, self.roster.future_picks, config)
        outgoing_need = {pos: out_analyzer.calculate_positional_need(pos) for pos in ["QB", "RB", "WR", "TE"]}
        
        in_after = self._get_roster_after_trade(incoming_players, outgoing_players)
        in_analyzer = RosterAnalyzer(in_after, self.roster.future_picks, config)
        incoming_need = {pos: in_analyzer.calculate_positional_need(pos) for pos in ["QB", "RB", "WR", "TE"]}
        
        team_classification = self.roster.classify_team()
        narrative = self._generate_narrative(
            outgoing_players, incoming_players, value_difference, is_fair,
            outgoing_need, incoming_need, team_classification
        )
        
        return TradeAnalysis(
            outgoing_players=outgoing_players,
            incoming_players=incoming_players,
            outgoing_value=outgoing_value,
            incoming_value=incoming_value,
            value_difference=value_difference,
            is_fair=is_fair,
            fairness_margin=fairness_margin,
            positional_need_outgoing=outgoing_need,
            positional_need_incoming=incoming_need,
            team_classification=team_classification,
            narrative=narrative
        )
    
    def _generate_narrative(
        self,
        outgoing: List[PlayerValue],
        incoming: List[PlayerValue],
        value_diff: int,
        is_fair: bool,
        out_need: Dict[str, float],
        in_need: Dict[str, float],
        team_type: str
    ) -> str:
        """Generate Roger-style analysis narrative."""
        parts = []
        
        # Value summary
        if value_diff > 500:
            parts.append(f"Winning by {value_diff:,} in value.")
        elif value_diff < -500:
            parts.append(f"Giving up {abs(value_diff):,} in value - need more coming back.")
        else:
            parts.append("Value is relatively even.")
        
        # Fairness
        if is_fair:
            parts.append("Fair trade from a value perspective.")
        else:
            if value_diff > 0:
                parts.append("You're overpaying significantly.")
            else:
                parts.append("You're getting a bargain.")
        
        # Positional impact
        incoming_pos = {p.position for p in incoming}
        for pos in incoming_pos:
            need = in_need.get(pos, 5)
            if need > 7:
                player = next((p.name for p in incoming if p.position == pos), "this player")
                parts.append(f"Immediately addresses your {pos} need ({need:.1f}/10 need score).")
            elif need < 3:
                parts.append(f"Note: You already have strong {pos} depth.")
        
        outgoing_pos = {p.position for p in outgoing}
        for pos in outgoing_pos:
            need = out_need.get(pos, 5)
            if need > 7:
                parts.append(f"WARNING: You're dealing from a weak {pos} position.")
        
        # Team context
        if team_type == "win_now":
            if value_diff < 0:
                parts.append("For a contender, this is a smart win-now move.")
            else:
                parts.append("As a contender, you might be overpaying for future assets.")
        elif team_type == "rebuild":
            if value_diff > 0:
                parts.append("Good asset accumulation for a rebuilding roster.")
            else:
                parts.append("Selling youth/picks for aging assets goes against your rebuild.")
        
        return " ".join(parts)


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
        incoming_player_ids: Sleeeper IDs being acquired
        player_values: Dict of player_name -> dynasty value
        player_details: Dict of player_id -> player info from Sleeper
        config: LeagueConfig for settings
    
    Returns:
        TradeAnalysis as dict
    """
    config = config or LeagueConfig()
    
    # Build player objects
    def build_player(player_id: str) -> Optional[PlayerValue]:
        details = player_details.get(player_id, {})
        if not details:
            return None
            
        name = f"{details.get('first_name', '')} {details.get('last_name', '')}".strip()
        value = player_values.get(name, 0)
        
        if not value:
            return None
        
        # Get age if available
        age = None
        if details.get("age"):
            try:
                age = float(details.get("age"))
            except (ValueError, TypeError):
                pass
        
        return PlayerValue(
            player_id=player_id,
            name=name,
            position=details.get("position", "UNK"),
            team=details.get("team", "UNK"),
            value=value,
            age=age
        )
    
    # Validate inputs
    if not outgoing_player_ids or not incoming_player_ids:
        return {"error": "Trade must include players on both sides"}
    
    # Get players
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
    evaluator = TradeEvaluator(analyzer, fair_margin=config.fair_margin)
    
    try:
        analysis = evaluator.evaluate(outgoing, incoming)
    except ValueError as e:
        return {"error": str(e)}
    
    return {
        "outgoing": [
            {"player_id": p.player_id, "name": p.name, "position": p.position, "value": p.value} 
            for p in analysis.outgoing_players
        ],
        "incoming": [
            {"player_id": p.player_id, "name": p.name, "position": p.position, "value": p.value} 
            for p in analysis.incoming_players
        ],
        "outgoing_value": analysis.outgoing_value,
        "incoming_value": analysis.incoming_value,
        "value_difference": analysis.value_difference,
        "is_fair": analysis.is_fair,
        "fairness_margin": round(analysis.fairness_margin, 2),
        "team_classification": analysis.team_classification,
        "strengths": analyzer.get_strengths(),
        "weaknesses": analyzer.get_weaknesses(),
        "narrative": analysis.narrative
    }
