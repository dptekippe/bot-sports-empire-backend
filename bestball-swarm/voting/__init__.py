"""
Voting package for bestball swarm consensus.
"""

from .pgvector_vote import PGVoteConsensus, VoteResult, vote, quick_vote

__all__ = ["PGVoteConsensus", "VoteResult", "vote", "quick_vote"]
