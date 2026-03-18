"""
Trade Calculation Test
KTC Normalization: eff(x) = (x/9999)^1.8085 * 9999
"""

KTC_MAX = 9999
KTC_POWER = 1.8085
STUD_THRESHOLD = 7000
GAP_MULTIPLIER = 2.5
BONUS_MULTIPLIER = 0.30

def effective_value(raw):
    if raw <= 0: return 0
    raw = min(raw, KTC_MAX)
    return (raw / KTC_MAX) ** KTC_POWER * KTC_MAX

def raw_from_effective(target):
    if target <= 0: return 0
    target = min(target, KTC_MAX)
    return (target / KTC_MAX) ** (1 / KTC_POWER) * KTC_MAX

# Test 1: Tet McMillan vs Jaylen Waddle + Late 1st
print("=" * 60)
print("TEST 1: Tet McMillan vs Jaylen Waddle + 2026 Late 1st")
print("=" * 60)

tet_ktc = 6704
waddle_ktc = 4890
late_1st_ktc = 4000  # 2026 Late 1st from our JSON
late_3rd_ktc = 2148   # 2026 Late 3rd from our JSON

tet_eff = effective_value(tet_ktc)
waddle_eff = effective_value(waddle_ktc)
late_1st_eff = effective_value(late_1st_ktc)
late_3rd_eff = effective_value(late_3rd_ktc)

print(f"\nKTC Values:")
print(f"  Tet (6704):       {tet_ktc}")
print(f"  Waddle (4890):   {waddle_ktc}")
print(f"  Late 1st (4000): {late_1st_ktc}")
print(f"  Late 3rd (2148): {late_3rd_ktc}")

print(f"\nEffective Values (power curve applied):")
print(f"  Tet:       {tet_eff:.1f}")
print(f"  Waddle:   {waddle_eff:.1f}")
print(f"  Late 1st: {late_1st_eff:.1f}")
print(f"  Late 3rd: {late_3rd_eff:.1f}")

print(f"\nTrade Analysis:")
print(f"  Waddle + Late 1st: {waddle_eff + late_1st_eff:.1f}")
print(f"  Delta from Tet: {tet_eff - (waddle_eff + late_1st_eff):.1f}")

print(f"\n  Waddle + Late 3rd: {waddle_eff + late_3rd_eff:.1f}")
print(f"  Delta from Tet: {tet_eff - (waddle_eff + late_3rd_eff):.1f}")

# Find what balances Tet - Waddle
gap = tet_eff - waddle_eff
needed_raw = raw_from_effective(gap)
print(f"\nTo balance Tet vs Waddle alone:")
print(f"  Gap in effective terms: {gap:.1f}")
print(f"  Required raw KTC value: {needed_raw:.0f}")

# Consensus-based calculation (if consensus is 0-999 scale)
print("\n" + "=" * 60)
print("TEST 2: Consensus-Based Calculation")
print("=" * 60)
print("\nIf consensus is on 0-999 scale, multiply by 10 for 0-9999:")
print(f"  Tet consensus 950 -> {effective_value(9500):.1f} effective")
print(f"  Waddle consensus 700 -> {effective_value(7000):.1f} effective")

