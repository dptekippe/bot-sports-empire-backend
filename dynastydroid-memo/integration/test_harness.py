"""
MEMO Test Harness
=================
End-to-end test harness for the MEMO-pgvector system.

Runs self-play experiments on toy games and asserts that:
  "Win rate improves after N self-play games with memory vs without"

Games
-----
1. Fantasy Football Trade Evaluator
   - Two agents (Buyer / Seller) negotiate a fantasy football trade
   - State = current roster + proposed trade
   - Outcome = did the trade improve the team's projected points?
   - Agents query MEMO for past trade insights before evaluating

2. Simple Negotiation (MEMO's SimpleNegotiation-inspired)
   - Two agents split a pot of tokens; each has private valuation
   - Must agree on a split; disagreement → 0 for both
   - Agents query MEMO for past negotiation strategies

Test runner
-----------
$ python -m integration.test_harness
$ python -m integration.test_harness --game fantasy_football --games 20 --verbose

Architecture
------------
  ToyGame (ABC)
    ├── FantasyFootballTradeGame
    └── SimpleNegotiationGame

  SelfPlayExperiment
    ├── run_without_memory()  → win rate baseline
    └── run_with_memory(n)    → win rate after n memory warm-up games

  assert_improvement(baseline, after_n, threshold=0.1)
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Game protocol
# ---------------------------------------------------------------------------

@dataclass
class GameConfig:
    """Configuration for a self-play game session."""
    game_id:       uuid.UUID
    seed:          Optional[str] = None
    verbose:       bool = False


@dataclass
class GameResult:
    """Outcome of a single self-play game."""
    trajectory_id: uuid.UUID
    game_id:       uuid.UUID
    outcome:       str           # "win" | "loss" | "draw"
    agent_a_score: float         # Agent A's final score
    agent_b_score: float         # Agent B's final score
    steps:         list[dict]    # State history


class ToyGame(ABC):
    """Abstract base for toy games used in the test harness."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable game name."""
        ...

    @property
    @abstractmethod
    def game_type(self) -> str:
        """MEMO game_type identifier, e.g. 'fantasy_football'."""
        ...

    @abstractmethod
    def setup(self, seed: Optional[str] = None) -> dict:
        """
        Initialize game state.

        Returns the initial state dict (must contain a 'description' key).
        """
        ...

    @abstractmethod
    def step(self, state: dict, agent: str, action: Any) -> dict:
        """
        Execute one step.

        Args:
            state:  Current game state.
            agent:  "agent_a" or "agent_b"
            action: Agent-chosen action

        Returns:
            New state dict.
        """
        ...

    @abstractmethod
    def is_done(self, state: dict) -> bool:
        """Return True if the game has ended."""
        ...

    @abstractmethod
    def payoff(self, state: dict) -> tuple[float, float]:
        """
        Compute final payoffs for agent_a and agent_b.

        Returns:
            (agent_a_score, agent_b_score)
        """
        ...

    @abstractmethod
    def score(self, state: dict, agent: str) -> float:
        """Return the current score for an agent (for RL reward signal)."""
        ...

    @abstractmethod
    def describe_state(self, state: dict) -> str:
        """Return a human-readable description of the state."""
        ...

    def policy_without_memory(self, state: dict, agent: str) -> Any:
        """
        Default policy: random valid action.

        Override for smarter baseline agents.
        """
        return None

    def policy_with_memory(
        self, state: dict, agent: str, memories: list[Any]
    ) -> Any:
        """
        Policy that takes MEMO memory context into account.

        Default: delegate to random policy if no relevant memories found.
        Override per game for meaningful memory-driven behaviour.
        """
        return self.policy_without_memory(state, agent)


# ---------------------------------------------------------------------------
# Game 1: Fantasy Football Trade Evaluator
# ---------------------------------------------------------------------------

