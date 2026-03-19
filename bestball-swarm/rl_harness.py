"""
RL Harness for Bestball Draft Simulation Swarm
===============================================
Multi-agent bestball draft simulator with 3 agent roles:
- Drafter (MiniMax-M2.5): ADP awareness, positional scarcity
- Valuator (DeepSeek): Projection variance, injury priors
- Optimizer (Gemini): Weekly lineup, tournament survival

Consensus via pgvector cosine similarity > 0.85.
"""

import asyncio
import argparse
import json
import os
import pickle
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional
import random

import numpy as np


# =============================================================================
# Configuration
# =============================================================================

class Config:
    """Global configuration for the RL harness."""
    DEFAULT_EPISODES = 1_000_000
    LARGE_SCALE_EPISODES = 10_000_000
    ROUNDS_PER_DRAFT = 17
    TEAMS_PER_DRAFT = 12
    CONSENSUS_THRESHOLD = 0.85
    PROGRESS_LOG_INTERVAL = 10_000
    SAVE_INTERVAL = 100_000
    PGVECTOR_HOST = os.getenv("PGVECTOR_HOST", "localhost")
    PGVECTOR_PORT = int(os.getenv("PGVECTOR_PORT", "5432"))
    PGVECTOR_DB = os.getenv("PGVECTOR_DB", "bestball")
    PGVECTOR_USER = os.getenv("PGVECTOR_USER", "postgres")
    PGVECTOR_PASSWORD = os.getenv("PGVECTOR_PASSWORD", "postgres")
    RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
    EMBEDDING_DIM = 1536  # Standard embedding dimension


# =============================================================================
# Data Models
# =============================================================================

class Position(Enum):
    QB = "QB"
    RB = "RB"
    WR = "WR"
    TE = "TE"
    FLEX = "FLEX"
    DST = "DST"
    K = "K"


@dataclass
class DraftResult:
    """Result of a complete draft episode."""
    episode_id: str
    timestamp: str
    duration_ms: float
    final_scores: dict[int, float]  # team_id -> total_points
    wins: dict[int, int]  # team_id -> weekly_wins
    draft_picks: list[dict]  # List of all picks made
    consensus_rate: float  # % of picks with high consensus
    strategy_patterns: dict[str, int]  # e.g., {"zero_rb": 1, "hero_rb": 0}

    def to_dict(self) -> dict:
        return asdict(self)


class Pick:
    """Represents a single draft pick."""
    def __init__(
        self,
        round_num: int,
        team_id: int,
        player_name: str,
        position: Position,
        adp: float,
        projection: float,
        agent_picks: dict[str, str],  # role -> player_name
        consensus_player: str,
        consensus_score: float,
    ):
        self.round_num = round_num
        self.team_id = team_id
        self.player_name = player_name
        self.position = position
        self.adp = adp
        self.projection = projection
        self.agent_picks = agent_picks
        self.consensus_player = consensus_player
        self.consensus_score = consensus_score

    def to_dict(self) -> dict:
        return {
            "round_num": self.round_num,
            "team_id": self.team_id,
            "player_name": self.player_name,
            "position": self.position.value,
            "adp": self.adp,
            "projection": self.projection,
            "agent_picks": self.agent_picks,
            "consensus_player": self.consensus_player,
            "consensus_score": float(self.consensus_score),
        }


class DraftState:
    """Current state of the draft."""
    def __init__(self):
        self.current_round = 1
        self.current_team = 1
        self.rosters: dict[int, list[Pick]] = {i: [] for i in range(1, 13)}
        self.available_players: list[dict] = []
        self.draft_order: list[int] = list(range(1, 13))
        self.picks_log: list[Pick] = []

    def next_pick(self) -> tuple[int, int]:
        """Returns (round, team) for next pick."""
        return self.current_round, self.current_team

    def advance(self):
        """Advance to next pick position."""
        self.current_team += 1
        if self.current_team > 12:
            self.current_team = 1
            self.current_round += 1

    def is_complete(self) -> bool:
        """Check if draft is complete."""
        return self.current_round > 17


