"""
Trade Edge Case Handler & Validation

Handles:
- Empty player lists
- Unknown players
- Value mismatches
- Position validation
- Roster limits
- Trade vetos
- Historical trade analysis
"""
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class TradeValidationError(Exception):
    """Custom exception for trade validation errors."""
    def __init__(self, code: str, message: str, details: Dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code}] {message}")


@dataclass
class ValidationResult:
    """Result of trade validation."""
    is_valid: bool
    errors: List[Dict]
    warnings: List[Dict]
    
    def add_error(self, code: str, message: str, details: Dict = None):
        self.is_valid = False
        self.errors.append({
            "code": code,
            "message": message,
            "details": details or {}
        })
    
    def add_warning(self, code: str, message: str, details: Dict = None):
        self.warnings.append({
            "code": code,
            "message": message,
            "details": details or {}
        })


class TradeValidator:
    """Validates trades for common issues."""
    
    VALID_POSITIONS = {"QB", "RB", "WR", "TE", "FLEX", "K", "DEF", "Pick"}
    MIN_VALUE = 0
    MAX_VALUE = 99999
    MAX_PLAYERS_PER_SIDE = 15
    
    def __init__(self, league_config: Dict = None):
        self.config = league_config or {}
        self.num_teams = self.config.get("num_teams", 12)
    
    def validate_trade(
        self,
        give_players: List[Dict],
        get_players: List[Dict],
        user_roster: List[Dict] = None
    ) -> ValidationResult:
        """
        Comprehensive trade validation.
        
        Checks:
        - Player count limits
        - Value ranges
        - Position validity
        - Roster ownership
        - Roster limit compliance
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Check for empty sides
        if not give_players:
            result.add_error("EMPTY_GIVE", "Trade must include players to give")
        if not get_players:
            result.add_error("EMPTY_GET", "Trade must include players to get")
        
        # Player count limits
        if len(give_players) > self.MAX_PLAYERS_PER_SIDE:
            result.add_error(
                "TOO_MANY_GIVE",
                f"Cannot give more than {self.MAX_PLAYERS_PER_SIDE} players",
                {"count": len(give_players)}
            )
        
        if len(get_players) > self.MAX_PLAYERS_PER_SIDE:
            result.add_error(
                "TOO_MANY_GET",
                f"Cannot get more than {self.MAX_PLAYERS_PER_SIDE} players",
                {"count": len(get_players)}
            )
        
        # Validate each player
        player_names = set()
        for i, player in enumerate(give_players):
            self._validate_player(player, f"give[{i}]", result)
            
            # Check for duplicates
            name = player.get("name", "").lower()
            if name in player_names:
                result.add_warning(
                    "DUPLICATE_PLAYER",
                    f"Duplicate player in give side: {name}",
                    {"index": i}
                )
            player_names.add(name)
        
        player_names = set()
        for i, player in enumerate(get_players):
            self._validate_player(player, f"get[{i}]", result)
            
            name = player.get("name", "").lower()
            if name in player_names:
                result.add_warning(
                    "DUPLICATE_PLAYER",
                    f"Duplicate player in get side: {name}",
                    {"index": i}
                )
            player_names.add(name)
        
        # Check value reasonableness
        give_total = sum(p.get("value", 0) for p in give_players)
        get_total = sum(p.get("value", 0) for p in get_players)
        
        if give_total == 0:
            result.add_warning(
                "ZERO_VALUE_GIVE",
                "All players being given have zero value"
            )
        
        if get_total == 0:
            result.add_warning(
                "ZERO_VALUE_GET",
                "All players being received have zero value"
            )
        
        # Extreme value imbalance
        if give_total > 0 and get_total > 0:
            ratio = max(give_total, get_total) / min(give_total, get_total)
            if ratio > 10:
                result.add_warning(
                    "EXTREME_IMBALANCE",
                    f"Trade value ratio is extreme ({ratio:.1f}x)",
                    {"ratio": ratio}
                )
        
        # Roster ownership validation
        if user_roster:
            self._validate_roster_ownership(
                give_players, user_roster, result
            )
        
        return result
    
    def _validate_player(
        self, 
        player: Dict, 
        path: str,
        result: ValidationResult
    ):
        """Validate a single player."""
        name = player.get("name", "")
        if not name:
            result.add_error(
                "MISSING_NAME",
                f"Player at {path} is missing name",
                {"path": path}
            )
        
        # Value range
        value = player.get("value", 0)
        if value < self.MIN_VALUE:
            result.add_error(
                "NEGATIVE_VALUE",
                f"Player {name} has negative value",
                {"name": name, "value": value}
            )
        if value > self.MAX_VALUE:
            result.add_warning(
                "EXTREME_VALUE",
                f"Player {name} has extreme value",
                {"name": name, "value": value}
            )
        
        # Position validation
        position = player.get("position", "").upper()
        if position and position not in self.VALID_POSITIONS:
            result.add_warning(
                "INVALID_POSITION",
                f"Unknown position: {position}",
                {"name": name, "position": position}
            )
    
    def _validate_roster_ownership(
        self,
        give_players: List[Dict],
        user_roster: List[Dict],
        result: ValidationResult
    ):
        """Validate that user owns the players they're giving."""
        roster_ids = {p.get("player_id") for p in user_roster}
        
        for player in give_players:
            player_id = player.get("player_id")
            if player_id and player_id not in roster_ids:
                result.add_error(
                    "NOT_OWNED",
                    f"User does not own {player.get('name')}",
                    {"player_id": player_id, "name": player.get("name")}
                )


