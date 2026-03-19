"""
Bestball Draft Simulator - Swarm Agents

Three specialized agents that vote on draft picks:
- Drafter (MiniMax-M2.5): ADP value + positional scarcity
- Valuator (DeepSeek): Projection variance + aging curves
- Optimizer (Gemini): Weekly ceiling + tournament survival
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

# =============================================================================
# Data Models
# =============================================================================

@dataclass
class Player:
    """Represents a fantasy football player."""
    name: str
    position: str  # QB, RB, WR, TE
    adp: float  # Average draft position (lower = drafted earlier)
    adp_rank: int
    age: int
    projected_points: float
    projection_variance: float  # Standard deviation of projections
    injury_risk: float  # 0.0-1.0 scale
    bye_week: int
    years_exp: int
    
    # Historical data for aging curves
    injury_history: list[str] = field(default_factory=list)  # e.g., ["ACL_2022", "hamstring_2023"]
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "position": self.position,
            "adp": self.adp,
            "adp_rank": self.adp_rank,
            "age": self.age,
            "projected_points": self.projected_points,
            "projection_variance": self.projection_variance,
            "injury_risk": self.injury_risk,
            "bye_week": self.bye_week,
            "years_exp": self.years_exp,
            "injury_history": self.injury_history,
        }


@dataclass
class DraftContext:
    """Current state of the draft."""
    round: int
    pick_in_round: int
    total_picks: int
    my_picks: list[str] = field(default_factory=list)  # Names of players I've drafted
    all_picks: list[str] = field(default_factory=list)  # All picks made so far
    my_roster: dict[str, int] = field(default_factory=lambda: {"QB": 0, "RB": 0, "WR": 0, "TE": 0})
    available_players: list[Player] = field(default_factory=list)
    
    @property
    def spots_filled(self) -> int:
        return sum(self.my_roster.values())
    
    @property
    def spots_remaining(self) -> int:
        return 16 - self.spots_filled  # Standard 16 roster spots


@dataclass 
class AgentVote:
    """Vote from a single agent."""
    agent_name: str
    agent_role: str
    pick: str  # Player name
    reasoning: str
    confidence: float  # 0.0-1.0
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "agent_role": self.agent_role,
            "pick": self.pick,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


# =============================================================================
# Response Cache
# =============================================================================

class ResponseCache:
    """Simple in-memory cache for agent responses to avoid redundant calls."""
    
    def __init__(self, ttl_seconds: int = 300):
        self._cache: dict[str, tuple[str, float]] = {}
        self._ttl = ttl_seconds
    
    def _make_key(self, agent_name: str, context_hash: str, players_hash: str) -> str:
        return hashlib.sha256(f"{agent_name}:{context_hash}:{players_hash}".encode()).hexdigest()[:16]
    
    def get(self, agent_name: str, context: DraftContext, available_players: list[Player]) -> Optional[str]:
        ctx_hash = hashlib.sha256(str(context.round).encode()).hexdigest()[:8]
        players_hash = hashlib.sha256(
            "".join(p.name for p in available_players).encode()
        ).hexdigest()[:8]
        key = self._make_key(agent_name, ctx_hash, players_hash)
        
        if key in self._cache:
            result, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl:
                return result
            del self._cache[key]
        return None
    
    def set(self, agent_name: str, context: DraftContext, available_players: list[Player], response: str):
        ctx_hash = hashlib.sha256(str(context.round).encode()).hexdigest()[:8]
        players_hash = hashlib.sha256(
            "".join(p.name for p in available_players).encode()
        ).hexdigest()[:8]
        key = self._make_key(agent_name, ctx_hash, players_hash)
        self._cache[key] = (response, time.time())
    
    def clear(self):
        self._cache.clear()


# =============================================================================
# Agent Prompts
# =============================================================================

AGENT_PROMPTS = {
    "drafter": """You are a bestball draft expert focusing on ADP value and positional scarcity.

