"""
Enhanced Dynasty Trade Calculator

Advanced features:
- Age-based value adjustment (career stage modeling)
- Contract/year modeling (RFAs, franchise tags)
- Stud dominance bonus (KTC-style)
- Multi-player package valuation
- Trade equity curves
"""
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Constants
# Value uncertainty ranges (standard deviation as % of value)
VALUE_UNCERTAINTY = {
    "elite": 0.08,    # Top 5 at position
    "starter": 0.12,  # Top 24 at position
    "rotation": 0.18, # Backup/flex
    "rookie": 0.20,   # Rookies more volatile
    "pick": 0.25,     # Picks very uncertain
}


@dataclass
class TradeScenario:
    """Represents a single scenario in multi-scenario analysis."""
    give_total: float
    get_total: float
    verdict: str
    difference: float
    margin: float
    probability: float = 1.0


@dataclass
class TradeResult:
    """Enhanced trade result with confidence intervals and scenarios."""
    # Core metrics
    give_total_raw: float
    get_total_raw: float
    give_total_adjusted: float
    get_total_adjusted: float
    difference: float
    margin: float
    
    # Fairness assessment
    is_fair: bool
    verdict: str
    recommendation: str
    
    # Bonuses
    stud_bonus: float
    stud_description: str
    
    # New fields
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    confidence_level: float = 0.0  # 0-1
    trade_grade: str = ""  # A+, A, B+, B, C, D, F
    scenarios: List[TradeScenario] = field(default_factory=list)
    player_details: Dict = field(default_factory=dict)
    market_notes: List[str] = field(default_factory=list)
    error_margin_pct: float = 0.0
KTC_MAX = 9999
KTC_POWER = 1.8085
AGE_PEAK = 26  # Peak performance age
AGE_DECLINE_START = 28  # When decline begins
DECLINE_RATE = 0.05  # 5% value decline per year after peak

# Position-based value curves
POSITION_MULTIPLIERS = {
    "QB": 1.2,   # QBs valued higher due to scarcity
    "RB": 1.1,   # RBs have shorter careers
    "WR": 1.0,   # WR is baseline
    "TE": 0.9,   # TE slightly discounted
    "FLEX": 1.0,
    "Pick": 0.85  # Draft picks slightly discounted (uncertainty)
}

# Contract year multipliers (post-2024 rookie contract + option years)
CONTRACT_STAGES = {
    "rookie": 1.0,        # Years 1-3
    "extension": 1.15,    # After rookie, before tag
    "franchise_tag": 0.9, # Franchise tagged player
    "restricted": 1.0,    # RFA
    "veteran": 0.95       # Past prime years
}


def effective_value(raw_value: float) -> float:
    """
    Apply KTC-style nonlinear normalization.
    This compresses the value scale so that elite players
    maintain premium value while mid-tier values converge.
    """
    if raw_value <= 0:
        return 0
    raw_value = min(raw_value, KTC_MAX)
    return (raw_value / KTC_MAX) ** KTC_POWER * KTC_MAX


def raw_from_effective(effective: float) -> float:
    """Reverse the effective value calculation."""
    if effective <= 0:
        return 0
    effective = min(effective, KTC_MAX)
    return (effective / KTC_MAX) ** (1 / KTC_POWER) * KTC_MAX


def calculate_age_adjustment(
    player_age: Optional[float],
    position: str = "WR"
) -> float:
    """
    Calculate age-based value adjustment.
    
    Returns multiplier based on player age:
    - Age < 23: Slight premium (upside)
    - Age 23-26: Full value (prime)
    - Age 27-29: Slight decline
    - Age 30+: Significant decline
    """
    if player_age is None:
        return 1.0  # Unknown age, no adjustment
    
    if player_age < 23:
        # Young players - premium for upside
        return 1.0 + (23 - player_age) * 0.03
    elif player_age <= 26:
        # Prime years - full value
        return 1.0
    elif player_age <= 29:
        # Early decline
        decline = (player_age - 26) * DECLINE_RATE
        return max(0.7, 1.0 - decline)
    else:
        # Past prime - significant decline
        years_past = player_age - 26
        decline = years_past * 0.08
        return max(0.4, 1.0 - decline)