# =============================================================================
# Player Pool (Mock - replace with real data in production)
# =============================================================================

def generate_player_pool() -> list[dict]:
    """Generate mock player pool. Replace with real ADP/projections."""
    positions = ["QB", "RB", "WR", "TE", "DST", "K"]
    players = []
    
    qb_names = ["Patrick Mahomes", "Josh Allen", "Lamar Jackson", "Jalen Hurts", 
                "Joe Burrow", "Tua Tagovailoa", "Justin Herbert", "Kirk Cousins",
                "Jordan Love", "Geno Smith", "Kyler Murray", "Deshaun Watson"]
    
    rb_names = ["Christian McCaffrey", "Bijan Robinson", "Saquon Barkley", "Derrick Henry",
                "Austin Ekeler", "Joe Mixon", "Jonathan Taylor", "Josh Jacobs",
                "Kenyan Drake", "Rashan Gary", "Jahmyr Gibbs", "Tony Pollard",
                "Dameon Pierce", "Brian Robinson", "James Cook", "Zach Charbonnet"]
    
    wr_names = ["Ja'Marr Chase", "CeeDee Lamb", "Tyreek Hill", "Amon-Ra St. Brown",
                "AJ Brown", "Stefon Diggs", "Davante Adams", "DeVonta Smith",
                "A.J. Dillon", "DK Metcalf", "Chris Olave", "Jaylen Waddle",
                "Jerry Jeudy", "Drake London", "Christian Watson", "Garrison Washburn",
                "Puka Nacua", "Keenan Allen", "Mike Evans", "Brandon Aiyuk"]
    
    te_names = ["Travis Kelce", "Mark Andrews", "George Kittle", "T.J. Hockenson",
                "Darren Waller", "Dallas Goedert", "Kyle Pitts", "David Njoku",
                "Jake Ferguson", "Evan Engram", "Pat Freiermuth", "Chigoziem Okonkwo"]
    
    dst_names = ["San Francisco 49ers", "Dallas Cowboys", "Buffalo Bills", 
                 "Philadelphia Eagles", "Kansas City Chiefs", "Miami Dolphins"]
    
    k_names = ["Harrison Butker", "Justin Tucker", "Daniel Carlson", 
               "Ka'imi Fairbairn", "Evan McPherson", "Tyler Bass"]
    
    adp_counter = 1
    for name in qb_names:
        players.append({
            "name": name,
            "position": "QB",
            "adp": adp_counter + 0.5,
            "projection": round(random.uniform(280, 420), 1),
            "variance": round(random.uniform(0.05, 0.20), 3),
            "injury_risk": round(random.uniform(0.0, 0.15), 3),
        })
        adp_counter += 1
    
    for name in rb_names:
        players.append({
            "name": name,
            "position": "RB",
            "adp": adp_counter + 0.5,
            "projection": round(random.uniform(180, 350), 1),
            "variance": round(random.uniform(0.10, 0.30), 3),
            "injury_risk": round(random.uniform(0.05, 0.20), 3),
        })
        adp_counter += 1
    
    for name in wr_names:
        players.append({
            "name": name,
            "position": "WR",
            "adp": adp_counter + 0.5,
            "projection": round(random.uniform(120, 280), 1),
            "variance": round(random.uniform(0.08, 0.25), 3),
            "injury_risk": round(random.uniform(0.03, 0.18), 3),
        })
        adp_counter += 1
    
    for name in te_names:
        players.append({
            "name": name,
            "position": "TE",
            "adp": adp_counter + 0.5,
            "projection": round(random.uniform(80, 200), 1),
            "variance": round(random.uniform(0.10, 0.25), 3),
            "injury_risk": round(random.uniform(0.02, 0.15), 3),
        })
        adp_counter += 1
    
    for name in dst_names:
        players.append({
            "name": name,
            "position": "DST",
            "adp": adp_counter + 0.5,
            "projection": round(random.uniform(80, 150), 1),
            "variance": round(random.uniform(0.15, 0.30), 3),
            "injury_risk": round(random.uniform(0.0, 0.10), 3),
        })
        adp_counter += 1
    
    for name in k_names:
        players.append({
            "name": name,
            "position": "K",
            "adp": adp_counter + 0.5,
            "projection": round(random.uniform(80, 140), 1),
            "variance": round(random.uniform(0.20, 0.35), 3),
            "injury_risk": round(random.uniform(0.0, 0.05), 3),
        })
        adp_counter += 1
    
    return players


