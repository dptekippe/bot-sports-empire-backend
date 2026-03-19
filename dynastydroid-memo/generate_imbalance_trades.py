#!/usr/bin/env python3
"""
Generate obvious imbalance trades for MEMO storage.
These are trades where the outcome is clear and easily understood.
"""
import json
import uuid
from datetime import datetime

def create_trade(trade_id, team_a, team_b, reasoning, context_override=None):
    """Create a single-step obvious imbalance trade."""
    context = {
        "league_type": "dynasty",
        "scoring": "PPR",
        "team_a_context": {"mode": "contender"},
        "team_b_context": {"mode": "rebuild"}
    }
    if context_override:
        context.update(context_override)
    
    team_a_total = sum(a.get("ktc_value", 0) for a in team_a)
    team_b_total = sum(b.get("ktc_value", 0) for b in team_b)
    diff = team_a_total - team_b_total
    
    # Determine outcome based on value difference
    pct_diff = abs(diff) / max(team_a_total, team_b_total)
    if pct_diff < 0.1:
        outcome = "even"
    elif team_a_total > team_b_total:
        outcome = "team_a_wins"
    else:
        outcome = "team_b_wins"
    
    trade = {
        "trade_id": trade_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "context": context,
        "steps": [{
            "step": 1,
            "team_a_offers": team_a,
            "team_b_offers": team_b,
            "team_a_total_value": team_a_total,
            "team_b_total_value": team_b_total,
            "value_difference": diff,
            "outcome": outcome,
            "reasoning": reasoning
        }]
    }
    return trade

# TIER 0 QB vs ANYTHING
trades = []

# Josh Allen trades
trades.append(create_trade(
    "allen_vs_tua_2026",
    [{"player": "Josh Allen", "ktc_value": 15000, "position": "QB", "age": 29, "asset_type": "player"}],
    [{"player": "Tua Tagovailoa", "ktc_value": 6500, "position": "QB", "age": 27, "asset_type": "player"}],
    "Josh Allen is tier-0 QB. Elite rushing + passing. 5 consecutive top-3 PPG seasons. Tua is good but not elite."
))

trades.append(create_trade(
    "allen_vs_mahomes_2026",
    [{"player": "Josh Allen", "ktc_value": 15000, "position": "QB", "age": 29, "asset_type": "player"}],
    [{"player": "Patrick Mahomes", "ktc_value": 11000, "position": "QB", "age": 30, "asset_type": "player"}],
    "Both elite but Allen younger (29 vs 30), Allen better rusher, Mahomes recovering from ACL tear."
))

trades.append(create_trade(
    "allen_vs_herbert_2026",
    [{"player": "Josh Allen", "ktc_value": 15000, "position": "QB", "age": 29, "asset_type": "player"}],
    [{"player": "Justin Herbert", "ktc_value": 5500, "position": "QB", "age": 27, "asset_type": "player"}],
    "Allen tier-0, Herbert has struggled behind bad O-line. Allen 5x the value."
))

trades.append(create_trade(
    "allen_3picks_2026",
    [{"player": "Josh Allen", "ktc_value": 15000, "position": "QB", "age": 29, "asset_type": "player"}],
    [{"pick": "2026-1st-01", "ktc_value": 5000}, {"pick": "2026-1st-mid", "ktc_value": 4500}, {"pick": "2027-1st-01", "ktc_value": 4500}],
    "Allen reportedly traded for 4 1sts + 2nd in real league. This offer is 3 1sts - still a win for seller."
))

# Drake Maye vs mid QBs
trades.append(create_trade(
    "maye_vs_bridgewater_2026",
    [{"player": "Drake Maye", "ktc_value": 12000, "position": "QB", "age": 23, "asset_type": "player"}],
    [{"player": "Teddy Bridgewater", "ktc_value": 500, "position": "QB", "age": 33, "asset_type": "player"}],
    "Maye QB2 at 23 years old. Bridgewater backup-tier. No contest."
))

trades.append(create_trade(
    "maye_vs_darnold_2026",
    [{"player": "Drake Maye", "ktc_value": 12000, "position": "QB", "age": 23, "asset_type": "player"}],
    [{"player": "Sam Darnold", "ktc_value": 4500, "position": "QB", "age": 28, "asset_type": "player"}],
    "Maye young elite at 12K value. Darnold 28 and declining. Dynasty window different."
))

# ELITE WR vs MID WR
trades.append(create_trade(
    "chase_vs_mooney_2026",
    [{"player": "Ja'Marr Chase", "ktc_value": 11000, "position": "WR", "age": 25, "asset_type": "player"}],
    [{"player": "Velus Jones", "ktc_value": 2500, "position": "WR", "age": 28, "asset_type": "player"}],
    "Chase WR1 overall. Mooney mid-tier. Chase elite every-year asset."
))

trades.append(create_trade(
    "puka_vs_johnson_2026",
    [{"player": "Puka Nacua", "ktc_value": 9000, "position": "WR", "age": 24, "asset_type": "player"}],
    [{"player": "Marquise Brown", "ktc_value": 3000, "position": "WR", "age": 27, "asset_type": "player"}],
    "Puka WR3 overall at 24. Hollywood been in committee his whole career."
))

trades.append(create_trade(
    "ceeb_vs_drake_2026",
    [{"player": "CeeDee Lamb", "ktc_value": 8500, "position": "WR", "age": 26, "asset_type": "player"}],
    [{"player": "Jahan Dotson", "ktc_value": 2000, "position": "WR", "age": 25, "asset_type": "player"}],
    "Lamb elite alpha WR1. Dotson been disappointment. 4x value gap."
))