# Pre-built player pool (simplified for toy use)
TOY_PLAYERS = {
    "bijan_robinson":  {"name": "Bijan Robinson", "pos": "RB", "value": 9500},
    "josh_allen":     {"name": "Josh Allen",     "pos": "QB", "value": 9700},
    "ja_mason":       {"name": "Ja'Marr Chase",  "pos": "WR", "value": 9400},
    "ceedee_lamb":    {"name": "CeeDee Lamb",    "pos": "WR", "value": 9300},
    "travis_kelce":   {"name": "Travis Kelce",   "pos": "TE", "value": 8800},
    "brittany_gardner":{"name":"Brittany Gardner","pos":"WR","value": 1500},
    "mason_crosby":   {"name": "Mason Crosby",   "pos": "K",  "value": 500},
    "d/ST_bears":     {"name": "Bears D/ST",     "pos": "DST","value": 800},
    "derrick_henry":  {"name": "Derrick Henry",  "pos": "RB", "value": 8500},
    "a.j._brown":     {"name": "A.J. Brown",     "pos": "WR", "value": 8200},
    "darren_waller":  {"name": "Darren Waller",  "pos": "TE", "value": 6000},
    "tom_brady":      {"name": "Tom Brady",      "pos": "QB", "value": 4000},
}

TRADE_TEMPLATES = [
    {
        "give": ["bijan_robinson"], "receive": ["josh_allen"],
        "label": "Sell Bijan for Josh Allen",
    },
    {
        "give": ["ja_mason"], "receive": ["derrick_henry", "mason_crosby"],
        "label": "Sell Chase for Henry + K",
    },
    {
        "give": ["travis_kelce"], "receive": ["darren_waller"],
        "label": "Downgrade TE",
    },
    {
        "give": ["tom_brady"], "receive": ["brittany_gardner", "d/ST_bears"],
        "label": "Dump Brady for depth",
    },
]