class TradeEdgeCaseHandler:
    """Handles edge cases in trade calculations."""
    
    @staticmethod
    def handle_unknown_players(
        players: List[Dict],
        default_value: int = 500
    ) -> Tuple[List[Dict], List[str]]:
        """
        Handle players with unknown values.
        
        Returns players with assigned default values
        and list of unknown player names.
        """
        unknown = []
        processed = []
        
        for player in players:
            value = player.get("value", 0)
            if value <= 0:
                # Assign default based on position
                position = player.get("position", "").upper()
                if position == "Pick":
                    default_value = 1500  # Mid-late 1st
                elif position == "QB":
                    default_value = 4000
                elif position == "RB":
                    default_value = 3000
                elif position == "WR":
                    default_value = 3500
                elif position == "TE":
                    default_value = 2500
                
                player = {**player, "value": default_value}
                unknown.append(player.get("name", "Unknown"))
            
            processed.append(player)
        
        return processed, unknown
    
    @staticmethod
    def normalize_player_names(players: List[Dict]) -> List[Dict]:
        """Normalize player names for matching."""
        normalized = []
        
        for player in players:
            name = player.get("name", "")
            # Remove suffixes like Jr., Sr., III, etc.
            for suffix in [" Jr.", " Sr.", " II", " III", " IV"]:
                name = name.replace(suffix, "")
            
            normalized.append({**player, "name": name.strip()})
        
        return normalized
    
    @staticmethod
    def calculate_trade_with_picks(
        give: List[Dict],
        get: List[Dict],
        pick_values: Dict[str, int]
    ) -> Dict:
        """
        Calculate trade value including draft picks.
        
        Picks can be specified as strings or dicts.
        """
        def get_pick_value(pick) -> int:
            if isinstance(pick, int):
                return pick
            if isinstance(pick, dict):
                return pick.get("value", 0)
            if isinstance(pick, str):
                return pick_values.get(pick, 0)
            return 0
        
        give_total = sum(
            p.get("value", 0) if not p.get("is_pick") else get_pick_value(p)
            for p in give
        )
        
        get_total = sum(
            p.get("value", 0) if not p.get("is_pick") else get_pick_value(p)
            for p in get
        )
        
        return {
            "give_total": give_total,
            "get_total": get_total,
            "difference": get_total - give_total,
            "is_fair": abs(get_total - give_total) / max(give_total, 1) < 0.15
        }