# YOUNG ELITE vs OLD DECLINING
trades.append(create_trade(
    "jefferson_vs_adams_2026",
    [{"player": "Justin Jefferson", "ktc_value": 9500, "position": "WR", "age": 26, "asset_type": "player"}],
    [{"player": "Davante Adams", "ktc_value": 5500, "position": "WR", "age": 33, "asset_type": "player"}],
    "Jefferson 26 in his prime. Adams 33 and declining. Prime vs past-prime."
))

trades.append(create_trade(
    "hill_vs_diggs_2026",
    [{"player": "Tyreek Hill", "ktc_value": 7500, "position": "WR", "age": 31, "asset_type": "player"}],
    [{"player": "Stefon Diggs", "ktc_value": 3500, "position": "WR", "age": 32, "asset_type": "player"}],
    "Hill still elite at 31. Diggs 32 and on the decline. Both Puka-aged WR but Hill clearly better."
))

trades.append(create_trade(
    "chase_vs_evans_2026",
    [{"player": "Ja'Marr Chase", "ktc_value": 11000, "position": "WR", "age": 25, "asset_type": "player"}],
    [{"player": "Mike Evans", "ktc_value": 4500, "position": "WR", "age": 32, "asset_type": "player"}],
    "Chase 25 WR1. Evans 32 declining. Long-term vs short-term."
))

# ELITE RB vs COMMITTEE RB
trades.append(create_trade(
    "bijan_vs_mixon_2026",
    [{"player": "Bijan Robinson", "ktc_value": 8500, "position": "RB", "age": 24, "asset_type": "player"}],
    [{"player": "Joe Mixon", "ktc_value": 3500, "position": "RB", "age": 29, "asset_type": "player"}],
    "Bijan young elite 24. Mixon 29 declining. Different dynasty windows."
))

trades.append(create_trade(
    "gibbs_vs_pacheco_2026",
    [{"player": "Jahmyr Gibbs", "ktc_value": 8000, "position": "RB", "age": 23, "asset_type": "player"}],
    [{"player": "Isiah Pacheco", "ktc_value": 2500, "position": "RB", "age": 26, "asset_type": "player"}],
    "Gibbs 23 years old dual-threat. Pacheco replacement-level after KC signed Walker."
))

trades.append(create_trade(
    "taylor_vs_ekeler_2026",
    [{"player": "Jonathan Taylor", "ktc_value": 6000, "position": "RB", "age": 26, "asset_type": "player"}],
    [{"player": "Austin Ekeler", "ktc_value": 1500, "position": "RB", "age": 29, "asset_type": "player"}],
    "Taylor still workhorse at 26. Ekeler past his best. 4x value."
))

# HIGH PICKS vs LOW PICKS
trades.append(create_trade(
    "top5_vs_late3rd_2026",
    [{"player": "2026-1st-01", "ktc_value": 5500, "position": "pick", "asset_type": "pick"}],
    [{"player": "2026-3rd-12", "ktc_value": 800, "position": "pick", "asset_type": "pick"}],
    "1.01 vs late 3rd. No contest. 7x value gap."
))

trades.append(create_trade(
    "mid1_vs_mid2_2026",
    [{"pick": "2026-1st-06", "ktc_value": 4500, "position": "pick", "asset_type": "pick"}],
    [{"pick": "2026-2nd-06", "ktc_value": 2500, "position": "pick", "asset_type": "pick"}],
    "Mid 1st vs mid 2nd. 1sts premium over 2nds clear in dynasty."
))

trades.append(create_trade(
    "two_firsts_vs_bijan_2026",
    [{"pick": "2026-1st-03", "ktc_value": 5000}, {"pick": "2027-1st-mid", "ktc_value": 4000}],
    [{"player": "Bijan Robinson", "ktc_value": 8500, "position": "RB", "age": 24, "asset_type": "player"}],
    "2 firsts (9K total) vs Bijan (8.5K). Close but Bijan better win-now asset."
))

# STALED ASSETS
trades.append(create_trade(
    "herbert_vs_minshew_2026",
    [{"player": "Justin Herbert", "ktc_value": 5500, "position": "QB", "age": 27, "asset_type": "player"}],
    [{"player": "Gardner Minshew", "ktc_value": 800, "position": "QB", "age": 28, "asset_type": "player"}],
    "Herbert still top-12 QB at 27. Minshew backup-tier. Elite vs stream."
))

trades.append(create_trade(
    "lawrence_vs_tannehill_2026",
    [{"player": "Trevor Lawrence", "ktc_value": 5000, "position": "QB", "age": 26, "asset_type": "player"}],
    [{"player": "Ryan Tannehill", "ktc_value": 500, "position": "QB", "age": 37, "asset_type": "player"}],
    "Lawrence 26 with career year. Tannehill 37 and done. No contest."
))

# ELITE TE vs BACKUP TE
trades.append(create_trade(
    "lachance_vs_ferguson_2026",
    [{"player": "Luke LaPorta", "ktc_value": 7500, "position": "TE", "age": 24, "asset_type": "player"}],
    [{"player": "Jake Ferguson", "ktc_value": 2500, "position": "TE", "age": 26, "asset_type": "player"}],
    "LaPorta elite TE at 24. Ferguson midTE1. 3x value gap."
))

# Save all trades
output_dir = "/Users/danieltekippe/.openclaw/workspace/dynastydroid-memo/trades"
for trade in trades:
    trade_id = trade["trade_id"]
    filepath = f"{output_dir}/{trade_id}.json"
    with open(filepath, 'w') as f:
        json.dump(trade, f, indent=2)
    print(f"Created: {filepath}")

print(f"\nTotal trades created: {len(trades)}")