class FantasyFootballTradeGame(ToyGame):
    """
    Fantasy football trade negotiation game.

    Agents (Buyer / Seller) evaluate whether a proposed trade improves
    their projected fantasy points.

    State dict shape:
      {
        "phase": "evaluate" | "done",
        "roster_a": [player_ids...],
        "roster_b": [player_ids...],
        "proposed_trade": {"give": [...], "receive": [...]},
        "agent_a_decision": bool | None,
        "agent_b_decision": bool | None,
        "winner": None | "agent_a" | "agent_b",
      }
    """

    @property
    def name(self) -> str:
        return "Fantasy Football Trade Evaluator"

    @property
    def game_type(self) -> str:
        return "fantasy_football_trade"

    def _roster_value(self, player_ids: list[str]) -> float:
        return sum(TOY_PLAYERS[p]["value"] for p in player_ids)

    def _roster_points(self, player_ids: list[str]) -> float:
        # Simplified projected points model:
        # QB: value/100, RB: value/120, WR: value/130, TE: value/150, K/DST: value/50
        total = 0.0
        for pid in player_ids:
            p = TOY_PLAYERS[pid]
            divisor = {"QB": 100, "RB": 120, "WR": 130, "TE": 150, "K": 50, "DST": 50}.get(p["pos"], 100)
            total += p["value"] / divisor
        return total

    def setup(self, seed: Optional[str] = None) -> dict:
        rng = random.Random(seed)
        # Build two roughly balanced rosters
        all_ids = list(TOY_PLAYERS.keys())
        rng.shuffle(all_ids)
        mid = len(all_ids) // 2
        roster_a = all_ids[:mid]
        roster_b = all_ids[mid:]
        # Pick a random trade template
        trade = rng.choice(TRADE_TEMPLATES)
        return {
            "phase": "evaluate",
            "roster_a": roster_a,
            "roster_b": roster_b,
            "proposed_trade": trade,
            "agent_a_decision": None,
            "agent_b_decision": None,
            "winner": None,
        }

    def score(self, state: dict, agent: str) -> float:
        if agent == "agent_a":
            return self._roster_points(state["roster_a"])
        return self._roster_points(state["roster_b"])

    def is_done(self, state: dict) -> bool:
        return state["phase"] == "done"

    def step(self, state: dict, agent: str, action: Any) -> dict:
        # action = True (accept) or False (reject)
        if agent == "agent_a":
            state["agent_a_decision"] = bool(action)
        else:
            state["agent_b_decision"] = bool(action)

        if state["agent_a_decision"] is not None and state["agent_b_decision"] is not None:
            state["phase"] = "done"
            both_accepted = state["agent_a_decision"] and state["agent_b_decision"]
            neither_accepted = not state["agent_a_decision"] and not state["agent_b_decision"]
            if both_accepted:
                # Execute trade and declare winner based on who gains more projected points
                winner = self._resolve_trade(state)
                state["winner"] = winner
            elif neither_accepted:
                state["winner"] = "draw"
            else:
                state["winner"] = "rejected"
        return state

    def _resolve_trade(self, state: dict) -> str:
        give_a = set(state["proposed_trade"]["give"])
        recv_a = set(state["proposed_trade"]["receive"])
        give_b = recv_a
        recv_b = give_a

        new_a = [p for p in state["roster_a"] if p not in give_a] + list(recv_a)
        new_b = [p for p in state["roster_b"] if p not in give_b] + list(recv_b)

        pts_a_before = self._roster_points(state["roster_a"])
        pts_b_before = self._roster_points(state["roster_b"])
        pts_a_after  = self._roster_points(new_a)
        pts_b_after  = self._roster_points(new_b)

        delta_a = pts_a_after - pts_a_before
        delta_b = pts_b_after - pts_b_before

        if delta_a > delta_b:
            return "agent_a"
        elif delta_b > delta_a:
            return "agent_b"
        return "draw"

    def payoff(self, state: dict) -> tuple[float, float]:
        if state["winner"] == "agent_a":
            return 1.0, 0.0
        elif state["winner"] == "agent_b":
            return 0.0, 1.0
        return 0.5, 0.5

    def describe_state(self, state: dict) -> str:
        trade = state["proposed_trade"]
        give_names = [TOY_PLAYERS[p]["name"] for p in trade["give"]]
        recv_names = [TOY_PLAYERS[p]["name"] for p in trade["receive"]]
        return (
            f"Trade: give {', '.join(give_names)} for {', '.join(recv_names)}. "
            f"Agent A decision: {state['agent_a_decision']}, "
            f"Agent B decision: {state['agent_b_decision']}"
        )

    def policy_without_memory(self, state: dict, agent: str) -> bool:
        """
        Default: accept if the trade improves projected points by > 5%.
        Uses a simple heuristic (no memory).
        """
        trade = state["proposed_trade"]
        if agent == "agent_a":
            give_ids = trade["give"]
            recv_ids = trade["receive"]
            before = self._roster_points(state["roster_a"])
            after_ids = [p for p in state["roster_a"] if p not in give_ids] + recv_ids
            after = self._roster_points(after_ids)
        else:
            give_ids = trade["receive"]   # from B's perspective
            recv_ids = trade["give"]
            before = self._roster_points(state["roster_b"])
            after_ids = [p for p in state["roster_b"] if p not in give_ids] + recv_ids
            after = self._roster_points(after_ids)

        return after >= before * 1.05   # accept if ≥5% improvement

    def policy_with_memory(
        self, state: dict, agent: str, memories: list[Any]
    ) -> bool:
        """
        Memory-augmented policy: accept if memory insights confirm the trade
        is historically good, or if the simple threshold check passes.
        """
        trade_label = state["proposed_trade"]["label"].lower()
        # Check if any memory mentions this trade type positively
        positive_mentions = 0
        for mem in memories:
            text = mem.text.lower()
            if any(word in text for word in ["trade", "accept", "improve", "worth"]):
                if "bad" not in text and "reject" not in text:
                    positive_mentions += 1

        # If memory is very confident, follow it; otherwise fall back to heuristic
        if len(memories) >= 3 and positive_mentions >= len(memories) * 0.6:
            return True
        return self.policy_without_memory(state, agent)


# ---------------------------------------------------------------------------
# Game 2: Simple Negotiation
# ---------------------------------------------------------------------------