Your strategy:
1. Pick the player with the highest ADP value (draft them earlier than their ADP suggests = good value)
2. Track positional scarcity - if a position is thin, grab starters early
3. Avoid reaching (drafting a player much earlier than their ADP)
4. Target consensus value picks

Available players are ranked by ADP. Draft the player who represents the best value relative to their draft position.

Return your pick in this exact format:
PICK: [Player Name]
REASONING: [1-2 sentences explaining why this is the best ADP value pick]
CONFIDENCE: [0.0-1.0]""",
    
    "valuator": """You are a dynasty fantasy analyst focusing on projection variance, injury priors, and aging curves.

Your aging curve model:
- RBs decline faster after age 26 (-0.5 EV per year past 26)
- WRs peak 27-29, decline slowly after (-0.3 EV per year past 29)
- QBs peak 28-32, minimal decline (-0.2 EV per year past 32)
- TEs decline sharply after 30 (-0.8 EV per year past 30)
- Injury risk increases with age and history

Key factors:
- Players with high projection variance = boom/bust (risky but high ceiling)
- Players with injury history = red flags, discount their projections
- Age-adjusted expected value over full season

Pick for LONG-TERM EXPECTED VALUE considering age, injury risk, and projection variance.

Return your pick in this exact format:
PICK: [Player Name]
REASONING: [1-2 sentences on age/injury/projections]
CONFIDENCE: [0.0-1.0]""",
    
    "optimizer": """You are a tournament specialist focusing on weekly ceiling and lineup optimization.

Bestball tournament strategy:
- Draft for HIGHEST WEEKLY CEILING, not total points
- Bestball uses your best lineup each week = weekly boom potential matters most
- Bye week stacking: avoid having too many players on the same bye
- Build depth at RB and WR (high injury positions)
- Tournament survival = roster flexibility to survive injuries

Key considerations:
- Boom/bust players have higher weekly ceiling = better for tournaments
- Stacking QBs with WRs from same team can amplify weekly ceiling
- Need backup depth at RB/WR for injury survival
- TEs are volatile week-to-week, streaming can work

Pick for MAXIMUM WEEKLY CEILING with tournament survival depth.

Return your pick in this exact format:
PICK: [Player Name]
REASONING: [1-2 sentences on weekly ceiling/tournament survival]
CONFIDENCE: [0.0-1.0]""",
}


# =============================================================================
# Base Swarm Agent
# =============================================================================

class SwarmAgent(ABC):
    """Base class for all swarm draft agents."""
    
    def __init__(self, name: str, role: str, model: str):
        self.name = name
        self.role = role
        self.model = model
        self._confidence = 0.7  # Base confidence
        self._last_reasoning = ""
    
    @abstractmethod
    async def generate_pick(self, context: DraftContext, available_players: list[Player]) -> str:
        """
        Given draft context and available players, return the best pick.
        Must be implemented by subclasses.
        """
        pass
    
    @abstractmethod
    def _build_prompt(self, context: DraftContext, available_players: list[Player]) -> str:
        """Build the agent-specific prompt with current context."""
        pass
    
    @abstractmethod
    def _parse_response(self, response: str) -> tuple[str, str, float]:
        """Parse model response into (player_name, reasoning, confidence)."""
        pass
    
    def get_confidence(self) -> float:
        """Return confidence score (0-1) for voting weight."""
        return self._confidence
    
    def get_reasoning(self) -> str:
        """Return last reasoning from this agent."""
        return self._last_reasoning
    
    async def think(self, context: DraftContext, available_players: list[Player]) -> AgentVote:
        """
        Main thinking loop - generates a pick and returns a vote.
        """
        response = await self.generate_pick(context, available_players)
        player_name, reasoning, confidence = self._parse_response(response)
        
        self._confidence = confidence
        self._last_reasoning = reasoning
        
        return AgentVote(
            agent_name=self.name,
            agent_role=self.role,
            pick=player_name,
            reasoning=reasoning,
            confidence=confidence,
        )


# =============================================================================
# Drafter Agent (MiniMax-M2.5)
# =============================================================================

class DrafterAgent(SwarmAgent):
    """
    Focus: ADP awareness, positional scarcity, value picks.
    Model: MiniMax-M2.5
    """
    
    def __init__(self):
        super().__init__(
            name="Drafter",
            role="ADP_Value_Scarcity",
            model="MiniMax-M2.5"
        )
        self._positional_depth: dict[str, list[float]] = {}  # Track ADP of available at each position
        self._scarce_positions: set[str] = set()
    
    def _analyze_scarcity(self, available_players: list[Player]) -> dict[str, int]:
        """Count available players by position."""
        counts = {"QB": 0, "RB": 0, "WR": 0, "TE": 0}
        for p in available_players:
            if p.position in counts:
                counts[p.position] += 1
        return counts
    
    def _build_prompt(self, context: DraftContext, available_players: list[Player]) -> str:
        scarcity = self._analyze_scarcity(available_players)
        
        # Format available players sorted by ADP
        player_list = "\n".join([
            f"{i+1}. {p.name} ({p.position}) - ADP: {p.adp}, Proj: {p.projected_points}"
            for i, p in enumerate(sorted(available_players, key=lambda x: x.adp)[:30])
        ])
        
        prompt = f"""{AGENT_PROMPTS['drafter']}