# =============================================================================
# Agent System
# =============================================================================

class SwarmAgent:
    """Base class for swarm agents."""
    
    def __init__(self, role: str, model: str):
        self.role = role
        self.model = model
        self.pick_count = 0
        self.strategy_history: list[str] = []

    async def generate_pick(self, context: str) -> str:
        """
        Generate a pick recommendation based on context.
        In production, this would call the actual LLM API.
        """
        await asyncio.sleep(0.001)  # Simulate async API call
        
        # Parse context to extract available players
        # This is a mock - real implementation would parse the context string
        available = self._parse_available_from_context(context)
        
        if not available:
            return "SKIP"  # No valid picks
        
        # Role-specific pick logic
        if self.role == "drafter":
            # Prioritize ADP, positional scarcity
            return self._drafter_pick(available)
        elif self.role == "valuator":
            # Prioritize projection variance, injury priors
            return self._valuator_pick(available)
        elif self.role == "optimizer":
            # Prioritize weekly lineup balance, tournament survival
            return self._optimizer_pick(available)
        
        return random.choice(available)["name"]

    def _parse_available_from_context(self, context: str) -> list[dict]:
        """Parse available players from context string."""
        # Mock implementation - in production, parse from structured context
        pool = generate_player_pool()
        # Return top available by ADP
        return sorted(pool, key=lambda x: x["adp"])[:30]

    def _drafter_pick(self, available: list[dict]) -> str:
        """Drafter strategy: ADP awareness, positional scarcity."""
        # Mock: pick best available by ADP
        return available[0]["name"]

    def _valuator_pick(self, available: list[dict]) -> str:
        """Valuator strategy: projection variance, injury priors."""
        # Mock: pick highest projected with variance discount
        scored = []
        for p in available:
            risk_adjusted = p["projection"] * (1 - p["injury_risk"]) * (1 - p["variance"])
            scored.append((p["name"], risk_adjusted))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]

    def _optimizer_pick(self, available: list[dict]) -> str:
        """Optimizer strategy: weekly lineup balance, tournament survival."""
        # Mock: pick best projected
        scored = [(p["name"], p["projection"]) for p in available]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]

    def generate_context(self, draft_state: DraftState, team_id: int) -> str:
        """Generate rich context for the agent."""
        roster = draft_state.rosters[team_id]
        available = [p for p in generate_player_pool() 
                     if p["name"] not in [pick.player_name for pick in draft_state.picks_log]]
        
        # Count positions drafted
        pos_counts = {"QB": 0, "RB": 0, "WR": 0, "TE": 0, "DST": 0, "K": 0}
        for pick in roster:
            pos_counts[pick.position.value] += 1
        
        context = f"""
Round {draft_state.current_round}, Team {team_id}
Your roster: {', '.join([f'{p.position.value}:{p.player_name}' for p in roster])}
Position counts: QB:{pos_counts['QB']} RB:{pos_counts['RB']} WR:{pos_counts['WR']} TE:{pos_counts['TE']}
Top available players by ADP:
{chr(10).join([f'  {i+1}. {p["name"]} ({p["position"]}) - ADP:{p["adp"]} Proj:{p["projection"]}' for i, p in enumerate(available[:15])])}
"""
        return context


# =============================================================================
# Embedding System (Mock - use real embeddings in production)
# =============================================================================