class SimpleNegotiationGame(ToyGame):
    """
    Simple negotiation game (MEMO SimpleNegotiation-inspired).

    Two agents must agree on how to split a pot of 100 tokens.
    Each agent has a private reservation value; if the proposed split
    is below their reservation, they reject.

    State dict shape:
      {
        "phase": "propose" | "respond" | "done",
        "pot": 100,
        "agent_a_valuations": (35, 65),   # (reservation, aspiration)
        "agent_b_valuations": (40, 60),
        "current_proposer": "agent_a",
        "proposal": {"agent_a": int, "agent_b": int} | None,
        "winner": None | "agent_a" | "agent_b",
      }
    """

    @property
    def name(self) -> str:
        return "Simple Negotiation"

    @property
    def game_type(self) -> str:
        return "negotiation"

    def setup(self, seed: Optional[str] = None) -> dict:
        rng = random.Random(seed)
        # Random valuations that sum to > 100 (leaving room for agreement zone)
        a_res = rng.randint(20, 45)
        b_res = rng.randint(20, 45)
        if a_res + b_res >= 95:
            a_res = min(a_res, 90 - b_res)
        return {
            "phase": "propose",
            "pot": 100,
            "agent_a_valuations": (a_res, a_res + rng.randint(20, 40)),
            "agent_b_valuations": (b_res, b_res + rng.randint(20, 40)),
            "current_proposer": "agent_a",
            "proposal": None,
            "winner": None,
        }

    def score(self, state: dict, agent: str) -> float:
        if state["proposal"] is None:
            return 0.0
        return float(state["proposal"].get(agent, 0))

    def is_done(self, state: dict) -> bool:
        return state["phase"] == "done"

    def step(self, state: dict, agent: str, action: Any) -> dict:
        # action = proposed split {"agent_a": int, "agent_b": int}
        if state["phase"] == "propose":
            state["proposal"] = action
            state["phase"] = "respond"
        elif state["phase"] == "respond":
            responder = "agent_b" if state["current_proposer"] == "agent_a" else "agent_a"
            assert agent == responder
            if bool(action):  # accept
                state["winner"] = agent
                state["phase"] = "done"
            else:
                # Negotiation failed
                state["winner"] = "draw"
                state["phase"] = "done"
        return state

    def payoff(self, state: dict) -> tuple[float, float]:
        if state["winner"] == "agent_a":
            return float(state["proposal"]["agent_a"]), float(state["proposal"]["agent_b"])
        elif state["winner"] == "agent_b":
            return 0.0, 0.0   # no agreement
        return 0.0, 0.0

    def describe_state(self, state: dict) -> str:
        prop = state["proposal"]
        if prop:
            return f"Proposal: A gets {prop['agent_a']}, B gets {prop['agent_b']}. Phase: {state['phase']}"
        return f"Pot of {state['pot']}. {state['current_proposer']} to propose."

    def _accept_if_fair(self, state: dict, agent: str, proposal: dict) -> bool:
        """Accept if the proposal meets reservation value."""
        res = (state["agent_a_valuations"][0] if agent == "agent_a" else state["agent_b_valuations"][0])
        offered = proposal.get(agent, 0)
        return offered >= res

    def policy_without_memory(self, state: dict, agent: str) -> Any:
        """
        Default: make a fair split proposal (50/50), accept if proposal meets reservation.
        """
        if state["phase"] == "propose":
            return {"agent_a": 50, "agent_b": 50}
        elif state["phase"] == "respond":
            return self._accept_if_fair(state, agent, state["proposal"])

    def policy_with_memory(
        self, state: dict, agent: str, memories: list[Any]
    ) -> Any:
        """
        Memory-augmented: use insights about negotiation tactics to
        inform proposals and acceptance thresholds.
        """
        # Check if memory suggests being more aggressive or cooperative
        aggressive = 0
        for mem in memories:
            text = mem.text.lower()
            if any(w in text for w in ["aggressive", "hold", "hardball", "high"]):
                aggressive += 1
            elif any(w in text for w in ["cooperate", "fair", "split", "compromise"]):
                aggressive -= 1

        if state["phase"] == "propose":
            if aggressive > 1:
                # Hardball: ask for 70% of pot
                if agent == "agent_a":
                    return {"agent_a": 70, "agent_b": 30}
                return {"agent_a": 30, "agent_b": 70}
            else:
                return {"agent_a": 50, "agent_b": 50}
        elif state["phase"] == "respond":
            # Be slightly more willing to accept if memory says cooperate
            if aggressive < -1:
                # Lenient: accept if proposal is within 5 of reservation
                res = (state["agent_a_valuations"][0] if agent == "agent_a" else state["agent_b_valuations"][0])
                offered = state["proposal"].get(agent, 0)
                return offered >= res - 5
            return self._accept_if_fair(state, agent, state["proposal"])


# ---------------------------------------------------------------------------
# Self-play experiment runner
# ---------------------------------------------------------------------------