CURRENT DRAFT STATE:
- Round: {context.round}
- Your picks: {', '.join(context.my_picks) if context.my_picks else 'None yet'}
- Your roster: {context.my_roster}

POSITIONAL SCARCITY (players available):
- QB: {scarcity['QB']} available
- RB: {scarcity['RB']} available  
- WR: {scarcity['WR']} available
- TE: {scarcity['TE']} available

TOP 30 AVAILABLE PLAYERS (by ADP):
{player_list}

Pick the best value. Consider:
1. Draft players earlier than ADP suggests (positive value = good)
2. If RB/WR are scarce, prioritize them
3. Don't reach more than 5 spots above ADP
"""
        return prompt
    
    async def generate_pick(self, context: DraftContext, available_players: list[Player]) -> str:
        """
        Generate pick using MiniMax-M2.5.
        In production, this would call sessions_spawn or the MiniMax API.
        """
        prompt = self._build_prompt(context, available_players)
        
        # Cache check
        cached = ResponseCache().get(self.name, context, available_players)
        if cached:
            return cached
        
        # In production: call MiniMax-M2.5 via sessions_spawn or API
        # For now, simulate with a rule-based fallback
        response = await self._simulate_drafter_pick(context, available_players)
        
        ResponseCache().set(self.name, context, available_players, response)
        return response
    
    async def _simulate_drafter_pick(self, context: DraftContext, available_players: list[Player]) -> str:
        """
        Rule-based simulation for testing when API unavailable.
        """
        if not available_players:
            return "PICK: No players available\nREASONING: Empty player pool\nCONFIDENCE: 0.0"
        
        # Sort by ADP value (lower adp = better value at that pick)
        sorted_players = sorted(available_players, key=lambda x: x.adp)
        
        # Find best ADP value: smallest gap between current round and ADP
        # Value = ADP is "supposed" to go, actual pick is where we get them
        best_pick = sorted_players[0]  # Default to best ADP
        best_value = float('inf')
        
        for player in sorted_players[:15]:
            # Value = how early we take them vs their ADP
            # Taking CMC at 1.01 when ADP is 1.01 = 0 value (perfect)
            # Taking CMC at 2.01 when ADP is 1.01 = -1.0 value (reach)
            # Taking player at 50 when ADP is 80 = +30 value (steal)
            expected_round = (player.adp_rank - 1) // 12 + 1  # Rough estimate
            value_diff = expected_round - context.round
            
            # Adjust for scarcity - being in range is still good
            if value_diff >= -3:  # Within 3 rounds of expected
                if value_diff < best_value:
                    best_value = value_diff
                    best_pick = player
        
        confidence = 0.7 + (0.2 * (1 - min(abs(best_value), 5) / 5))
        
        return f"""PICK: {best_pick.name}