class EmbeddingGenerator:
    """Generate embeddings for picks. Mock implementation."""
    
    def __init__(self, dim: int = Config.EMBEDDING_DIM):
        self.dim = dim
        self.cache: dict[str, np.ndarray] = {}
    
    def generate(self, text: str) -> np.ndarray:
        """Generate embedding for text."""
        # Cache lookup
        if text in self.cache:
            return self.cache[text]
        
        # Mock embedding - deterministic based on text hash
        np.random.seed(hash(text) % (2**32))
        embedding = np.random.randn(self.dim).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)  # Normalize
        
        self.cache[text] = embedding
        return embedding
    
    async def generate_async(self, text: str) -> np.ndarray:
        """Async wrapper for embedding generation."""
        return self.generate(text)


# =============================================================================
# pgvector Consensus System
# =============================================================================

class PGVoteConsensus:
    """
    Consensus system using pgvector cosine similarity.
    In production, this connects to actual pgvector database.
    """
    
    def __init__(self, embedding_generator: EmbeddingGenerator):
        self.embedding_generator = embedding_generator
        self.memory: list[tuple[str, np.ndarray]] = []  # (pick, embedding)
        self.connection = None
        self._connected = False
    
    async def connect(self):
        """Connect to pgvector database."""
        try:
            import asyncpg
            self.connection = await asyncpg.connect(
                host=Config.PGVECTOR_HOST,
                port=Config.PGVECTOR_PORT,
                database=Config.PGVECTOR_DB,
                user=Config.PGVECTOR_USER,
                password=Config.PGVECTOR_PASSWORD,
            )
            await self._init_schema()
            self._connected = True
            print(f"Connected to pgvector at {Config.PGVECTOR_HOST}:{Config.PGVECTOR_PORT}")
        except ImportError:
            print("asyncpg not installed, using mock consensus")
            self._connected = False
        except Exception as e:
            print(f"Could not connect to pgvector: {e}, using mock consensus")
            self._connected = False
    
    async def _init_schema(self):
        """Initialize pgvector schema."""
        if not self._connected:
            return
        
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS pick_embeddings (
                id SERIAL PRIMARY KEY,
                pick_text TEXT NOT NULL,
                embedding vector(%s) NOT NULL,
                episode_id TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """, (Config.EMBEDDING_DIM,))
        
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS pick_embedding_idx 
            ON pick_embeddings USING ivfflat (embedding vector_cosine_ops)
        """)

    async def add_to_memory(self, pick: str, embedding: np.ndarray, episode_id: str = None):
        """Add a pick and its embedding to memory."""
        self.memory.append((pick, embedding))
        
        if self._connected:
            try:
                await self.connection.execute(
                    "INSERT INTO pick_embeddings (pick_text, embedding, episode_id) VALUES ($1, $2, $3)",
                    pick, embedding.tolist(), episode_id
                )
            except Exception as e:
                print(f"Error storing embedding: {e}")

    async def vote(self, picks: list[str]) -> tuple[str, float]:
        """
        Vote on picks using cosine similarity consensus.
        Returns (consensus_pick, consensus_score).
        
        If similarity > threshold with memory, use that.
        Otherwise, return most common/first pick.
        """
        if not picks:
            return "SKIP", 0.0
        
        if len(picks) == 1:
            return picks[0], 1.0
        
        # Generate embeddings for all picks
        embeddings = [self.embedding_generator.generate(p) for p in picks]
        
        # Check similarity with memory
        best_match = None
        best_similarity = 0.0
        
        for i, (pick, emb) in enumerate(zip(picks, embeddings)):
            for mem_pick, mem_emb in self.memory[-100:]:  # Check recent memory
                similarity = np.dot(emb, mem_emb)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = pick
        
        # Calculate pairwise similarity among current picks
        if len(picks) > 1:
            similarities = []
            for i in range(len(embeddings)):
                for j in range(i + 1, len(embeddings)):
                    sim = np.dot(embeddings[i], embeddings[j])
                    similarities.append(sim)
            avg_similarity = np.mean(similarities) if similarities else 0.0
        else:
            avg_similarity = 1.0
        
        # Use best match if above threshold, else pick highest ranked
        if best_similarity >= Config.CONSENSUS_THRESHOLD:
            consensus_pick = best_match
            consensus_score = best_similarity
        else:
            # Pick most similar to others (lowest avg distance to centroid)
            centroid = np.mean(embeddings, axis=0)
            centroid_distances = [np.dot(e, centroid) for e in embeddings]
            best_idx = np.argmax(centroid_distances)
            consensus_pick = picks[best_idx]
            consensus_score = avg_similarity
        
        # Store winning pick in memory
        winning_emb = self.embedding_generator.generate(consensus_pick)
        await self.add_to_memory(consensus_pick, winning_emb)
        
        return consensus_pick, consensus_score

    async def close(self):
        """Close database connection."""
        if self.connection:
            await self.connection.close()