def calculate_stud_dominance_bonus(
    player_value: float,
    other_side_total: float,
    threshold: float = 0.35,
    multiplier: float = 0.25
) -> Tuple[float, str]:
    """
    Calculate KTC-style stud dominance bonus.
    
    When one player represents >35% of the other side's total value,
    they get a bonus to account for their elite status.
    
    Returns: (bonus_amount, description)
    """
    if other_side_total <= 0:
        return 0, "No bonus - empty other side"
    
    dominance = player_value / other_side_total
    
    if dominance > threshold:
        excess = player_value - (other_side_total * threshold)
        bonus = excess * multiplier
        return bonus, f"Stud bonus: {bonus:.0f} (dominance: {dominance:.0%})"
    
    return 0, ""


def calculate_stud_bonus_for_side(
    side_values: List[float],
    other_side_total: float,
    threshold: float = 0.35,
    multiplier: float = 0.25
) -> Tuple[float, str]:
    """
    Calculate stud bonus for the entire side (highest value player only).
    Returns bonus amount and description for the side's stud player.
    """
    if not side_values or other_side_total <= 0:
        return 0, ""
    
    max_value = max(side_values)
    return calculate_stud_dominance_bonus(max_value, other_side_total, threshold, multiplier)


def calculate_position_scarcity(
    position: str,
    format: str = "2qb",
    te_premium: bool = False
) -> float:
    """
    Calculate position scarcity multiplier.
    
    Superflex: QB more valuable
    TE Premium: TE more valuable in TE-premium formats
    """
    multiplier = POSITION_MULTIPLIERS.get(position, 1.0)
    
    if format == "Superflex" and position == "QB":
        multiplier *= 1.15
    
    if te_premium and position == "TE":
        multiplier *= 1.20
    
    return multiplier


# Draft pick round-based value multipliers (early picks more valuable)
PICK_ROUND_MULTIPLIERS = {
    1: 1.0,      # First round baseline
    2: 0.75,     # Second round
    3: 0.50,     # Third round
    4: 0.30,     # Fourth round
    5: 0.20,     # Fifth round and later
}

# Pick value by round from KTC historical data (approximate)
PICK_BASE_VALUES = {
    1: 3000,   # Early first
    2: 2200,   # Mid-late first
    3: 1400,   # Second round
    4: 800,    # Third round
    5: 400,    # Fourth round
}


def calculate_pick_value(
    pick_round: int,
    pick_number: int = 12,
    num_teams: int = 12,
    year_multiplier: float = 1.0
) -> float:
    """
    Calculate draft pick value with round-specific adjustments.
    
    Args:
        pick_round: Draft round (1-5+)
        pick_number: Pick number within the round (1-12+)
        num_teams: Number of teams in league (affects pick value)
        year_multiplier: Year adjustment (2026 picks worth less than 2025)
    """
    # Normalize round
    round_key = min(max(pick_round, 1), 5)
    round_mult = PICK_ROUND_MULTIPLIERS.get(round_key, 0.15)
    
    # Base value for this round
    base_val = PICK_BASE_VALUES.get(round_key, 200)
    
    # Within-round adjustment (earlier picks in round worth more)
    # Pick 1.01 vs 1.12 difference
    if pick_round == 1:
        # Early 1.01-1.03 get premium, rest taper
        if pick_number <= 3:
            within_round_mult = 1.0 + (4 - pick_number) * 0.05
        else:
            within_round_mult = 0.95 - (pick_number - 3) * 0.02
    else:
        within_round_mult = 0.9 - (pick_number - 1) * 0.03
    
    within_round_mult = max(0.6, min(1.15, within_round_mult))
    
    # Team count adjustment (more teams = slightly more value per pick)
    team_mult = 0.9 + (num_teams / 100)
    
    value = base_val * round_mult * within_round_mult * team_mult * year_multiplier
    return round(value, 1)