REASONING: Best ADP value - drafting {best_pick.name} ({best_pick.position}) at ADP {best_pick.adp_rank}. 
Positional scarcity: {self._analyze_scarcity(available_players)[best_pick.position]} {best_pick.position}s available.
CONFIDENCE: {min(confidence, 0.95):.2f}"""
    
    def _parse_response(self, response: str) -> tuple[str, str, float]:
        """Parse Drafter response."""
        lines = response.strip().split("\n")
        player_name = ""
        reasoning = ""
        confidence = 0.7
        
        for line in lines:
            if line.startswith("PICK:"):
                player_name = line.replace("PICK:", "").strip()
            elif line.startswith("REASONING:"):
                reasoning = line.replace("REASONING:", "").strip()
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.replace("CONFIDENCE:", "").strip())
                except ValueError:
                    confidence = 0.7
        
        return player_name, reasoning, confidence


# =============================================================================
# Valuator Agent (DeepSeek)
# =============================================================================

class ValuatorAgent(SwarmAgent):
    """
    Focus: Projection variance, injury priors, aging curves.
    Model: DeepSeek
    """
    
    # Aging curve adjustments per year past threshold
    AGING_CURVES = {
        "RB": {"threshold": 26, "decay": -0.5},
        "WR": {"threshold": 29, "decay": -0.3},
        "QB": {"threshold": 32, "decay": -0.2},
        "TE": {"threshold": 30, "decay": -0.8},
    }
    
    def __init__(self):
        super().__init__(
            name="Valuator", 
            role="Projection_Aging_Injury",
            model="DeepSeek"
        )
    
    def _calculate_age_adjusted_ev(self, player: Player) -> float:
        """Calculate age-adjusted expected value."""
        base_ev = player.projected_points
        
        if player.position in self.AGING_CURVES:
            curve = self.AGING_CURVES[player.position]
            if player.age > curve["threshold"]:
                years_past = player.age - curve["threshold"]
                age_penalty = years_past * curve["decay"]
                base_ev += age_penalty  # Decay is negative, so this reduces EV
        
        # Injury history penalty
        injury_penalty = len(player.injury_history) * 0.05 * player.projected_points
        base_ev -= injury_penalty
        
        # High projection variance = risky but potential upside
        # For long-term value, slightly discount variance
        variance_discount = 0.1 * (player.projection_variance / 100)
        base_ev *= (1 - variance_discount)
        
        return base_ev
    
    def _build_prompt(self, context: DraftContext, available_players: list[Player]) -> str:
        # Format with aging curve info
        player_list = []
        for p in sorted(available_players, key=lambda x: self._calculate_age_adjusted_ev(x), reverse=True)[:25]:
            age_adj = self._calculate_age_adjusted_ev(p)
            injuries = ", ".join(p.injury_history) if p.injury_history else "None"
            player_list.append(
                f"{p.name} ({p.position}, Age {p.age}) - Proj: {p.projected_points:.1f}, "
                f"Variance: ±{p.projection_variance:.1f}, Injury Risk: {p.injury_risk:.2f}, "
                f"Injuries: {injuries}, Age-Adj EV: {age_adj:.1f}"
            )
        
        prompt = f"""{AGENT_PROMPTS['valuator']}

AGING CURVES BY POSITION:
- RB: Decline after 26 (-0.5 EV/year past 26)
- WR: Peak 27-29, slow decline (-0.3 EV/year past 29)  
- QB: Peak 28-32 (-0.2 EV/year past 32)
- TE: Sharp decline after 30 (-0.8 EV/year past 30)

