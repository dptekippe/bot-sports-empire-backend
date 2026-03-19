"""
PGVector Voting Mechanism for Bestball Swarm Consensus

Uses pgvector cosine similarity to reach consensus among 3 agents:
- Drafter: Generates draft picks
- Valuator: Evaluates player values
- Optimizer: Optimizes lineup/roster construction

Consensus is reached when any two picks have cosine similarity > 0.85.
"""

import os
import json
from typing import Optional
from dataclasses import dataclass
from enum import Enum

import asyncpg
import openai
from openai import AsyncOpenAI

# Connection pool for performance
_pool: Optional[asyncpg.Pool] = None

# Embedding dimensions for text-embedding-3-small
EMBEDDING_DIM = 1536

# Consensus threshold
COSINE_THRESHOLD = 0.85


class AgentRole(Enum):
    """Agent roles in the swarm."""
    DRAFTER = "Drafter"
    VALUATOR = "Valuator"
    OPTIMIZER = "Optimizer"


@dataclass
class VoteResult:
    """Result of a voting round."""
    consensus_reached: bool
    winning_pick: str
    confidence: float
    similarities: dict[tuple[str, str], float]
    fallback_used: bool = False


class PGVoteConsensus:
    """
    Consensus voting using pgvector cosine similarity.
    
    Takes picks from 3 agents (Drafter, Valuator, Optimizer),
    embeds them, and uses cosine similarity to determine consensus.
    """
    
    def __init__(self, db_url: str):
        """
        Initialize the voting consensus engine.
        
        Args:
            db_url: PostgreSQL connection URL with pgvector extension
        """
        self.db_url = db_url
        self._client: Optional[AsyncOpenAI] = None
        
    @property
    def client(self) -> AsyncOpenAI:
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=os.environ.get("OPENAI_API_KEY")
            )
        return self._client
    
    async def _get_pool(self) -> asyncpg.Pool:
        """Get or create the connection pool."""
        global _pool
        if _pool is None:
            _pool = await asyncpg.create_pool(
                self.db_url,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
        return _pool
    
    async def close(self):
        """Close the connection pool."""
        global _pool
        if _pool is not None:
            await _pool.close()
            _pool = None
    
    async def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for pick text using text-embedding-3-small.
        
        Args:
            text: The text to embed (e.g., "[Drafter] Pick Bijan Robinson...")
            
        Returns:
            List of 1536-dimensional embedding vectors
        """
        response = await self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            dimensions=EMBEDDING_DIM
        )
        return response.data[0].embedding
    
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Efficiently embed multiple texts in a single API call.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        response = await self.client.embeddings.create(
            model="text-embedding-3-small",
            input=texts,
            dimensions=EMBEDDING_DIM
        )
        # Sort by index to maintain order
        embeddings = [None] * len(texts)
        for item in response.data:
            embeddings[item.index] = item.embedding
        return embeddings
    
    def _format_pick(self, agent_role: str, pick: str) -> str:
        """
        Format a pick with agent role prefix.
        
        Args:
            agent_role: Role name (Drafter, Valuator, Optimizer)
            pick: The actual pick text
            
        Returns:
            Formatted string like "[Drafter] Pick Bijan Robinson..."
        """
        return f"[{agent_role}] {pick}"
    
    async def _store_embedding(
        self,
        pool: asyncpg.Pool,
        pick_text: str,
        embedding: list[float],
        outcome: Optional[str] = None
    ) -> None:
        """
        Store an embedding in the insight_embeddings table.
        
        Args:
            pool: Database connection pool
            pick_text: The original pick text
            embedding: The embedding vector
            outcome: Optional outcome result
        """
        async with pool.acquire() as conn:
            # Ensure extension exists
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            
            # Ensure table exists with proper schema
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS insight_embeddings (
                    id SERIAL PRIMARY KEY,
                    text TEXT NOT NULL,
                    embedding vector(1536) NOT NULL,
                    outcome TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Create index for similarity search
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_embedding_cosine 
                ON insight_embeddings 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)
            
            # Insert the embedding
            await conn.execute(
                """
                INSERT INTO insight_embeddings (text, embedding, outcome)
                VALUES ($1, $2, $3)
                """,
                pick_text,
                embedding,
                outcome
            )
    
    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            a: First embedding vector
            b: Second embedding vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = sum(x * x for x in a) ** 0.5
        magnitude_b = sum(y * y for y in b) ** 0.5
        
        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0
        
        return dot_product / (magnitude_a * magnitude_b)
    
    def vote(
        self,
        picks: list[str],
        agent_scores: Optional[dict[str, float]] = None
    ) -> VoteResult:
        """
        Synchronous vote wrapper - use vote_async for full functionality.
        
        Note: This is a convenience wrapper. For production use,
        prefer vote_async() which handles async embedding properly.
        """
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.vote_async(picks, agent_scores)
            )
            loop.close()
            return result
        
        return loop.run_until_complete(self.vote_async(picks, agent_scores))
    
    async def vote_async(
        self,
        picks: list[str],
        agent_scores: Optional[dict[str, float]] = None
    ) -> VoteResult:
        """
        Given list of picks from agents + agent confidence scores,
        return consensus pick using cosine similarity via pgvector.
        
        Args:
            picks: List of picks from 3 agents (order: Drafter, Valuator, Optimizer)
            agent_scores: Optional confidence scores for each agent (0.0-1.0)
            
        Returns:
            VoteResult with consensus decision
        """
        if len(picks) != 3:
            raise ValueError("Expected exactly 3 picks (Drafter, Valuator, Optimizer)")
        
        if agent_scores is None:
            agent_scores = {
                "Drafter": 0.8,
                "Valuator": 0.9,
                "Optimizer": 0.85
            }
        
        agent_names = ["Drafter", "Valuator", "Optimizer"]
        
        # Format picks with agent prefixes
        formatted_picks = [
            self._format_pick(agent_names[i], picks[i])
            for i in range(3)
        ]
        
        # Batch embed all picks for efficiency
        embeddings = await self.embed_batch(formatted_picks)
        
        # Calculate pairwise cosine similarities
        similarities: dict[tuple[str, str], float] = {}
        max_similarity = 0.0
        consensus_pair = None
        
        for i in range(3):
            for j in range(i + 1, 3):
                sim = self._cosine_similarity(embeddings[i], embeddings[j])
                similarities[(agent_names[i], agent_names[j])] = sim
                
                if sim > max_similarity:
                    max_similarity = sim
                    consensus_pair = (agent_names[i], agent_names[j])
        
        # Check for consensus (similarity > threshold)
        if max_similarity >= COSINE_THRESHOLD and consensus_pair:
            # Consensus reached - use weighted voting among the agreeing agents
            agreeing_indices = [
                agent_names.index(consensus_pair[0]),
                agent_names.index(consensus_pair[1])
            ]
            
            # Weight by agent scores
            weights = [
                agent_scores[agent_names[i]]
                for i in agreeing_indices
            ]
            total_weight = sum(weights)
            
            # Choose the higher-weighted agent's pick
            if weights[0] >= weights[1]:
                winner_idx = agreeing_indices[0]
            else:
                winner_idx = agreeing_indices[1]
            
            return VoteResult(
                consensus_reached=True,
                winning_pick=picks[winner_idx],
                confidence=max_similarity,
                similarities=similarities,
                fallback_used=False
            )
        
        # No consensus - use weighted voting
        weighted_scores: dict[int, float] = {0: 0.0, 1: 0.0, 2: 0.0}
        
        for i in range(3):
            for j in range(3):
                if i != j:
                    # Add similarity as weight contribution
                    key = tuple(sorted([agent_names[i], agent_names[j]]))
                    sim = similarities.get(key, 0.0)
                    weighted_scores[i] += sim * agent_scores[agent_names[j]]
        
        # Select the pick with highest weighted score
        winner_idx = max(weighted_scores, key=weighted_scores.get)
        
        return VoteResult(
            consensus_reached=False,
            winning_pick=picks[winner_idx],
            confidence=max_similarity,
            similarities=similarities,
            fallback_used=True
        )
    
    async def add_pick_to_memory(
        self,
        pick_text: str,
        outcome: Optional[str] = None,
        embedding: Optional[list[float]] = None
    ) -> None:
        """
        Store successful pick for future reference.
        
        Args:
            pick_text: The successful pick text
            outcome: Optional outcome (e.g., "won", "lost", "value_plus")
            embedding: Optional pre-computed embedding (will generate if not provided)
        """
        if embedding is None:
            embedding = await self.embed_text(pick_text)
        
        pool = await self._get_pool()
        await self._store_embedding(pool, pick_text, embedding, outcome)
    
    async def get_similar_picks(
        self,
        pick_text: str,
        limit: int = 5
    ) -> list[dict]:
        """
        Query similar historical picks from memory.
        
        Uses pgvector cosine similarity to find similar picks.
        
        Args:
            pick_text: The pick text to search for
            limit: Maximum number of results to return
            
        Returns:
            List of dicts with 'text', 'similarity', and 'outcome' keys
        """
        pool = await self._get_pool()
        
        # Generate embedding for the query
        embedding = await self.embed_text(pick_text)
        
        async with pool.acquire() as conn:
            # Ensure table exists
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS insight_embeddings (
                    id SERIAL PRIMARY KEY,
                    text TEXT NOT NULL,
                    embedding vector(1536) NOT NULL,
                    outcome TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Query for similar picks using pgvector
            results = await conn.fetch(
                """
                SELECT 
                    text,
                    outcome,
                    1 - (embedding <=> $1) as similarity
                FROM insight_embeddings
                ORDER BY embedding <=> $1
                LIMIT $2
                """,
                embedding,
                limit
            )
            
            return [
                {
                    "text": row["text"],
                    "outcome": row["outcome"],
                    "similarity": round(row["similarity"], 4)
                }
                for row in results
            ]
    
    async def get_pick_history(
        self,
        agent_role: Optional[str] = None,
        limit: int = 50
    ) -> list[dict]:
        """
        Get historical picks, optionally filtered by agent role.
        
        Args:
            agent_role: Optional role filter (Drafter, Valuator, Optimizer)
            limit: Maximum number of results
            
        Returns:
            List of historical picks with metadata
        """
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            if agent_role:
                results = await conn.fetch(
                    """
                    SELECT text, outcome, created_at
                    FROM insight_embeddings
                    WHERE text LIKE $1
                    ORDER BY created_at DESC
                    LIMIT $2
                    """,
                    f"[{agent_role}]%",
                    limit
                )
            else:
                results = await conn.fetch(
                    """
                    SELECT text, outcome, created_at
                    FROM insight_embeddings
                    ORDER BY created_at DESC
                    LIMIT $1
                    """,
                    limit
                )
            
            return [
                {
                    "text": row["text"],
                    "outcome": row["outcome"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None
                }
                for row in results
            ]


# Convenience function for quick voting
async def quick_vote(
    picks: list[str],
    db_url: str,
    agent_scores: Optional[dict[str, float]] = None
) -> VoteResult:
    """
    Quick voting without instantiating the class.
    
    Args:
        picks: List of 3 picks
        db_url: PostgreSQL connection URL
        agent_scores: Optional agent confidence scores
        
    Returns:
        VoteResult with consensus decision
    """
    voter = PGVoteConsensus(db_url)
    try:
        return await voter.vote_async(picks, agent_scores)
    finally:
        await voter.close()


# Sync wrapper for convenience
def vote(
    picks: list[str],
    db_url: str,
    agent_scores: Optional[dict[str, float]] = None
) -> VoteResult:
    """
    Synchronous quick voting.
    
    Args:
        picks: List of 3 picks
        db_url: PostgreSQL connection URL
        agent_scores: Optional agent confidence scores
        
    Returns:
        VoteResult with consensus decision
    """
    import asyncio
    
    try:
        loop = asyncio.get_running_loop()
        # Already in async context
        voter = PGVoteConsensus(db_url)
        try:
            return loop.run_until_complete(voter.vote_async(picks, agent_scores))
        finally:
            loop.run_until_complete(voter.close())
    except RuntimeError:
        # No running loop
        return asyncio.run(quick_vote(picks, db_url, agent_scores))
