# Corrected Trade Engine Calculation for OpenClaw Bots
# Blends multiple sources, applies KTC-style nonlinear norm + stud adjustment

import numpy as np
import pandas as pd
from typing import Dict, List, Any

def ktc_total_value(p: float, top_value: float = 9999, team_value: float = 8200) -> float:
    """
    Returns BASE RAW + ADJUSTMENT (total trade value). Matches KTC stud-flattening behavior.
    
    Formula applies compression to the raw KTC scale:
    - Top players (near 9999) are compressed less (elite plateau)
    - Mid-tier players are compressed more
    - This creates the non-linear trade value curve
    
    Args:
        p: Raw KTC value
        top_value: Scale maximum (9999)
        team_value: Typical top team value threshold (8200)
    
    Returns:
        Total trade value (base + adjustment) on 0-9999+ scale
    """
    term1 = 0.15 * (p / top_value) ** 8  # Elite plateau
    term2 = 0.15 * (p / team_value) ** 1.3  # Mid scaling
    term3 = 0.1 * (p / (top_value + 2000)) ** 1.28  # Volume penalty
    adjustment = p * (0.1 + term1 + term2 + term3)
    return p + adjustment  # ✅ KEY FIX: total, not just premium


def calculate_blended_trade_value(player_id: str, sources: Dict[str, List[float]]) -> Dict[str, float]:
    """
    Blends sources, normalizes nonlinearly, applies stud boost.
    
    Sources should be a dict of source_name -> list of values.
    Multiple values per source are averaged.
    
    Args:
        player_id: Player name or ID
        sources: Dict like {"KTC": [8500], "DynastyProcess": [8200], ...}
    
    Returns:
        Dict with blended_raw, normalized, stud_factor, trade_value
    """
    # Blend base value (average across all sources, weighted equally)
    values = [val for src_vals in sources.values() for val in src_vals if val > 0]
    if not values:
        return {"error": "No valid source values"}
    
    blended_p = np.mean(values)
    
    # Nonlinear normalization
    normalized = ktc_total_value(blended_p)
    
    # Stud value adjustment (KTC-like premium for elites)
    percentile = np.clip(blended_p / 10000, 0, 1)  # Assume 10k max scale
    
    if percentile > 0.9:
        # Top 10%: 1.2x to 1.5x multiplier
        stud_factor = 1.0 + 0.5 * (percentile - 0.9) / 0.1
    elif percentile < 0.1:
        # Bottom 10%: 0.5x to 1.0x discount
        stud_factor = max(0.5, 1.0 - 0.5 * (0.1 - percentile) / 0.1)
    else:
        stud_factor = 1.0
    
    final_value = normalized * stud_factor
    
    return {
        "player_id": player_id,
        "blended_raw": round(blended_p, 1),
        "normalized": round(normalized, 1),
        "stud_factor": round(stud_factor, 3),
        "trade_value": round(final_value, 1)
    }


def evaluate_trade(
    side_a: List[Dict[str, Any]],
    side_b: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Evaluate a trade between two sides.
    
    Each side is a list of player dicts with 'name' and 'sources' keys.
    Example: [{"name": "Tet McMillan", "sources": {"KTC": [6704], "DynastyProcess": [6500]}}, ...]
    
    Returns trade analysis with winner, balance suggestions.
    """
    # Calculate trade value for each player on each side
    side_a_values = [calculate_blended_trade_value(p["name"], p["sources"]) for p in side_a]
    side_b_values = [calculate_blended_trade_value(p["name"], p["sources"]) for p in side_b]
    
    # Sum totals
    total_a = sum(p["trade_value"] for p in side_a_values)
    total_b = sum(p["trade_value"] for p in side_b_values)
    
    # Delta
    delta = total_b - total_a  # Positive = B winning
    
    # Determine winner
    if abs(delta) < 50:
        winner = "EVEN"
        balance_raw = 0
        balance_side = None
    elif delta > 0:
        winner = "B"
        balance_raw = delta
        balance_side = "A"  # Side A needs to add
    else:
        winner = "A"
        balance_raw = -delta
        balance_side = "B"
    
    return {
        "side_a_players": [p["player_id"] for p in side_a_values],
        "side_b_players": [p["player_id"] for p in side_b_values],
        "side_a_total": round(total_a, 1),
        "side_b_total": round(total_b, 1),
        "delta": round(delta, 1),
        "winner": winner,
        "balance_raw_needed": round(balance_raw, 1),
        "balance_side": balance_side
    }


# =============================================================================
# Integration with OpenClaw Trade Calculator
# =============================================================================
# 
# To integrate with the trade-calculator.html frontend:
#
# 1. Replace the /api/v2/consensus-values endpoint to call this engine
# 2. Return trade_value (0-9999 scale) for each player
# 3. Frontend applies: effectiveValue(trade_value) for display
#
# =============================================================================


# Example usage for OpenClaw integration
if __name__ == "__main__":
    # Example: Tet McMillan vs Jaylen Waddle + 2026 Late 1st
    example_side_a = [
        {
            "name": "Tet McMillan",
            "sources": {
                "KTC": [6704],
                "DynastyProcess": [6500],
                "DLF": [6800]
            }
        }
    ]
    
    example_side_b = [
        {
            "name": "Jaylen Waddle",
            "sources": {
                "KTC": [4890],
                "DynastyProcess": [4700],
                "DLF": [5100]
            }
        },
        {
            "name": "2026 Late 1st",
            "sources": {
                "KTC": [4000]
            }
        }
    ]
    
    result = evaluate_trade(example_side_a, example_side_b)
    
    print("=" * 60)
    print("TRADE EVALUATION")
    print("=" * 60)
    print(f"\nSide A: {result['side_a_players']}")
    print(f"  Total: {result['side_a_total']}")
    print(f"\nSide B: {result['side_b_players']}")
    print(f"  Total: {result['side_b_total']}")
    print(f"\nDelta: {result['delta']}")
    print(f"Winner: {result['winner']}")
    if result['balance_side']:
        print(f"Balance: Side {result['balance_side']} needs to add ~{result['balance_raw_needed']} raw value")
    
    # Show individual player breakdowns
    print("\n" + "=" * 60)
    print("PLAYER BREAKDOWNS")
    print("=" * 60)
    
    for player in example_side_a + example_side_b:
        calc = calculate_blended_trade_value(player["name"], player["sources"])
        print(f"\n{player['name']}:")
        print(f"  Blended raw: {calc['blended_raw']}")
        print(f"  Normalized:  {calc['normalized']}")
        print(f"  Stud factor: {calc['stud_factor']}")
        print(f"  Trade value: {calc['trade_value']}")