# Market trend adjustments (can be updated externally)
MARKET_TRENDS = {
    "rising": 1.10,    # Player value increasing
    "falling": 0.90,  # Player value decreasing  
    "stable": 1.0,
}

# Bye week collision penalty (if same position players share bye)
BYE_COLLISION_PENALTY = 0.05  # 5% penalty per colliding player


def calculate_market_adjustment(
    market_trend: str = "stable"
) -> float:
    """Get market trend multiplier."""
    return MARKET_TRENDS.get(market_trend, 1.0)


def calculate_roster_context_adjustment(
    current_starter_value: Optional[float],
    trade_away_player_value: float,
    position: str,
    bench_values: List[float] = None
) -> Tuple[float, str]:
    """
    Calculate adjustment based on roster context.
    
    If you're trading away a starter and don't have backup, penalty applies.
    If you're getting a starter at position of need, bonus applies.
    
    Returns: (adjustment_multiplier, description)
    """
    if current_starter_value is None:
        return 1.0, ""
    
    # Losing a starter at thin position
    if position in ["RB", "TE"]:
        # These positions have less depth
        if current_starter_value > trade_away_player_value * 0.8:
            penalty = 0.08
            return (1 - penalty), f"Starters at {position} position are thin - trading away hurts"
    
    # Getting a starter when you have need
    bench = bench_values or []
    if bench and trade_away_player_value > max(bench) * 1.5:
        bonus = 0.05
        return (1 + bonus), f"You need {position} help - this fills a gap"
    
    return 1.0, ""


def calculate_bye_week_collision(
    players_in_trade: List[str],
    your_roster_bye_weeks: Dict[str, int]
) -> float:
    """
    Calculate penalty if traded players have colliding bye weeks.
    Returns penalty multiplier (0.95 = 5% penalty).
    """
    if not your_roster_bye_weeks:
        return 1.0
    
    trade_bye_weeks = [your_roster_bye_weeks.get(p) for p in players_in_trade if p in your_roster_bye_weeks]
    if len(trade_bye_weeks) != len(set(trade_bye_weeks)):
        # Has collision
        return (1 - BYE_COLLISION_PENALTY)
    
    return 1.0


def project_player_value(
    current_value: float,
    age: Optional[float],
    position: str = "WR",
    years_ahead: int = 1
) -> float:
    """
    Project player value N years into the future.
    
    Accounts for age-related decline and career stage.
    Useful for evaluating multi-year asset value.
    """
    if current_value <= 0 or age is None:
        return current_value
    
    projected_value = current_value
    
    for year in range(1, years_ahead + 1):
        future_age = age + year
        
        # Calculate decline for this year
        if future_age < 23:
            projected_value *= 1.03
        elif future_age <= 26:
            projected_value *= 1.0
        elif future_age <= 29:
            projected_value *= (1.0 - DECLINE_RATE)
        elif future_age <= 32:
            projected_value *= 0.92
        else:
            projected_value *= 0.88
        
        # Position-specific adjustment
        if position == "RB" and future_age > 28:
            projected_value *= 0.95
        elif position == "QB" and future_age > 32:
            projected_value *= 0.97
    
    return round(projected_value, 1)


def find_comparable_trades(
    target_value: float,
    recent_trades: List[Dict],
    tolerance: float = 0.15
) -> List[Dict]:
    """
    Find historically similar trades from recent trade data.
    
    Args:
        target_value: The trade value to match
        recent_trades: List of dicts with 'give_value', 'get_value', 'result'
        tolerance: How close the match should be (15% default)
    
    Returns:
        List of comparable trades with match quality score
    """
    if not recent_trades:
        return []
    
    comparables = []
    
    for trade in recent_trades:
        trade_total = (trade.get("give_value", 0) + trade.get("get_value", 0)) / 2
        diff = abs(trade_total - target_value)
        
        if target_value > 0 and diff / target_value <= tolerance:
            match_quality = 1.0 - (diff / target_value)
            comparables.append({
                **trade,
                "match_quality": round(match_quality, 3),
                "value_diff": round(diff, 1)
            })
    
    comparables.sort(key=lambda x: x["match_quality"], reverse=True)
    return comparables[:5]