# =============================================================================
# Draft Simulator
# =============================================================================

class DraftSimulator:
    """Simulates a single bestball draft episode."""
    
    def __init__(self, agents: list[SwarmAgent], consensus: PGVoteConsensus):
        self.agents = agents
        self.consensus = consensus
        self.embedding_generator = EmbeddingGenerator()
        self.player_pool = generate_player_pool()
    
    def generate_pick_context(self, draft_state: DraftState, team_id: int) -> str:
        """Generate context for a pick."""
        # Find the agent that should pick for this team
        agent = self.agents[0]  # Use first agent for context generation
        return agent.generate_context(draft_state, team_id)
    
    async def run_episode(self, episode_id: str) -> DraftResult:
        """Run a complete draft episode."""
        start_time = time.time()
        
        draft_state = DraftState()
        strategy_patterns = {"zero_rb": 0, "hero_rb": 0, "zero_te": 0, "late_qb": 0}
        
        consensus_hits = 0
        total_picks = 0
        
        while not draft_state.is_complete():
            round_num, team_id = draft_state.next_pick()
            
            # Generate context for all agents
            context = self.generate_pick_context(draft_state, team_id)
            
            # Spawn 3 agents concurrently to generate picks
            agent_picks: dict[str, str] = {}
            tasks = []
            
            for agent in self.agents:
                task = asyncio.create_task(
                    self._agent_pick(agent, context, draft_state)
                )
                tasks.append((agent.role, task))
            
            # Collect picks
            for role, task in tasks:
                pick = await task
                agent_picks[role] = pick
            
            # Vote on consensus
            picks_list = list(agent_picks.values())
            consensus_pick, consensus_score = await self.consensus.vote(picks_list)
            
            # Record consensus rate
            if consensus_score >= Config.CONSENSUS_THRESHOLD:
                consensus_hits += 1
            total_picks += 1
            
            # Find player in pool
            player = next(
                (p for p in self.player_pool if p["name"] == consensus_pick),
                None
            )
            
            if player:
                # Create pick record
                pick_record = Pick(
                    round_num=round_num,
                    team_id=team_id,
                    player_name=player["name"],
                    position=Position(player["position"]),
                    adp=player["adp"],
                    projection=player["projection"],
                    agent_picks=agent_picks,
                    consensus_player=consensus_pick,
                    consensus_score=consensus_score,
                )
                
                draft_state.rosters[team_id].append(pick_record)
                draft_state.picks_log.append(pick_record)
                
                # Track strategy patterns
                self._track_strategy(draft_state, team_id, strategy_patterns)
            
            # Advance to next pick
            draft_state.advance()
        
        # Calculate final scores (mock - use real scoring in production)
        final_scores = self._calculate_scores(draft_state)
        
        duration_ms = (time.time() - start_time) * 1000
        
        return DraftResult(
            episode_id=episode_id,
            timestamp=datetime.now().isoformat(),
            duration_ms=duration_ms,
            final_scores=final_scores,
            wins=self._calculate_wins(final_scores),
            draft_picks=[p.to_dict() for p in draft_state.picks_log],
            consensus_rate=consensus_hits / total_picks if total_picks > 0 else 0.0,
            strategy_patterns=strategy_patterns,
        )
    
    async def _agent_pick(
        self, 
        agent: SwarmAgent, 
        context: str, 
        draft_state: DraftState
    ) -> str:
        """Get a single agent's pick."""
        pick = await agent.generate_pick(context)
        
        # Validate pick exists in pool
        valid_picks = [p["name"] for p in self.player_pool 
                       if p["name"] not in [x.player_name for x in draft_state.picks_log]]
        
        if pick not in valid_picks:
            # Fallback to highest ADP available
            pick = valid_picks[0] if valid_picks else "SKIP"
        
        return pick
    
    def _track_strategy(
        self, 
        draft_state: DraftState, 
        team_id: int, 
        patterns: dict[str, int]
    ):
        """Track draft strategy patterns."""
        roster = draft_state.rosters[team_id]
        
        # Zero RB: 0 RBs in first 5 rounds
        if len(roster) == 5:
            rb_count = sum(1 for p in roster if p.position == Position.RB)
            if rb_count == 0:
                patterns["zero_rb"] += 1
        
        # Hero RB: RB in round 1, no RB in rounds 2-4
        if len(roster) == 5:
            has_round1_rb = roster[0].position == Position.RB
            mid_rbs = sum(1 for p in roster[1:5] if p.position == Position.RB)
            if has_round1_rb and mid_rbs == 0:
                patterns["hero_rb"] += 1
        
        # Zero TE: 0 TEs in first 8 rounds
        if len(roster) == 8:
            te_count = sum(1 for p in roster if p.position == Position.TE)
            if te_count == 0:
                patterns["zero_te"] += 1
        
        # Late QB: QB drafted in round 8 or later
        for i, pick in enumerate(roster):
            if pick.position == Position.QB and i >= 8:
                patterns["late_qb"] += 1
                break
    
    def _calculate_scores(self, draft_state: DraftState) -> dict[int, float]:
        """Calculate total projected points for each team."""
        scores = {}
        for team_id, roster in draft_state.rosters.items():
            total = sum(p.projection for p in roster)
            scores[team_id] = round(total, 1)
        return scores
    
    def _calculate_wins(self, scores: dict[int, float]) -> dict[int, int]:
        """Calculate weekly wins (mock - 17 weeks, best score wins each week)."""
        wins = {team_id: 0 for team_id in scores}
        
        # Mock weekly results
        for week in range(17):
            # Add some variance to simulate weekly scores
            weekly_scores = {
                team_id: score + random.gauss(0, score * 0.1)
                for team_id, score in scores.items()
            }
            winner = max(weekly_scores, key=weekly_scores.get)
            wins[winner] += 1
        
        return wins