class SelfPlayExperiment:
    """
    Runs self-play experiments and compares win rates with/without memory.

    Usage
    -----
    exp = SelfPlayExperiment(game=game, memo=memo_interface, game_id=game_uuid)
    baseline = exp.run_without_memory(n=20)
    with_memory = exp.run_with_memory(n=20, warmup_games=10)
    improvement = with_memory["agent_a_win_rate"] - baseline["agent_a_win_rate"]
    """

    def __init__(
        self,
        game: ToyGame,
        memo: Any,          # MemoInterface instance
        game_id: uuid.UUID,
        verbose: bool = False,
    ):
        self.game     = game
        self.memo     = memo
        self.game_id  = game_id
        self.verbose  = verbose

    def run_games(
        self,
        n: int,
        use_memory: bool,
        warmup_games: int = 0,
    ) -> dict:
        """
        Run n self-play games.

        Args:
            n:             Number of games to run.
            use_memory:    If True, call memo_sample_memories before each game.
            warmup_games:  Number of games to run WITHOUT memory before
                           starting to store trajectories (for the `with_memory` run).

        Returns:
            dict with keys:
              total_games, agent_a_wins, agent_b_wins, draws,
              agent_a_win_rate, agent_b_win_rate, draw_rate
        """
        agent_a_wins = 0
        agent_b_wins = 0
        draws        = 0
        stored       = 0

        for i in range(n):
            seed    = f"{self.game.name}-{i}-{uuid.uuid4()}"
            state   = self.game.setup(seed=seed)
            step_idx = 0
            steps   = []

            # Memory context (only used when use_memory=True)
            memories = []
            if use_memory:
                memories = self.memo.memo_sample_memories(
                    game_id=self.game_id,
                    k=10,
                    strategy="diverse",
                )
                if self.verbose:
                    print(f"  [Game {i}] Memory context: {len(memories)} insights")

            agents = ["agent_a", "agent_b"]
            turn   = 0

            while not self.game.is_done(state):
                agent = agents[turn % 2]

                if use_memory and memories:
                    action = self.game.policy_with_memory(state, agent, memories)
                else:
                    action = self.game.policy_without_memory(state, agent)

                state = self.game.step(state, agent, action)

                steps.append({
                    "step_idx": step_idx,
                    "state_json": {"description": self.game.describe_state(state)},
                    "reward": self.game.score(state, agent),
                    "done": self.game.is_done(state),
                })
                step_idx += 1
                turn += 1

            # Determine outcome
            a_score, b_score = self.game.payoff(state)
            if a_score > b_score:
                outcome = "win"
                agent_a_wins += 1
            elif b_score > a_score:
                outcome = "loss"
                agent_b_wins += 1
            else:
                outcome = "draw"
                draws += 1

            if self.verbose:
                print(f"  Game {i}: outcome={outcome}, a={a_score:.2f}, b={b_score:.2f}")

            # Store trajectory (skip first `warmup_games` for warmup period)
            if stored >= warmup_games or warmup_games == 0:
                from integration.memo_interface import TrajectoryProto
                proto = TrajectoryProto(
                    game_id=self.game_id,
                    outcome=outcome,
                    seed=seed,
                    agent_name=f"{self.game.name}_selfplay",
                    steps=steps,
                )
                traj_id = self.memo.memo_add_trajectory(proto)
                # Reflect to extract insights
                self.memo.memo_reflect(traj_id)
                stored += 1

        total = n
        return {
            "total_games":     total,
            "agent_a_wins":    agent_a_wins,
            "agent_b_wins":    agent_b_wins,
            "draws":           draws,
            "agent_a_win_rate": agent_a_wins / total,
            "agent_b_win_rate": agent_b_wins / total,
            "draw_rate":       draws / total,
            "trajectories_stored": stored,
        }

    def run_without_memory(self, n: int = 20) -> dict:
        """Run n games with no memory retrieval."""
        return self.run_games(n=n, use_memory=False)

    def run_with_memory(self, n: int = 20, warmup_games: int = 10) -> dict:
        """
        Run n games with memory retrieval.

        Args:
            n:             Total games to run.
            warmup_games:  Number of games to run and store (to seed memory)
                           before counting wins.
        """
        return self.run_games(n=n, use_memory=True, warmup_games=warmup_games)


