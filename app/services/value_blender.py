# app/services/value_blender.py
"""
Multi-source dynasty value blending
Blends: KTC + DynastyProcess + DLF + Sleeper Trades
"""

import httpx
import json
import os
import math
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# In-memory cache
_cache = {}
CACHE_TTL = 300  # 5 minutes


def rank_to_value(rank: float, scale: float = 999, decay: float = 30) -> float:
    """
    Convert FantasyPros ECR rank to trade value (0-999 scale)
    Uses exponential decay: value = scale * e^(-rank/decay)
    
    Examples: Rank 1→967, Rank 2.5→920, Rank 4.4→864
    """
    if rank <= 0:
        return 0
    return scale * math.exp(-rank / decay)


# TE Premium multiplier (derived from Draft Sharks data)
# TE-Premium vs No-TE: Bowers 1.6x, McBride 1.6x, Warren 1.8x
TE_PREMIUM_MULTIPLIER = 1.65

def apply_te_premium(value: float, position: str, te_premium: bool = False) -> float:
    """Apply TE premium multiplier to TE values"""
    if te_premium and position == "TE":
        return value * TE_PREMIUM_MULTIPLIER
    return value


def get_ktc_values(player_names: List[str]) -> Dict[str, float]:
    """Load KTC values from local JSON"""
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static", "ktc_values.json")
    try:
        with open(json_path, 'r') as f:
            players = json.load(f)
        values = {}
        for p in players:
            values[p['name']] = p['value']
        return {name: values.get(name, 0) for name in player_names}
    except Exception as e:
        print(f"KTC load error: {e}")
        return {name: 0 for name in player_names}


def get_dynastyprocess_values(player_names: List[str]) -> Dict[str, float]:
    """Load DynastyProcess values from local JSON"""
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static", "dynastyprocess_values.json")
    try:
        with open(json_path, 'r') as f:
            players = json.load(f)
        values = {}
        for p in players:
            values[p['name']] = p['value']
        return {name: values.get(name, 0) for name in player_names}
    except Exception as e:
        print(f"DynastyProcess load error: {e}")
        return {name: 0 for name in player_names}


def get_dlf_values(player_names: List[str]) -> Dict[str, float]:
    """DLF expert values - use DynastyProcess as proxy"""
    # DLF (DynastyLeagueFootball) values - use DP for now
    return get_dynastyprocess_values(player_names)


def get_sleeper_trade_values(player_names: List[str]) -> Dict[str, float]:
    """Sleeper trade data values - use KTC as proxy"""
    # Would scrape recent trades from Sleeper - use KTC for now
    return get_ktc_values(player_names)


def get_fantasypros_values(player_names: List[str]) -> Dict[str, float]:
    """FantasyPros ECR converted to trade values"""
    # Load FantasyPros ECR from local JSON
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static", "fantasypros_values.json")
    try:
        with open(json_path, 'r') as f:
            players = json.load(f)
        # Convert ECR rank to trade value
        values = {}
        for p in players:
            ecr_rank = p.get('ecr', p.get('rank', 999))
            values[p['name']] = rank_to_value(ecr_rank)
        return {name: values.get(name, 0) for name in player_names}
    except Exception as e:
        print(f"FantasyPros load error: {e}")
        return {name: 0 for name in player_names}


def get_draftsharks_values(player_names: List[str]) -> Dict[str, float]:
    """Draft Sharks dynasty values (0-999 scale)"""
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static", "draftsharks_values.json")
    try:
        with open(json_path, 'r') as f:
            players = json.load(f)
        values = {}
        for p in players:
            values[p['name']] = p.get('value', 0)
        return {name: values.get(name, 0) for name in player_names}
    except Exception as e:
        print(f"DraftSharks load error: {e}")
        return {name: 0 for name in player_names}


