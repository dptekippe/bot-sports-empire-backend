# Fixed KTC Trade Engine for OpenClaw
# Pure Raw Adjustment + Trade Value Balance Calculation

import math
from typing import Dict, List, Tuple

KTC_MAX = 9999.0


def ktc_raw_adjust(p: float, t: float, v: float = KTC_MAX) -> float:
    """
    KTC raw adjustment formula.
    Compresses mid-tier players, amplifies studs via curve shape.
    
    Args:
        p: Player's KTC value
        t: Trade max (highest KTC value in this trade)
        v: Overall KTC scale max (9999)
    
    Returns:
        Raw adjusted value for trade comparison
    """
    return p * (0.1 + 0.15 * (p / v) ** 8 + 0.15 * (p / t) ** 1.3 + 0.1 * (p / (v + 2000)) ** 1.28)


def calculate_value_adjustment(target_eff: float) -> float:
    """
    Inverse of ktc_raw_adjust.
    Given a target effective value, find the raw KTC value needed.
    Uses binary search for numerical stability.
    """
    lo, hi = 0, KTC_MAX * 2
    for _ in range(100):
        mid = (lo + hi) / 2
        if ktc_raw_adjust(mid, KTC_MAX) < target_eff:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def evaluate_trade(side_a: List[float], side_b: List[float]) -> Dict:
    """
    Evaluate a trade using KTC mechanics.
    
    Base values stay fixed. Raw adjustment compresses for comparison.
    If one side is weaker, calculate the value adjustment needed to balance.
    
    Args:
        side_a: List of KTC values for Side A (e.g., [9999] for Bijan)
        side_b: List of KTC values for Side B (e.g., [6695, 4896, 3343] for Tet+Waddle+Early2nd)
    
    Returns:
        Trade evaluation with raw adjustments, gap, and value adjustment
    """
    # Trade max = highest individual value in this trade
    t = max(max(side_a, default=0), max(side_b, default=0))
    
    # Calculate raw adjustments for each side
    raw_adj_a = sum(ktc_raw_adjust(p, t) for p in side_a)
    raw_adj_b = sum(ktc_raw_adjust(p, t) for p in side_b)
    
    # Raw gap between sides
    raw_gap = raw_adj_a - raw_adj_b
    
    # Value adjustment needed to balance
    # This is what KTC shows as the "value adjustment" (e.g., +5646 for Bijan)
    # It represents the additional KTC value needed on the weaker side
    if raw_gap > 0:
        # Side B needs adjustment to balance
        value_adjustment = calculate_value_adjustment(raw_gap)
        balance_side = "B"
    elif raw_gap < 0:
        # Side A needs adjustment
        value_adjustment = calculate_value_adjustment(-raw_gap)
        balance_side = "A"
    else:
        value_adjustment = 0
        balance_side = None
    
    # Determine winner
    if abs(raw_gap) < 50:
        winner = "EVEN"
    elif raw_gap > 0:
        winner = "A"
    else:
        winner = "B"
    
    return {
        "side_a_values": side_a,
        "side_b_values": side_b,
        "trade_max": t,
        "side_a_raw_adj": round(raw_adj_a, 1),
        "side_b_raw_adj": round(raw_adj_b, 1),
        "raw_gap": round(raw_gap, 1),
        "winner": winner,
        "value_adjustment": round(value_adjustment, 1),
        "balance_side": balance_side
    }


def pretty_print(result: Dict) -> None:
    """Print trade evaluation in readable format."""
    print("=" * 60)
    print("KTC TRADE EVALUATION")
    print("=" * 60)
    print(f"\nSide A: {result['side_a_values']}")
    print(f"  Raw adj: {result['side_a_raw_adj']}")
    print(f"\nSide B: {result['side_b_values']}")
    print(f"  Raw adj: {result['side_b_raw_adj']}")
    print(f"\nTrade max (t): {result['trade_max']}")
    print(f"Raw gap: {result['raw_gap']}")
    print(f"Winner: {result['winner']}")
    if result['balance_side']:
        print(f"Value adjustment: +{result['value_adjustment']} to Side {result['balance_side']}")
    print("=" * 60)


# Test cases
if __name__ == "__main__":
    # Test 1: Bijan vs Tet + Waddle + Early 2nd
    # Daniel says: KTC shows +5646 value adjustment
    print("TEST 1: Bijan vs Tet + Waddle + Early 2nd")
    result1 = evaluate_trade([9999], [6695, 4896, 3343])
    pretty_print(result1)
    print()
    
    # Test 2: Tet vs Waddle + Late 1st
    # Daniel says: Should be close to even
    print("TEST 2: Tet vs Waddle + Late 1st")
    result2 = evaluate_trade([6695], [4896, 3343])
    pretty_print(result2)
    print()
    
    # Test 3: Josh Allen (9999) vs mid-tier players
    print("TEST 3: Josh Allen vs 4 mid-RBs")
    result3 = evaluate_trade([9999], [5000, 4500, 4000, 3500])
    pretty_print(result3)