def assert_improvement(
    baseline: dict,
    after_warmup: dict,
    threshold: float = 0.1,
    agent: str = "agent_a",
) -> None:
    """
    Assert that win rate improved by at least `threshold` after memory warmup.

    Raises AssertionError if the improvement is below threshold.
    """
    if agent == "agent_a":
        base_rate    = baseline["agent_a_win_rate"]
        warmup_rate  = after_warmup["agent_a_win_rate"]
    else:
        base_rate    = baseline["agent_b_win_rate"]
        warmup_rate  = after_warmup["agent_b_win_rate"]

    improvement = warmup_rate - base_rate

    status = "✅ PASS" if improvement >= threshold else "❌ FAIL"
    print(
        f"\n{status} — Win rate improvement: {base_rate:.1%} → {warmup_rate:.1%} "
        f"(Δ={improvement:+.1%}, threshold={threshold:.1%})"
    )

    if improvement < threshold:
        raise AssertionError(
            f"Win rate improvement {improvement:.1%} below threshold {threshold:.1%}"
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

GAMES = {
    "fantasy_football": FantasyFootballTradeGame,
    "negotiation":      SimpleNegotiationGame,
}


def main():
    parser = argparse.ArgumentParser(description="MEMO-pgvector test harness")
    parser.add_argument(
        "--game", "-g",
        choices=list(GAMES.keys()),
        default="fantasy_football",
        help="Toy game to run",
    )
    parser.add_argument(
        "--games", "-n",
        type=int,
        default=20,
        help="Number of self-play games per arm",
    )
    parser.add_argument(
        "--warmup", "-w",
        type=int,
        default=10,
        help="Number of warmup games to seed memory",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print per-game details",
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=0.05,
        help="Minimum win-rate improvement to assert (default 0.05)",
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"MEMO Test Harness — {GAMES[args.game]().name}")
    print(f"{'='*60}\n")

    # Initialize MEMO interface
    from integration.memo_interface import MemoInterface, MemoBackend
    memo = MemoInterface(backend=MemoBackend.DIRECT)

    # Register the game (idempotent — re-registering with same name is fine)
    game_type = GAMES[args.game]().game_type
    print(f"[Setup] Registering game type: {game_type}")
    game_id = memo.create_game(
        game_type=game_type,
        name=f"{game_type}_selfplay",
        config={"test_harness": True},
    )
    print(f"[Setup] Game registered: {game_id}\n")

    game = GAMES[args.game]()

    exp = SelfPlayExperiment(
        game=game,
        memo=memo,
        game_id=game_id,
        verbose=args.verbose,
    )

    # Arm 1: baseline (no memory)
    print(f"[Arm 1] Running {args.games} games WITHOUT memory...")
    baseline = exp.run_without_memory(n=args.games)
    print(f"  → Agent A win rate: {baseline['agent_a_win_rate']:.1%}")
    print(f"  → Agent B win rate: {baseline['agent_b_win_rate']:.1%}")
    print(f"  → Draw rate:        {baseline['draw_rate']:.1%}")

    # Arm 2: with memory (after warmup)
    print(f"\n[Arm 2] Running {args.games} games WITH memory (warmup={args.warmup})...")
    after_warmup = exp.run_with_memory(n=args.games, warmup_games=args.warmup)
    print(f"  → Agent A win rate: {after_warmup['agent_a_win_rate']:.1%}")
    print(f"  → Agent B win rate: {after_warmup['agent_b_win_rate']:.1%}")
    print(f"  → Draw rate:        {after_warmup['draw_rate']:.1%}")
    print(f"  → Trajectories stored: {after_warmup['trajectories_stored']}")

    # Assertions
    print(f"\n{'='*60}")
    print("Assertion: Agent A win rate improves after memory warmup")
    assert_improvement(baseline, after_warmup, threshold=args.threshold, agent="agent_a")

    print("\nAssertion: Agent B win rate improves after memory warmup")
    assert_improvement(baseline, after_warmup, threshold=args.threshold, agent="agent_b")

    print(f"\n{'='*60}")
    print("✅ All assertions passed.")
    print(f"\nFinal insight count in MEMO: {memo.get_insight_count(game_id=game_id)}")


if __name__ == "__main__":
    main()