def calculate_positional_win_rate(
    position: str,
    format: str = "2qb"
) -> float:
    """
    Estimate historical win rate contribution by position.
    
    Based on championship rosters from dynasty leagues.
    """
    win_rates = {
        "QB": {"2qb": 0.85, "Superflex": 0.90, "1qb": 0.80},
        "RB": {"2qb": 0.75, "Superflex": 0.75, "1qb": 0.78},
        "WR": {"2qb": 0.80, "Superflex": 0.80, "1qb": 0.82},
        "TE": {"2qb": 0.70, "Superflex": 0.70, "1qb": 0.72},
    }
    
    return win_rates.get(position, {}).get(format, 0.75)


def validate_trade_inputs(
    give_players: List[Dict],
    get_players: List[Dict]
) -> Tuple[bool, List[str]]:
    """
    Validate trade inputs and return errors if any.
    """
    errors = []
    
    if not give_players:
        errors.append("Give side is empty")
    if not get_players:
        errors.append("Get side is empty")
    
    for i, player in enumerate(give_players):
        if "value" in player and player["value"] < 0:
            errors.append(f"Give player {player.get('name', i)} has negative value")
    
    for i, player in enumerate(get_players):
        if "value" in player and player["value"] < 0:
            errors.append(f"Get player {player.get('name', i)} has negative value")
    
    return len(errors) == 0, errors


def calculate_contract_value(
    years_remaining: int,
    contract_stage: str = "rookie"
) -> float:
    """
    Calculate contract-based value adjustment.
    
    More years of cheap production = higher value
    """
    base = CONTRACT_STAGES.get(contract_stage, 1.0)
    
    # Add value for each year of team control (scaled by control quality)
    year_bonus = 0.0
    if years_remaining >= 4:
        year_bonus = 0.12
    elif years_remaining >= 3:
        year_bonus = 0.08
    elif years_remaining >= 2:
        year_bonus = 0.04
    
    # Cap the total multiplier at reasonable levels
    return min(base + year_bonus, 1.35)


def calculate_trade_equity(
    give_values: List[float],
    get_values: List[float],
    include_stud_bonus: bool = True
) -> Dict:
    """
    Calculate comprehensive trade equity with all adjustments.
    
    This is the main trade calculation function.
    """
    give_total = sum(give_values)
    get_total = sum(get_values)
    
    if give_total == 0 or get_total == 0:
        return {
            "error": "Both sides must have value",
            "is_fair": False
        }
    
    # Base calculation
    raw_diff = get_total - give_total
    raw_margin = abs(raw_diff) / give_total
    
    # Apply stud bonus (only to the side with the elite player)
    stud_bonus = 0
    stud_description = ""
    stud_side = ""
    
    if include_stud_bonus and give_total > 0 and get_total > 0:
        give_bonus, give_desc = calculate_stud_bonus_for_side(give_values, get_total)
        get_bonus, get_desc = calculate_stud_bonus_for_side(get_values, give_total)
        
        # Apply bonus to whichever side's stud provides more value to the trade
        if give_bonus > get_bonus:
            stud_bonus = give_bonus
            stud_description = f"GIVE: {give_desc}"
            stud_side = "give"
            give_total += stud_bonus
        elif get_bonus > give_bonus:
            stud_bonus = get_bonus
            stud_description = f"GET: {get_desc}"
            stud_side = "get"
            get_total += stud_bonus
    
    # Recalculate with stud bonus
    adjusted_diff = get_total - give_total
    adjusted_margin = abs(adjusted_diff) / give_total if give_total > 0 else 1.0
    
    # Determine fairness
    is_fair = adjusted_margin <= 0.15
    
    if adjusted_margin <= 0.05:
        verdict = "EVEN"
    elif adjusted_diff > 0:
        verdict = "YOU_WIN"
    else:
        verdict = "THEY_WIN"
    
    # Calculate raw totals before stud bonus for reference
    give_raw = sum(give_values)
    get_raw = sum(get_values)
    
    return {
        "give_total_raw": round(give_raw, 1),
        "get_total_raw": round(get_raw, 1),
        "stud_bonus": round(stud_bonus, 1),
        "stud_description": stud_description,
        "give_total_adjusted": round(give_total, 1),
        "get_total_adjusted": round(get_total, 1),
        "difference": round(adjusted_diff, 1),
        "margin": round(adjusted_margin, 3),
        "is_fair": is_fair,
        "verdict": verdict,
        "recommendation": _get_recommendation(verdict, adjusted_margin)
    }