CURRENT DRAFT STATE:
- Round: {context.round}
- Your picks: {', '.join(context.my_picks) if context.my_picks else 'None yet'}
- Your roster: {context.my_roster}

TOP 25 PLAYERS BY AGE-ADJUSTED EXPECTED VALUE:
{chr(10).join(player_list)}

Pick for LONG-TERM EXPECTED VALUE. Consider:
1. Age-adjusted projections
2. Injury history impact on durability
3. Projection variance (high variance = boom/bust)
4. Dynasty value (not just this year)
"""
        return prompt
    
    async def generate_pick(self, context: DraftContext, available_players: list[Player]) -> str:
        """Generate pick using DeepSeek."""
        prompt = self._build_prompt(context, available_players)
        
        cached = ResponseCache().get(self.name, context, available_players)
        if cached:
            return cached
        
        # Simulate DeepSeek response with age-adjusted logic
        response = await self._simulate_valuator_pick(context, available_players)
        
        ResponseCache().set(self.name, context, available_players, response)
        return response
    
    async def _simulate_valuator_pick(self, context: DraftContext, available_players: list[Player]) -> str:
        """Rule-based simulation for testing."""
        if not available_players:
            return "PICK: No players available\nREASONING: Empty player pool\nCONFIDENCE: 0.0"
        
        # Calculate age-adjusted EV for all players
        scored = []
        for p in available_players:
            age_adj_ev = self._calculate_age_adjusted_ev(p)
            
            # Injury history multiplier
            injury_count = len(p.injury_history)
            injury_multiplier = 1.0 - (injury_count * 0.08)
            injury_multiplier = max(0.7, injury_multiplier)  # Cap at 30% reduction
            
            final_ev = age_adj_ev * injury_multiplier
            
            # Boost confidence for players with good projection/variance ratio
            if p.projected_points > 200 and p.projection_variance < 30:
                final_ev *= 1.1  # High volume, stable = premium
            
            scored.append((p, final_ev))
        
        # Sort by age-adjusted EV
        scored.sort(key=lambda x: x[1], reverse=True)
        best_player, best_ev = scored[0]
        
        # Calculate confidence based on how clear the choice is
        if len(scored) > 1:
            gap = scored[0][1] - scored[1][1]
            confidence = 0.7 + min(gap / 50, 0.25)  # Larger gap = more confident
        else:
            confidence = 0.9
        
        reasoning = (
            f"Age-adjusted EV: {best_ev:.1f}. {best_player.name} ({best_player.position}, Age {best_player.age}) "
            f"projects well given aging curve. {len(best_player.injury_history)} injury{'es' if len(best_player.injury_history) != 1 else ''} on record."
        )
        
        return f"""PICK: {best_player.name}
