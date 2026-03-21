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
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Constants
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
    
    return 0, "No stud bonus applied"


def calculate_position_scarcity(
    position: str,
    format: str = "2qb"
) -> float:
    """
    Calculate position scarcity multiplier.
    
    Superflex: QB more valuable
    TE Premium: TE more valuable
    """
    multiplier = POSITION_MULTIPLIERS.get(position, 1.0)
    
    if format == "Superflex" and position == "QB":
        multiplier *= 1.15
    
    return multiplier


def calculate_contract_value(
    years_remaining: int,
    contract_stage: str = "rookie"
) -> float:
    """
    Calculate contract-based value adjustment.
    
    More years of cheap production = higher value
    """
    base = CONTRACT_STAGES.get(contract_stage, 1.0)
    
    # Add value for each year of team control
    if years_remaining >= 3:
        return base * 1.1
    elif years_remaining >= 2:
        return base * 1.05
    else:
        return base


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
    
    if include_stud_bonus:
        give_max = max(give_values) if give_values else 0
        get_max = max(get_values) if get_values else 0
        
        if give_max > get_max:
            bonus, desc = calculate_stud_dominance_bonus(give_max, get_total)
            if bonus > 0:
                stud_bonus = bonus
                stud_description = desc
                get_total += bonus
        elif get_max > give_max:
            bonus, desc = calculate_stud_dominance_bonus(get_max, give_total)
            if bonus > 0:
                stud_bonus = bonus
                stud_description = desc
                give_total += bonus
    
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
    
    return {
        "give_total_raw": round(give_total - stud_bonus, 1),
        "get_total_raw": round(get_total - (stud_bonus if stud_bonus > 0 else 0), 1),
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
    contract_stage: str = "rookie"
) -> Dict:
    """
    Calculate complete player value with all adjustments.
    
    Returns detailed breakdown of value components.
    """
    # Apply position scarcity
    pos_multiplier = calculate_position_scarcity(position, format)
    
    # Apply age adjustment
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
        calc = DynastyTradeCalculator()
        result = calc.evaluate_trade(
            give_players=[...],
            get_players=[...]
        )
    """
    
    def __init__(
        self,
        format: str = "2qb",
        num_teams: int = 12,
        fair_margin: float = 0.15
    ):
        self.format = format
        self.num_teams = num_teams
        self.fair_margin = fair_margin
    
    def evaluate_trade(
        self,
        give_players: List[Dict],
        get_players: List[Dict],
        include_stud_bonus: bool = True
    ) -> Dict:
        """
        Evaluate a trade between two sides.
        
        Each player dict should have:
        - name: str
        - value: float (base KTC value)
        - position: str (optional)
        - age: float (optional)
        """
        give_values = []
        get_values = []
        
        for p in give_players:
            val = p.get("value", 0)
            if val > 0:
                # Apply adjustments
                adjusted = self._adjust_player_value(p)
                give_values.append(adjusted)
        
        for p in get_players:
            val = p.get("value", 0)
            if val > 0:
                adjusted = self._adjust_player_value(p)
                get_values.append(adjusted)
        
        return calculate_trade_equity(
            give_values, get_values, include_stud_bonus
        )
    
    def _adjust_player_value(self, player: Dict) -> float:
        """Apply all value adjustments to a player."""
        base = player.get("value", 0)
        position = player.get("position", "WR")
        age = player.get("age")
        
        result = calculate_player_value(
            base_value=base,
            age=age,
            position=position,
            format=self.format
        )
        
        return result["effective_value"]


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