def _get_recommendation(verdict: str, margin: float) -> str:
    """Get text recommendation based on verdict."""
    if verdict == "YOU_WIN":
        if margin > 0.25:
            return "Strong accept - you're getting significant value"
        return "Accept - you're getting good value"
    elif verdict == "THEY_WIN":
        if margin > 0.25:
            return "Strong reject - you're significantly overpaying"
        return "Reject - you're overpaying"
    else:
        return "Fair trade - depends on positional needs"


def calculate_player_value(
    base_value: float,
    age: Optional[float] = None,
    position: str = "WR",
    format: str = "2qb",
    years_control: int = 3,
    contract_stage: str = "rookie",
    te_premium: bool = False,
    is_rookie: bool = False
) -> Dict:
    """
    Calculate complete player value with all adjustments.
    
    Returns detailed breakdown of value components.
    """
    # Special handling for draft picks
    if position == "Pick":
        pick_details = base_value  # base_value contains pick info dict
        if isinstance(pick_details, dict):
            pick_round = pick_details.get("round", 1)
            pick_number = pick_details.get("number", 12)
            num_teams = pick_details.get("teams", 12)
            year_mult = pick_details.get("year_mult", 0.95)
            return calculate_pick_value(pick_round, pick_number, num_teams, year_mult)
        return base_value
    
    # Apply position scarcity
    pos_multiplier = calculate_position_scarcity(position, format, te_premium)
    
    # Apply age adjustment (rookies get youth premium)
    if is_rookie and age is not None and age < 24:
        age_multiplier = calculate_age_adjustment(age, position) * 1.05
    else:
        age_multiplier = calculate_age_adjustment(age, position)
    
    # Apply contract adjustment
    contract_multiplier = calculate_contract_value(years_control, contract_stage)
    
    # Calculate final value
    raw_value = base_value * pos_multiplier * age_multiplier * contract_multiplier
    effective_val = effective_value(raw_value)
    
    return {
        "base_value": base_value,
        "position": position,
        "age": age,
        "is_rookie": is_rookie,
        "age_multiplier": round(age_multiplier, 3),
        "pos_multiplier": round(pos_multiplier, 3),
        "contract_multiplier": round(contract_multiplier, 3),
        "raw_value": round(raw_value, 1),
        "effective_value": round(effective_val, 1)
    }


def find_balance_picks(
    target_value: float,
    available_picks: List[Dict],
    max_picks: int = 3
) -> List[Dict]:
    """
    Find draft pick combinations that balance a trade.
    
    Uses a greedy algorithm to find pick combinations
    that approximate the target value.
    """
    if not available_picks:
        return []
    
    # Sort picks by value descending
    picks = sorted(available_picks, key=lambda x: x.get("value", 0), reverse=True)
    
    solutions = []
    
    # Try combinations of 1-3 picks
    for num_picks in range(1, min(max_picks + 1, len(picks) + 1)):
        for combo in _combinations(picks, num_picks):
            combo_value = sum(p.get("value", 0) for p in combo)
            diff = abs(target_value - combo_value)
            
            if diff < target_value * 0.15:  # Within 15%
                solutions.append({
                    "picks": [p.get("name", "Unknown") for p in combo],
                    "total_value": combo_value,
                    "difference": diff,
                    "match_quality": 1 - (diff / target_value)
                })
    
    # Sort by match quality
    solutions.sort(key=lambda x: x["match_quality"], reverse=True)
    return solutions[:5]