REASONING: {reasoning}
CONFIDENCE: {min(confidence, 0.95):.2f}"""
    
    def _parse_response(self, response: str) -> tuple[str, str, float]:
        """Parse Valuator response."""
        lines = response.strip().split("\n")
        player_name = ""
        reasoning = ""
        confidence = 0.7
        
        for line in lines:
            if line.startswith("PICK:"):
                player_name = line.replace("PICK:", "").strip()
            elif line.startswith("REASONING:"):
                reasoning = line.replace("REASONING:", "").strip()
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.replace("CONFIDENCE:", "").strip())
                except ValueError:
                    confidence = 0.7
        
        return player_name, reasoning, confidence


# =============================================================================
# Optimizer Agent (Gemini)
# =============================================================================

class OptimizerAgent(SwarmAgent):
    """
    Focus: Weekly lineup optimization, tournament survival.
    Model: Gemini
    """
    
    def __init__(self):
        super().__init__(
            name="Optimizer",
            role="Weekly_Ceiling_Tournament",
            model="Gemini"
        )
        self._byes_used: set[int] = set()
        self._team_stacks: dict[str, str] = {}  # QB -> WR stack tracking
    
    def _analyze_roster_depth(self, context: DraftContext) -> dict[str, int]:
        """Analyze backup depth at each position."""
        roster = context.my_roster.copy()
        depth = {}
        
        # Need 2 RB slots + 2 backup = minimum 4 RBs
        # Need 3 WR slots + 2 backup = minimum 5 WRs
        depth["RB"] = max(0, 4 - roster.get("RB", 0))
        depth["WR"] = max(0, 5 - roster.get("WR", 0))
        depth["TE"] = max(0, 2 - roster.get("TE", 0))
        depth["QB"] = max(0, 2 - roster.get("QB", 0))
        
        return depth
    
    def _check_bye_conflict(self, player: Player, context: DraftContext) -> bool:
        """Check if adding this player creates bye week conflict."""
        if player.bye_week in self._byes_used:
            return True  # Already have someone on this bye
        return False
    
    def _build_prompt(self, context: DraftContext, available_players: list[Player]) -> str:
        depth_needed = self._analyze_roster_depth(context)
        byes_used = list(self._byes_used) if self._byes_used else ["None"]
        
        # Format players with weekly ceiling info
        player_list = []
        for p in sorted(available_players, key=lambda x: x.projected_points + x.projection_variance, reverse=True)[:25]:
            weekly_ceiling = p.projected_points + p.projection_variance
            player_list.append(
                f"{p.name} ({p.position}) - Ceiling: {weekly_ceiling:.1f}, "
                f"Proj: {p.projected_points:.1f}, Bye: Week {p.bye_week}"
            )
        
        prompt = f"""{AGENT_PROMPTS['optimizer']}

CURRENT ROSTER STATE:
- Round: {context.round}
- Your picks: {', '.join(context.my_picks) if context.my_picks else 'None yet'}
- Your roster: {context.my_roster}
- Roster depth needed: {depth_needed}

BYES ALREADY COVERED: Weeks {', '.join(map(str, byes_used))}

TOP 25 PLAYERS BY WEEKLY CEILING:
{chr(10).join(player_list)}