async def get_consensus_values(player_names: List[str], te_premium: bool = False) -> List[Dict]:
    """
    Blend multiple sources for consensus values
    
    Method:
    1. Min-max normalize each source to 0-100%
    2. Average the percentages (50/50 split)
    3. Multiply by 999 to get 0-999 range
    
    Weights:
    - KTC: 50% (crowdsourced)
    - DynastyProcess: 50% (data-driven)
    """
    results = []
    
    # Get all sources
    ktc = get_ktc_values(player_names)
    dp = get_dynastyprocess_values(player_names)
    
    # Load full KTC data for position info
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static", "ktc_values.json")
    ktc_players = []
    try:
        with open(json_path, 'r') as f:
            ktc_players = json.load(f)
    except Exception as e:
        print(f"KTC load error for positions: {e}")
    
    for name in player_names:
        ktc_val = ktc.get(name, 0)
        dp_val = dp.get(name, 0)
        
        # Get position from KTC
        pos = "WR"
        for p in ktc_players:
            if p['name'] == name:
                pos = p.get('pos', 'WR')
                break
        
        # Calculate raw weighted average (both sources now on 0-9999 scale)
        # DynastyProcess and KTC both use same scale, no percentage normalization needed
        raw_values = []
        raw_weights = []
        
        if ktc_val > 0:
            raw_values.append(ktc_val)
            raw_weights.append(0.50)
        if dp_val > 0:
            raw_values.append(dp_val)
            raw_weights.append(0.50)
        
        if raw_values and raw_weights:
            total_weight = sum(raw_weights)
            consensus = sum(v * w for v, w in zip(raw_values, raw_weights)) / total_weight
        else:
            consensus = 0
        
        # Apply TE premium if enabled
        if te_premium and pos == "TE":
            consensus = apply_te_premium(consensus, pos, True)
        
        # Determine sources used
        sources = sum(1 for v in [ktc_val, dp_val] if v > 0)
        
        results.append({
            "player_id": name,
            "name": name,
            "position": pos,
            "ktc": ktc_val,
            "dynastyprocess": dp_val,
            "consensus": round(consensus, 1),
            "sources_used": sources,
            "blend_weights": {"ktc": 0.50, "dynastyprocess": 0.50}
        })
    
    return results


# === STUD DOMINANCE BONUS (KTC-style) ===

def simple_stud_dominance_bonus(players: List[Dict], other_side_total: float) -> Dict:
    """
    Simple KTC-style stud bonus.
    Tuned so that:
    - 1.01 = 7456 vs 10673 on other side gives ~2.3k bonus (KTC-even case).
    """
    if not players:
        return {"bonus": 0, "stud_player": None, "dominance_ratio": 0, "threshold_crossed": False}
    
    max_player = max(players, key=lambda p: p.get('value', 0))
    max_value = max_player.get('value', 0)
    other_total = other_side_total if other_side_total > 0 else 1
    
    dominance_ratio = max_value / other_total
    
    # Tunable constants
    THRESHOLD = 0.38  # how big a share of the other side's total before bonus kicks in
    MULTIPLIER = 0.70  # how aggressively to reward excess over threshold
    
    if dominance_ratio > THRESHOLD:
        excess = max_value - other_total * THRESHOLD
        bonus = excess * MULTIPLIER
        adjusted_total = sum(p.get('value', 0) for p in players) + bonus
        return {
            "bonus": round(bonus),
            "stud_player": max_player.get('name', 'Unknown'),
            "dominance_ratio": round(dominance_ratio, 3),
            "threshold_crossed": True,
            "adjusted_total": round(adjusted_total),
            "message": f"{max_player.get('name', 'Unknown')} gets ${round(bonus):,} stud bonus (dominance {dominance_ratio:.0%}, threshold {THRESHOLD:.0%})"
        }
    else:
        return {
            "bonus": 0,
            "stud_player": None,
            "dominance_ratio": round(dominance_ratio, 3),
            "threshold_crossed": False,
            "message": "No stud dominance bonus applied"
        }


def apply_stud_adjustment(give_values: List[float], get_values: List[float], give_names: List[str] = None, get_names: List[str] = None) -> Dict:
    """
    Full trade stud adjustment - only ONE side gets bonus
    """
    give_total = sum(give_values)
    get_total = sum(get_values)
    
    # Find max player on each side
    give_max = max(give_values) if give_values else 0
    get_max = max(get_values) if get_values else 0
    
    # Only one side (the higher player) can get bonus
    if give_max > get_max:
        # Give side has higher player - only give gets bonus check
        give_players = [{"name": give_names[i] if give_names else f"Player{i+1}", "value": v} for i, v in enumerate(give_values)]
        give_bonus = simple_stud_dominance_bonus(give_players, get_total)
        adjusted_give = give_total + give_bonus['bonus']
        adjusted_get = get_total
        get_bonus = {"bonus": 0, "threshold_crossed": False}
    else:
        # Get side has higher player (or equal) - only get gets bonus check
        get_players = [{"name": get_names[i] if get_names else f"Player{i+1}", "value": v} for i, v in enumerate(get_values)]
        get_bonus = simple_stud_dominance_bonus(get_players, give_total)
        adjusted_get = get_total + get_bonus['bonus']
        adjusted_give = give_total
        give_bonus = {"bonus": 0, "threshold_crossed": False}
    
    net = adjusted_get - adjusted_give
    
    return {
        "raw_totals": {"give": give_total, "get": get_total},
        "give_bonus": give_bonus,
        "get_bonus": get_bonus,
        "adjusted_totals": {"give": adjusted_give, "get": adjusted_get},
        "net_adjustment": round(net),
        "winner": "get" if net > 0 else "give" if net < 0 else "even"
    }