def _combinations(items: List, n: int) -> List[List]:
    """Generate n-length combinations."""
    if n == 0:
        return [[]]
    if not items:
        return []
    
    result = []
    for i, item in enumerate(items):
        for rest in _combinations(items[i+1:], n-1):
            result.append([item] + rest)
    return result


# ============================================================================
# Trade Calculator Class - Main Interface
# ============================================================================

class DynastyTradeCalculator:
    """
    Main trade calculator class.
    
    Usage:
        calc = DynastyTradeCalculator(format="Superflex", num_teams=10, te_premium=True)
        result = calc.evaluate_trade(
            give_players=[...],
            get_players=[...]
        )
    """
    
    def __init__(
        self,
        format: str = "2qb",
        num_teams: int = 12,
        fair_margin: float = 0.15,
        te_premium: bool = False
    ):
        self.format = format
        self.num_teams = num_teams
        self.fair_margin = fair_margin
        self.te_premium = te_premium
    
    def evaluate_trade(
        self,
        give_players: List[Dict],
        get_players: List[Dict],
        include_stud_bonus: bool = True,
        roster_context: Dict = None,
        market_trends: Dict = None
    ) -> Dict:
        """
        Evaluate a trade between two sides.
        
        Each player dict should have:
        - name: str
        - value: float (base KTC value)
        - position: str (optional)
        - age: float (optional)
        
        roster_context (optional):
        - your_starters: Dict[str, float] - current starters by position
        - your_bench: List[float] - bench player values
        - bye_weeks: Dict[str, int] - player name to bye week mapping
        
        market_trends (optional):
        - Dict of player_name -> "rising"|"falling"|"stable"
        """
        roster_context = roster_context or {}
        market_trends = market_trends or {}
        
        # Validate inputs
        is_valid, errors = validate_trade_inputs(give_players, get_players)
        if not is_valid:
            return {
                "error": "; ".join(errors),
                "is_fair": False,
                "verdict": "INVALID",
                "is_valid": False
            }
        
        give_values = []
        get_values = []
        give_details = []
        get_details = []
        
        for p in give_players:
            val = p.get("value", 0)
            if val > 0:
                adjusted = self._adjust_player_value(p)
                trend = market_trends.get(p.get("name", ""), "stable")
                trend_mult = calculate_market_adjustment(trend)
                adjusted *= trend_mult
                give_values.append(adjusted)
                give_details.append({
                    "name": p.get("name", "Unknown"),
                    "position": p.get("position", "WR"),
                    "adjusted_value": adjusted,
                    "trend": trend
                })
        
        for p in get_players:
            val = p.get("value", 0)
            if val > 0:
                adjusted = self._adjust_player_value(p)
                trend = market_trends.get(p.get("name", ""), "stable")
                trend_mult = calculate_market_adjustment(trend)
                adjusted *= trend_mult
                get_values.append(adjusted)
                get_details.append({
                    "name": p.get("name", "Unknown"),
                    "position": p.get("position", "WR"),
                    "adjusted_value": adjusted,
                    "trend": trend
                })
        
        # Check bye week collisions
        bye_weeks = roster_context.get("bye_weeks", {})
        if bye_weeks:
            give_names = [d["name"] for d in give_details]
            get_names = [d["name"] for d in get_details]
            give_bye_mult = calculate_bye_week_collision(give_names, bye_weeks)
            get_bye_mult = calculate_bye_week_collision(get_names, bye_weeks)
            
            # Apply bye penalties
            if give_bye_mult < 1.0:
                give_values = [v * give_bye_mult for v in give_values]
            if get_bye_mult < 1.0:
                get_values = [v * get_bye_mult for v in get_values]
        
        result = calculate_trade_equity(
            give_values, get_values, include_stud_bonus
        )
        
        # Add confidence interval
        ci, confidence = self.calculate_confidence_interval(give_values, get_values)
        result["confidence_interval"] = (round(ci[0], 1), round(ci[1], 1))
        result["confidence_level"] = round(confidence, 3)
        
        # Add trade grade
        result["trade_grade"] = self.calculate_trade_grade(
            result["margin"], result["is_fair"]
        )
        
        # Add scenario analysis
        scenarios = self.run_scenario_analysis(give_values, get_values)
        result["scenarios"] = [
            {"verdict": s.verdict, "margin": round(s.margin, 3), "probability": round(s.probability, 3)}
            for s in scenarios[:10]
        ]
        
        # Calculate scenario probabilities
        if scenarios:
            win_pct = sum(s.probability for s in scenarios if s.verdict == "YOU_WIN")
            lose_pct = sum(s.probability for s in scenarios if s.verdict == "THEY_WIN")
            even_pct = sum(s.probability for s in scenarios if s.verdict == "EVEN")
            result["scenario_probabilities"] = {
                "win": round(win_pct, 3),
                "lose": round(lose_pct, 3),
                "even": round(even_pct, 3)
            }
        
        # Add error margin
        result["error_margin_pct"] = round(result["margin"] * 0.15, 3)  # 15% error assumption
        
        # Add detailed breakdown
        result["give_details"] = give_details
        result["get_details"] = get_details
        result["market_notes"] = self._generate_market_notes(give_details, get_details)
        
        return result
    
    def _adjust_player_value(self, player: Dict) -> float:
        """Apply all value adjustments to a player."""
        base = player.get("value", 0)
        position = player.get("position", "WR")
        age = player.get("age")
        
        # Handle draft picks
        if position == "Pick":
            pick_info = player.get("pick_info", {})
            return calculate_pick_value(
                pick_round=pick_info.get("round", 1),
                pick_number=pick_info.get("number", self.num_teams // 2 + 1),
                num_teams=self.num_teams,
                year_multiplier=pick_info.get("year_mult", 0.95)
            )
        
        result = calculate_player_value(
            base_value=base,
            age=age,
            position=position,
            format=self.format,
            years_control=player.get("years_control", 3),
            contract_stage=player.get("contract_stage", "rookie"),
            te_premium=self.te_premium,
            is_rookie=player.get("is_rookie", False)
        )
        
        return result["effective_value"]
    
    def _generate_market_notes(
        self,
        give_details: List[Dict],
        get_details: List[Dict]
    ) -> List[str]:
        """Generate contextual notes about the trade."""
        notes = []
        
        for detail in give_details + get_details:
            trend = detail.get("trend", "stable")
            if trend == "rising":
                notes.append(f"{detail['name']} is rising in value")
            elif trend == "falling":
                notes.append(f"{detail['name']} is falling in value")
        
        return notes
    
    def calculate_confidence_interval(
        self,
        give_values: List[float],
        get_values: List[float]
    ) -> Tuple[Tuple[float, float], float]:
        """
        Calculate 80% confidence interval for trade values.
        
        Returns: ((low_get, high_get), confidence_level)
        """
        if not give_values or not get_values:
            return ((0, 0), 0.5)
        
        # Calculate weighted uncertainty based on player types
        give_uncertainty = self._calculate_combined_uncertainty(give_values)
        get_uncertainty = self._calculate_combined_uncertainty(get_values)
        
        give_std = sum(give_values) * give_uncertainty
        get_std = sum(get_values) * get_uncertainty
        
        # 80% CI = mean +/- 1.28 * std
        z_score = 1.28
        
        give_low = sum(give_values) - z_score * give_std
        give_high = sum(give_values) + z_score * give_std
        get_low = sum(get_values) - z_score * get_std
        get_high = sum(get_values) + z_score * get_std
        
        # Confidence that the trade is fair (intervals overlap)
        combined_low = max(give_low, get_low)
        combined_high = min(give_high, get_high)
        
        if combined_high >= combined_low:
            overlap = (combined_high - combined_low) / ((give_high - give_low + get_high - get_low) / 2)
            confidence = min(0.95, 0.5 + overlap * 0.3)
        else:
            gap = combined_low - combined_high
            max_gap = min(give_high - give_low, get_high - get_low)
            confidence = max(0.3, 0.5 - (gap / max_gap) * 0.3) if max_gap > 0 else 0.5
        
        return ((get_low, get_high), confidence)
    
    def _calculate_combined_uncertainty(self, values: List[float]) -> float:
        """Calculate combined uncertainty for a list of values."""
        if not values:
            return 0.15
        
        # Use average uncertainty weighted by value
        total_val = sum(values)
        if total_val == 0:
            return 0.25
        
        avg_uncertainty = 0.12  # Default for unknown player types
        
        # Higher value players tend to be more proven (less uncertain)
        max_val = max(values)
        if max_val > 8000:
            return VALUE_UNCERTAINTY["elite"]
        elif max_val > 4000:
            return VALUE_UNCERTAINTY["starter"]
        elif max_val > 2000:
            return VALUE_UNCERTAINTY["rotation"]
        else:
            return VALUE_UNCERTAINTY["rookie"]
    
    def calculate_trade_grade(self, margin: float, is_fair: bool) -> str:
        """Calculate letter grade for the trade."""
        if not is_fair:
            return "D" if margin < 0.25 else "F"
        
        abs_margin = abs(margin)
        if abs_margin <= 0.03:
            return "A+"
        elif abs_margin <= 0.07:
            return "A"
        elif abs_margin <= 0.10:
            return "B+"
        elif abs_margin <= 0.15:
            return "B"
        elif abs_margin <= 0.20:
            return "C"
        else:
            return "D"
    
    def run_scenario_analysis(
        self,
        give_values: List[float],
        get_values: List[float],
        num_scenarios: int = 100
    ) -> List[TradeScenario]:
        """
        Run Monte Carlo simulation for trade scenarios.
        
        Returns list of scenarios with different value assumptions.
        """
        scenarios = []
        
        for _ in range(num_scenarios):
            give_sc = [v * random.uniform(0.85, 1.15) for v in give_values]
            get_sc = [v * random.uniform(0.85, 1.15) for v in get_values]
            
            give_tot = sum(give_sc)
            get_tot = sum(get_sc)
            
            if give_tot == 0:
                continue
            
            diff = get_tot - give_tot
            margin = abs(diff) / give_tot
            
            if margin <= 0.05:
                verdict = "EVEN"
            elif diff > 0:
                verdict = "YOU_WIN"
            else:
                verdict = "THEY_WIN"
            
            scenarios.append(TradeScenario(
                give_total=give_tot,
                get_total=get_tot,
                verdict=verdict,
                difference=diff,
                margin=margin,
                probability=1.0 / num_scenarios
            ))
        
        # Sort by margin (fairest first)
        scenarios.sort(key=lambda x: x.margin)
        return scenarios


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    calc = DynastyTradeCalculator(format="2qb")
    
    # Example: Tet McMillan vs Jaylen Waddle + 2026 Late 1st
    give = [
        {"name": "Tet McMillan", "value": 6704, "position": "WR", "age": 22}
    ]
    
    get = [
        {"name": "Jaylen Waddle", "value": 4890, "position": "WR", "age": 25},
        {"name": "2026 1.10", "value": 2800, "position": "Pick"}
    ]
    
    result = calc.evaluate_trade(give, get)
    
    print("=" * 60)
    print("TRADE EVALUATION")
    print("=" * 60)
    print(f"\nGive: {give[0]['name']} ({give[0]['value']})")
    print(f"Get: {get[0]['name']} ({get[0]['value']}) + {get[1]['name']} ({get[1]['value']})")
    print(f"\nVerdict: {result['verdict']}")
    print(f"Difference: {result['difference']}")
    print(f"Fairness: {'Fair' if result['is_fair'] else 'Unfair'}")
    print(f"Recommendation: {result['recommendation']}")
    
    if result['stud_bonus'] > 0:
        print(f"\nStud Bonus: {result['stud_description']}")