# =============================================================================
# Results Persistence
# =============================================================================

def save_results(results: list[DraftResult], filepath: str):
    """Save results to file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, "w") as f:
        json.dump([r.to_dict() for r in results], f, indent=2)
    
    print(f"Saved {len(results)} results to {filepath}")


def load_results(filepath: str) -> list[DraftResult]:
    """Load results from file."""
    with open(filepath, "r") as f:
        data = json.load(f)
    
    return [
        DraftResult(
            episode_id=d["episode_id"],
            timestamp=d["timestamp"],
            duration_ms=d["duration_ms"],
            final_scores=d["final_scores"],
            wins=d["wins"],
            draft_picks=d["draft_picks"],
            consensus_rate=d["consensus_rate"],
            strategy_patterns=d["strategy_patterns"],
        )
        for d in data
    ]


# =============================================================================
# Main Simulation Loop
# =============================================================================

async def run_episode(
    simulator: DraftSimulator,
    episode_id: str
) -> DraftResult:
    """Run a single episode."""
    return await simulator.run_episode(episode_id)


async def run_batch(
    simulator: DraftSimulator,
    start_episode: int,
    batch_size: int,
) -> list[DraftResult]:
    """Run a batch of episodes concurrently."""
    tasks = []
    for i in range(batch_size):
        episode_id = f"ep_{start_episode + i:08d}"
        task = asyncio.create_task(simulator.run_episode(episode_id))
        tasks.append(task)
    
    return await asyncio.gather(*tasks)


async def main(episodes: int = None, batch_size: int = 10):
    """Main entry point for the RL harness."""
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Bestball Draft RL Harness")
    parser.add_argument(
        "--episodes", "-n",
        type=int,
        default=Config.DEFAULT_EPISODES,
        help=f"Number of episodes to run (default: {Config.DEFAULT_EPISODES:,})"
    )
    parser.add_argument(
        "--large", "-l",
        action="store_true",
        help=f"Run large scale: {Config.LARGE_SCALE_EPISODES:,} episodes"
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=10,
        help="Batch size for concurrent episodes (default: 10)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output file path"
    )
    
    args = parser.parse_args()
    
    # Determine episode count
    if args.large:
        episodes = Config.LARGE_SCALE_EPISODES
    else:
        episodes = args.episodes or Config.DEFAULT_EPISODES
    
    batch_size = args.batch_size
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           BESTBALL DRAFT SIMULATION SWARM - RL HARNESS        ║
╠══════════════════════════════════════════════════════════════╣
║  Episodes:     {episodes:>15,}                              ║
║  Batch Size:   {batch_size:>15}                              ║
║  Rounds/Team:  {Config.ROUNDS_PER_DRAFT:>15}                              ║
║  Teams/Draft:  {Config.TEAMS_PER_DRAFT:>15}                              ║
║  Consensus:    {Config.CONSENSUS_THRESHOLD:>15.2f} cosine similarity            ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    # Initialize systems
    embedding_generator = EmbeddingGenerator()
    consensus = PGVoteConsensus(embedding_generator)
    await consensus.connect()
    
    agents = [
        SwarmAgent("drafter", "minimax-m2.5"),
        SwarmAgent("valuator", "deepseek"),
        SwarmAgent("optimizer", "gemini"),
    ]
    
    simulator = DraftSimulator(agents, consensus)
    
    # Results storage
    all_results: list[DraftResult] = []
    start_time = time.time()
    
    # Output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = args.output or os.path.join(
        Config.RESULTS_DIR, 
        f"results_{timestamp}.json"
    )
    
    # Main simulation loop
    episode = 0
    while episode < episodes:
        # Calculate batch size (don't overshoot)
        remaining = episodes - episode
        current_batch = min(batch_size, remaining)
        
        # Run batch
        batch_start = time.time()
        batch_results = await run_batch(simulator, episode, current_batch)
        batch_time = time.time() - batch_start
        
        all_results.extend(batch_results)
        episode += current_batch
        
        # Progress logging
        if episode % Config.PROGRESS_LOG_INTERVAL == 0 or episode >= episodes:
            elapsed = time.time() - start_time
            rate = episode / elapsed if elapsed > 0 else 0
            eta = (remaining / rate) if rate > 0 else 0
            
            # Aggregate stats
            avg_consensus = np.mean([r.consensus_rate for r in batch_results])
            avg_duration = np.mean([r.duration_ms for r in batch_results])
            
            print(
                f"[{episode:>10,}/{episodes:,}] "
                f"Rate: {rate:>8.1f} ep/s | "
                f"Consensus: {avg_consensus:.2%} | "
                f"Pick Time: {avg_duration:.1f}ms | "
                f"ETA: {eta/60:>6.1f} min"
            )
        
        # Periodic saves
        if episode % Config.SAVE_INTERVAL == 0 and episode > 0:
            save_results(all_results, output_file)
    
    # Final save
    save_results(all_results, output_file)
    
    # Cleanup
    await consensus.close()
    
    # Summary statistics
    total_time = time.time() - start_time
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    SIMULATION COMPLETE                         ║
╠══════════════════════════════════════════════════════════════╣
║  Total Episodes:   {len(all_results):>15,}                          ║
║  Total Time:       {total_time:>15.1f}s                          ║
║  Avg Rate:         {len(all_results)/total_time:>15.1f} ep/s                       ║
║  Results File:     {output_file:>15}                          ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    return all_results


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    asyncio.run(main())
