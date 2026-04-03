import sys
sys.path.insert(0, '/Users/danieltekippe/.openclaw/workspace')
import asyncio

async def test():
    # Import the fixed function
    from app.services.value_blender import get_consensus_values
    
    # Test with known players
    result = await get_consensus_values(["Ja'Marr Chase", "Bijan Robinson", "Tetairoa McMillan"])
    
    print("Test Results:")
    for r in result:
        ktc = r.get('ktc', 0)
        dp = r.get('dynastyprocess', 0)
        consensus = r.get('consensus', 0)
        # Calculate expected raw average
        expected = (ktc + dp) / 2 if ktc > 0 and dp > 0 else max(ktc, dp) if max(ktc, dp) > 0 else 0
        print(f"{r['name']}: KTC={ktc}, DP={dp}, Consensus={consensus}, Expected={expected:.1f}")
        
        # Check if consensus matches expected raw average (within 1 point tolerance)
        if abs(consensus - expected) > 1:
            print(f"  WARNING: Consensus mismatch!")
        else:
            print(f"  OK: Consensus matches expected raw average")

asyncio.run(test())