Pick for MAXIMUM WEEKLY CEILING. Consider:
1. Players with high projection variance = higher weekly ceiling (good for bestball)
2. Avoid bye week stacking (don't double up on same bye week)
3. Build depth at RB/WR for tournament survival
4. QB-WR stacks amplify weekly ceiling when both hit
"""
        return prompt
    
    async def generate_pick(self, context: DraftContext, available_players: list[Player]) -> str:
        """Generate pick using Gemini."""
        prompt = self._build_prompt(context, available_players)
        
        cached = ResponseCache().get(self.name, context, available_players)
        if cached:
            return cached
        
        response = await self._simulate_optimizer_pick(context, available_players)
        
        ResponseCache().set(self.name, context, available_players, response)
        return response
    
    async def _simulate_optimizer_pick(self, context: DraftContext, available_players: list[Player]) -> str:
        """Rule-based simulation for testing."""
        if not available_players:
            return "PICK: No players available\nREASONING: Empty player pool\nCONFIDENCE: 0.0"
        
        depth_needed = self._analyze_roster_depth(context)
        
        # Calculate weekly ceiling score
        scored = []
        for p in available_players:
            # Weekly ceiling = projected + variance (potential to boom)
            weekly_ceiling = p.projected_points + p.projection_variance
            
            # Penalize bye week conflicts
            bye_penalty = 0
            if self._check_bye_conflict(p, context):
                bye_penalty = p.projected_points * 0.15
                weekly_ceiling -= bye_penalty
            
            # Boost for positions we need depth at
            if depth_needed.get(p.position, 0) > 0:
                weekly_ceiling *= 1.15  # 15% boost for needed depth
            
            # Boom/bust bonus - variance is good for tournament ceiling
            if p.projection_variance > 40:
                weekly_ceiling *= 1.1  # 10% bonus for high variance (tournament upside)
            
            scored.append((p, weekly_ceiling))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        best_player, best_ceiling = scored[0]
        
        # Confidence calculation
        if len(scored) > 1:
            gap = scored[0][1] - scored[1][1]
            confidence = 0.7 + min(gap / 30, 0.25)
        else:
            confidence = 0.9
        
        bye_note = "No bye conflict." if not self._check_bye_conflict(best_player, context) else f"Bye Week {best_player.bye_week} conflict."
        
        reasoning = (
            f"Weekly ceiling: {best_ceiling:.1f}. {best_player.name} ({best_player.position}) "
            f"has high tournament upside (variance: ±{best_player.projection_variance:.1f}). "
            f"{bye_note}"
        )
        
        return f"""PICK: {best_player.name}
REASONING: {reasoning}
CONFIDENCE: {min(confidence, 0.95):.2f}"""
    
    def _parse_response(self, response: str) -> tuple[str, str, float]:
        """Parse Optimizer response."""
        lines = response.strip().split("\n")
        player_name = ""
        reasoning = ""
        confidence = 0.7
        
        for line in lines:
            if line.startswith("PICK:"):
                player_name = line.replace("PICK:", "").strip()
            elif line.startswith("REASONING:"):
                reasoning = line.replace("REASONING:", "").strip()
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.replace("CONFIDENCE:", "").strip())
                except ValueError:
                    confidence = 0.7
        
        return player_name, reasoning, confidence


# =============================================================================
# Swarm Manager
# =============================================================================

class DraftSwarm:
    """
    Manages the three-agent swarm for draft decisions.
    Aggregates votes using weighted confidence scoring.
    """
    
    def __init__(self):
        self.drafter = DrafterAgent()
        self.valuator = ValuatorAgent()
        self.optimizer = OptimizerAgent()
        self.agents: list[SwarmAgent] = [self.drafter, self.valuator, self.optimizer]
        self._cache = ResponseCache(ttl_seconds=300)
    
    async def run_draft_poll(self, context: DraftContext, available_players: list[Player]) -> list[AgentVote]:
        """
        Run all three agents in parallel and collect their votes.
        """
        tasks = [agent.think(context, available_players) for agent in self.agents]
        votes = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_votes = []
        for v in votes:
            if isinstance(v, AgentVote):
                valid_votes.append(v)
            elif isinstance(v, Exception):
                print(f"Agent error: {v}")
        
        return valid_votes
    
    def aggregate_votes(self, votes: list[AgentVote]) -> tuple[str, dict]:
        """
        Aggregate votes using weighted confidence scoring.
        Returns (final_pick, vote_summary)
        """
        if not votes:
            return "NO_VOTE", {}
        
        # Weight votes by confidence
        weighted_scores: dict[str, float] = {}
        reasoning_store: dict[str, str] = {}
        
        for vote in votes:
            if vote.pick and vote.pick != "NO_VOTE":
                weighted_scores[vote.pick] = weighted_scores.get(vote.pick, 0) + vote.confidence
                if vote.pick not in reasoning_store:
                    reasoning_store[vote.pick] = vote.reasoning
        
        if not weighted_scores:
            return "NO_VOTE", {}
        
        # Pick the player with highest weighted score
        final_pick = max(weighted_scores, key=weighted_scores.get)
        
        summary = {
            "votes": [v.to_dict() for v in votes],
            "weighted_scores": weighted_scores,
            "final_pick": final_pick,
            "winning_score": weighted_scores[final_pick],
            "reasoning": reasoning_store.get(final_pick, ""),
        }
        
        return final_pick, summary
    
    async def draft_pick(self, context: DraftContext, available_players: list[Player]) -> tuple[str, dict]:
        """
        Main entry point: run all agents and return aggregated decision.
        """
        votes = await self.run_draft_poll(context, available_players)
        final_pick, summary = self.aggregate_votes(votes)
        
        # Update optimizer's bye tracking if we picked someone
        if final_pick != "NO_VOTE":
            picked = next((p for p in available_players if p.name == final_pick), None)
            if picked:
                self.optimizer._byes_used.add(picked.bye_week)
        
        return final_pick, summary
    
    def clear_cache(self):
        """Clear the response cache."""
        self._cache.clear()


# =============================================================================
# Example Usage
# =============================================================================

async def demo():
    """Demo the swarm with sample data."""
    # Create sample players
    players = [
        Player(name="Christian McCaffrey", position="RB", adp=1.0, adp_rank=1, age=28, 
               projected_points=320, projection_variance=35, injury_risk=0.4, bye_week=7, 
               years_exp=8, injury_history=["knee_2020"]),
        Player(name="Ja'Marr Chase", position="WR", adp=2.0, adp_rank=2, age=24, 
               projected_points=290, projection_variance=45, injury_risk=0.2, bye_week=11, 
               years_exp=4),
        Player(name="CeeDee Lamb", position="WR", adp=3.0, adp_rank=3, age=25, 
               projected_points=285, projection_variance=40, injury_risk=0.25, bye_week=7, 
               years_exp=5),
        Player(name="Bijan Robinson", position="RB", adp=4.0, adp_rank=4, age=22, 
               projected_points=270, projection_variance=50, injury_risk=0.3, bye_week=12, 
               years_exp=3),
        Player(name="Marvin Harrison Jr", position="WR", adp=5.0, adp_rank=5, age=22, 
               projected_points=275, projection_variance=55, injury_risk=0.15, bye_week=14, 
               years_exp=2),
        Player(name="Davante Adams", position="WR", adp=8.0, adp_rank=8, age=32, 
               projected_points=250, projection_variance=30, injury_risk=0.5, bye_week=9, 
               years_exp=12, injury_history=["hamstring_2023", "ankle_2024"]),
        Player(name="Jalen Hurts", position="QB", adp=6.0, adp_rank=6, age=26, 
               projected_points=420, projection_variance=60, injury_risk=0.35, bye_week=5, 
               years_exp=5),
        Player(name="Travis Kelce", position="TE", adp=7.0, adp_rank=7, age=35, 
               projected_points=240, projection_variance=25, injury_risk=0.6, bye_week=6, 
               years_exp=12, injury_history=["knee_2022", "back_2023"]),
    ]
    
    # Create draft context
    context = DraftContext(
        round=1,
        pick_in_round=1,
        total_picks=180,
        my_picks=[],
        all_picks=[],
        my_roster={"QB": 0, "RB": 0, "WR": 0, "TE": 0},
        available_players=players,
    )
    
    print("=" * 60)
    print("BESTBALL DRAFT SIMULATOR - SWARM AGENTS")
    print("=" * 60)
    print(f"\nDraft State: Round {context.round}, Pick {context.pick_in_round}")
    print(f"Available Players: {len(players)}")
    print()
    
    # Initialize swarm
    swarm = DraftSwarm()
    
    # Run draft poll
    print("Running swarm agents...")
    votes = await swarm.run_draft_poll(context, players)
    
    print("\n" + "-" * 60)
    print("AGENT VOTES:")
    print("-" * 60)
    
    for vote in votes:
        print(f"\n[{vote.agent_name} ({vote.agent_role})]")
        print(f"  PICK: {vote.pick}")
        print(f"  CONFIDENCE: {vote.confidence:.2f}")
        print(f"  REASONING: {vote.reasoning[:80]}...")
    
    # Aggregate
    final_pick, summary = swarm.aggregate_votes(votes)
    
    print("\n" + "=" * 60)
    print(f"FINAL PICK: {final_pick}")
    print(f"Winning Score: {summary.get('winning_score', 0):.2f}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())