"""
Example usage of the pgvector voting mechanism.

Usage:
    python example_usage.py
"""

import asyncio
import os

# Set your API keys
os.environ.setdefault("OPENAI_API_KEY", "your-api-key-here")

from voting.pgvector_vote import PGVoteConsensus


DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://dynastydroid_user:password@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid"
)


async def example_vote():
    """Demonstrate the voting mechanism."""
    
    voter = PGVoteConsensus(DB_URL)
    
    # Picks from 3 agents
    picks = [
        "Pick Bijan Robinson (RB, ADP 1.03) at pick 3",  # Drafter
        "Avoid aging RB, prefer younger WR like JSN",    # Valuator  
        "Stack CMC with Panthers DST for correlation"    # Optimizer
    ]
    
    # Agent confidence scores
    agent_scores = {
        "Drafter": 0.85,
        "Valuator": 0.90,
        "Optimizer": 0.80
    }
    
    print("=" * 60)
    print("PGVECTOR SWARM VOTING DEMO")
    print("=" * 60)
    print("\nPicks from agents:")
    for i, role in enumerate(["Drafter", "Valuator", "Optimizer"]):
        print(f"  [{role}] {picks[i]}")
    print()
    
    # Run vote
    result = await voter.vote_async(picks, agent_scores)
    
    print("VOTE RESULTS:")
    print(f"  Consensus reached: {result.consensus_reached}")
    print(f"  Winning pick: {result.winning_pick}")
    print(f"  Confidence: {result.confidence:.4f}")
    print(f"  Fallback used: {result.fallback_used}")
    print()
    
    print("Pairwise similarities:")
    for (a, b), sim in result.similarities.items():
        print(f"  {a} <-> {b}: {sim:.4f}")
    print()
    
    # Store successful pick in memory
    await voter.add_pick_to_memory(
        "[Drafter] Pick Bijan Robinson (RB, ADP 1.03) at pick 3",
        outcome="value_plus"
    )
    
    # Query similar picks
    print("Similar historical picks:")
    similar = await voter.get_similar_picks("Bijan Robinson draft pick", limit=3)
    for pick in similar:
        print(f"  [{pick['similarity']:.4f}] {pick['text']} -> {pick['outcome']}")
    
    await voter.close()
    return result


if __name__ == "__main__":
    asyncio.run(example_vote())