class TradeHistoryAnalyzer:
    """Analyzes trade history for patterns and fairness."""
    
    def __init__(self, trade_history: List[Dict] = None):
        self.history = trade_history or []
    
    def is_robbery(self, trade_value: float, fair_value: float) -> bool:
        """
        Detect if a trade was a clear robbery.
        
        A trade is considered a robbery if:
        - One side got >50% more value than fair
        - Or one side gave <50% of fair value
        """
        if fair_value <= 0:
            return False
        
        ratio = trade_value / fair_value
        return ratio > 1.5 or ratio < 0.67
    
    def calculate_market_rate(
        self, 
        player_name: str,
        position: str = None
    ) -> Optional[float]:
        """Calculate average market rate for a player from history."""
        rates = []
        
        for trade in self.history:
            for side in [trade.get("give", []), trade.get("get", [])]:
                for player in side:
                    if player.get("name", "").lower() == player_name.lower():
                        if position is None or player.get("position") == position:
                            rates.append(player.get("value", 0))
        
        if rates:
            return sum(rates) / len(rates)
        return None
    
    def find_similar_trades(
        self,
        give_positions: List[str],
        get_positions: List[str],
        tolerance: int = 1
    ) -> List[Dict]:
        """Find historically similar trades."""
        similar = []
        
        for trade in self.history:
            give_pos = set(p.get("position") for p in trade.get("give", []))
            get_pos = set(p.get("position") for p in trade.get("get", []))
            
            # Check if positions match (with tolerance)
            give_match = len(give_pos.symmetric_difference(set(give_positions))) <= tolerance
            get_match = len(get_pos.symmetric_difference(set(get_positions))) <= tolerance
            
            if give_match and get_match:
                similar.append(trade)
        
        return similar[:10]


# ============================================================================
# Robust Trade Evaluator Wrapper
# ============================================================================

def evaluate_trade_robust(
    give_players: List[Dict],
    get_players: List[Dict],
    user_roster: List[Dict] = None,
    league_config: Dict = None,
    pick_values: Dict[str, int] = None
) -> Dict:
    """
    Robust trade evaluation with full edge case handling.
    
    This is the recommended entry point for trade evaluation.
    """
    # Initialize components
    validator = TradeValidator(league_config)
    edge_handler = TradeEdgeCaseHandler()
    
    # Normalize names
    give_players = edge_handler.normalize_player_names(give_players)
    get_players = edge_handler.normalize_player_names(get_players)
    
    # Handle unknown players
    give_players, give_unknown = edge_handler.handle_unknown_players(give_players)
    get_players, get_unknown = edge_handler.handle_unknown_players(get_players)
    
    # Validate
    validation = validator.validate_trade(give_players, get_players, user_roster)
    
    # Build warnings from unknown players
    warnings = validation.warnings.copy()
    if give_unknown:
        warnings.append({
            "code": "UNKNOWN_GIVE",
            "message": f"Assigned default values to: {', '.join(give_unknown)}"
        })
    if get_unknown:
        warnings.append({
            "code": "UNKNOWN_GET",
            "message": f"Assigned default values to: {', '.join(get_unknown)}"
        })
    
    # Calculate trade value
    trade_calc = edge_handler.calculate_trade_with_picks(
        give_players, get_players, pick_values or {}
    )
    
    # Determine fairness
    is_fair = trade_calc["is_fair"] and validation.is_valid
    
    return {
        "is_valid": validation.is_valid,
        "is_fair": is_fair,
        "errors": validation.errors,
        "warnings": warnings,
        "give_total": trade_calc["give_total"],
        "get_total": trade_calc["get_total"],
        "difference": trade_calc["difference"],
        "unknown_players": {
            "give": give_unknown,
            "get": get_unknown
        }
    }


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    # Test validation
    validator = TradeValidator({"num_teams": 12})
    
    # Valid trade
    valid_trade = [
        {"name": "Ja'Marr Chase", "value": 10500, "position": "WR"},
        {"name": "Bijan Robinson", "value": 8500, "position": "RB"}
    ], [
        {"name": "C.J. Stroud", "value": 9500, "position": "QB"},
        {"name": "2026 1.05", "value": 5000, "position": "Pick", "is_pick": True}
    ]
    
    result = validator.validate_trade(*valid_trade)
    print("Valid trade validation:")
    print(f"  Valid: {result.is_valid}")
    print(f"  Errors: {len(result.errors)}")
    print(f"  Warnings: {len(result.warnings)}")
    
    # Invalid trade (empty)
    invalid_trade = [], [{"name": "Player", "value": 1000}]
    result = validator.validate_trade(*invalid_trade)
    print("\nInvalid trade (empty give):")
    print(f"  Valid: {result.is_valid}")
    print(f"  Errors: {result.errors}")
