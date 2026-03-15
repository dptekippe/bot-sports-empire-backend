"""
MCTS Exploration Gym v1 - Pre-Answer Reasoning Tree Search

Gymnasium environment for Monte Carlo Tree Search pre-answer reasoning.
Forces exploration-first before committing to a response, counteracting
LLM default of quick first-answer exploitation.

Training target: 15% accuracy lift via PPO+CFR-HER (100k steps).
Part of Roger's metacog_v3 upgrade path.
"""

import math
import random
import hashlib
import json
import os
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field

try:
    import gymnasium as gym
    from gymnasium import spaces
    import numpy as np
except ImportError:
    import gym
    from gym import spaces
    import numpy as np


# ============================================================
# MCTS Hyperparameters
# ============================================================
MAX_DEPTH = 4
NUM_SIMULATIONS = 50
EXPLORATION_CONSTANT = 1.414  # C in UCB1 = sqrt(2)

# Action space
ACTION_EXPLORE_8 = 0
ACTION_EXPLORE_16 = 1
ACTION_CRITIQUE_NL = 2
ACTION_MERGE_TOP3 = 3
ACTION_CONVERGE_FINAL = 4

ACTION_NAMES = {
    ACTION_EXPLORE_8: "explore_8branches",
    ACTION_EXPLORE_16: "explore_16branches",
    ACTION_CRITIQUE_NL: "critique_nl",
    ACTION_MERGE_TOP3: "merge_top3",
    ACTION_CONVERGE_FINAL: "converge_final",
}

# Domain detection keywords and risk mappings
DOMAIN_KEYWORDS = {
    "deploy": {"domain_risk": 0.8, "domain": "deploy"},
    "render": {"domain_risk": 0.8, "domain": "deploy"},
    "hosting": {"domain_risk": 0.8, "domain": "deploy"},
    "production": {"domain_risk": 0.85, "domain": "deploy"},
    "think": {"query_complexity": 0.9, "domain": "reasoning"},
    "complex": {"query_complexity": 0.9, "domain": "reasoning"},
    "optimal": {"query_complexity": 0.9, "domain": "reasoning"},
    "trade": {"domain_risk": 0.7, "query_complexity": 0.7, "domain": "trade"},
    "dynasty": {"domain_risk": 0.6, "query_complexity": 0.7, "domain": "trade"},
    "debug": {"query_complexity": 0.75, "domain": "debug"},
    "error": {"query_complexity": 0.7, "domain": "debug"},
    "cost": {"domain_risk": 0.65, "query_complexity": 0.6, "domain": "cost"},
    "budget": {"domain_risk": 0.65, "query_complexity": 0.6, "domain": "cost"},
    "code": {"query_complexity": 0.6, "domain": "code"},
    "implement": {"query_complexity": 0.65, "domain": "code"},
    "refactor": {"query_complexity": 0.7, "domain": "code"},
}


# ============================================================
# MCTSNode - Tree node with UCB1 selection
# ============================================================
@dataclass
class MCTSNode:
    """Single node in the MCTS reasoning tree."""
    state: Dict[str, Any]
    parent: Optional['MCTSNode'] = None
    children: List['MCTSNode'] = field(default_factory=list)
    visits: int = 0
    total_reward: float = 0.0
    action_taken: Optional[int] = None
    reasoning_path: str = ""
    depth: int = 0

    @property
    def exploit_score(self) -> float:
        if self.visits == 0:
            return 0.0
        return self.total_reward / self.visits

    def ucb1(self, exploration_constant: float = EXPLORATION_CONSTANT) -> float:
        """UCB1 = exploit/visits + C * sqrt(ln(parent_visits) / visits)"""
        if self.visits == 0:
            return float('inf')
        if self.parent is None or self.parent.visits == 0:
            return self.exploit_score
        exploit = self.total_reward / self.visits
        explore = exploration_constant * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )
        return exploit + explore

    def best_child(self, exploration_constant: float = EXPLORATION_CONSTANT) -> 'MCTSNode':
        """Select child with highest UCB1 value."""
        return max(self.children, key=lambda c: c.ucb1(exploration_constant))

    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def is_terminal(self) -> bool:
        return self.depth >= MAX_DEPTH

    def add_child(self, state: Dict, action: int, reasoning: str = "") -> 'MCTSNode':
        child = MCTSNode(
            state=state,
            parent=self,
            action_taken=action,
            reasoning_path=reasoning,
            depth=self.depth + 1,
        )
        self.children.append(child)
        return child


# ============================================================
# Seed Data - 200 synthetic query scenarios
# ============================================================
def generate_seed_scenarios() -> List[Dict]:
    """Generate 200 synthetic query scenarios across 5 domains."""
    scenarios = []
    domains = [
        # Deploy domain (40 scenarios)
        ("deploy", [
            "Optimal Render deploy?", "Best hosting for Node app?",
            "Deploy strategy for microservices?", "Production rollback plan?",
            "Zero-downtime deploy approach?", "Container orchestration choice?",
            "CDN configuration for static assets?", "SSL certificate rotation?",
            "Blue-green deployment setup?", "Canary release strategy?",
            "Auto-scaling configuration?", "Load balancer setup?",
            "Deploy pipeline optimization?", "Staging environment design?",
            "Infrastructure as code approach?", "Cloud cost optimization?",
            "Multi-region deployment?", "Database migration strategy?",
            "Service mesh configuration?", "Monitoring stack selection?",
            "Render vs Railway vs Fly.io?", "Docker compose production?",
            "Kubernetes vs ECS decision?", "Serverless deploy pattern?",
            "Edge function deployment?", "Build cache optimization?",
            "Deploy frequency tradeoffs?", "Feature flag rollout?",
            "Rollback automation?", "Health check configuration?",
            "Deploy notification setup?", "Artifact versioning?",
            "Environment variable management?", "Secret rotation deploy?",
            "Preview environment strategy?", "Deploy approval workflow?",
            "Post-deploy validation?", "Deploy metrics tracking?",
            "Incident response deploy?", "Hotfix deploy process?",
        ]),
        # Debug domain (40 scenarios)
        ("debug", [
            "Debug memory leak in production?", "Error rate spike analysis?",
            "Performance regression root cause?", "Deadlock detection approach?",
            "Log aggregation strategy?", "Distributed tracing setup?",
            "Profiling CPU bottleneck?", "Debug race condition?",
            "Network timeout diagnosis?", "Database query slow analysis?",
            "Debug intermittent failures?", "Memory profiling strategy?",
            "Thread dump analysis?", "Debug API timeout?",
            "Error correlation approach?", "Debug data inconsistency?",
            "Cache invalidation debugging?", "Debug webhook failures?",
            "Debug authentication issues?", "Session management debug?",
            "Debug WebSocket disconnects?", "CORS error diagnosis?",
            "Debug SSL handshake?", "DNS resolution debugging?",
            "Debug connection pooling?", "Debug OOM kills?",
            "Debug high latency?", "Debug queue backpressure?",
            "Debug file descriptor leaks?", "Debug CPU throttling?",
            "Debug disk I/O bottleneck?", "Debug network partitions?",
            "Debug certificate errors?", "Debug rate limiting?",
            "Debug serialization errors?", "Debug encoding issues?",
            "Debug timezone problems?", "Debug caching bugs?",
            "Debug pagination errors?", "Debug concurrency bugs?",
        ]),
        # Trade domain (40 scenarios)
        ("trade", [
            "Optimal dynasty trade value?", "Trade calculator strategy?",
            "Buy low candidate analysis?", "Sell high window detection?",
            "Trade package optimization?", "Dynasty asset valuation?",
            "Rookie pick trade value?", "Contender vs rebuilder trade?",
            "Trade deadline strategy?", "Multi-team trade analysis?",
            "Trade veto analysis?", "Future pick discounting?",
            "Age curve trade timing?", "Injury risk trade adjustment?",
            "Trade offer evaluation?", "Counter-offer strategy?",
            "Trade tree exploration?", "League-specific trade values?",
            "Positional scarcity trade?", "Trade market inefficiency?",
            "Startup draft trade?", "Trade up strategy?",
            "Trade down value?", "Win-now trade calculus?",
            "Rebuild trade priorities?", "Trade partner profiling?",
            "Trade frequency optimization?", "Trade regret analysis?",
            "Historical trade comparison?", "Trade impact projection?",
            "Mid-season trade targets?", "Offseason trade windows?",
            "Trade for depth vs stars?", "Handcuff trade strategy?",
            "IR stash trade value?", "Taxi squad trades?",
            "Best ball trade approach?", "Superflex trade premiums?",
            "TE premium trade values?", "QB trade value windows?",
        ]),
        # Cost domain (40 scenarios)
        ("cost", [
            "Cloud cost optimization?", "Budget allocation strategy?",
            "Cost vs performance tradeoff?", "Reserved instance analysis?",
            "Spot instance strategy?", "Cost monitoring setup?",
            "Resource right-sizing?", "Cost allocation tagging?",
            "Multi-cloud cost comparison?", "Storage cost optimization?",
            "Network cost reduction?", "Compute cost analysis?",
            "Database cost optimization?", "CDN cost management?",
            "API gateway cost?", "Serverless cost estimation?",
            "Container cost optimization?", "CI/CD cost reduction?",
            "Monitoring cost management?", "Log storage cost?",
            "Backup cost strategy?", "Disaster recovery cost?",
            "License cost optimization?", "SaaS cost management?",
            "Team tooling budget?", "Development environment cost?",
            "Testing infrastructure cost?", "Staging environment cost?",
            "Production environment cost?", "Cost forecasting model?",
            "Cost anomaly detection?", "Idle resource cleanup?",
            "Auto-shutdown policies?", "Cost governance framework?",
            "Chargeback model design?", "FinOps implementation?",
            "Cost optimization roadmap?", "Budget alert configuration?",
            "Cost reporting dashboard?", "ROI calculation framework?",
        ]),
        # Code domain (40 scenarios)
        ("code", [
            "Refactor authentication module?", "Implement caching layer?",
            "Code review best practices?", "Design pattern selection?",
            "API versioning strategy?", "Error handling architecture?",
            "Test coverage improvement?", "Code splitting approach?",
            "Dependency management?", "Code generation strategy?",
            "Monolith to microservices?", "State management pattern?",
            "Database schema design?", "API rate limiting?",
            "Input validation strategy?", "Logging architecture?",
            "Configuration management?", "Feature toggle design?",
            "Event sourcing approach?", "CQRS implementation?",
            "GraphQL schema design?", "REST API design?",
            "WebSocket implementation?", "Background job processing?",
            "File upload handling?", "Search implementation?",
            "Notification system design?", "Permission system design?",
            "Audit logging approach?", "Data migration strategy?",
            "Cache invalidation pattern?", "Circuit breaker implementation?",
            "Retry strategy design?", "Idempotency implementation?",
            "Pagination design?", "Bulk operation handling?",
            "Webhook implementation?", "Plugin architecture?",
            "Multi-tenancy design?", "Internationalization approach?",
        ]),
    ]

    for domain_name, queries in domains:
        for query in queries:
            complexity = random.uniform(0.4, 1.0)
            risk = random.uniform(0.3, 0.9)

            # Adjust based on domain
            if domain_name == "deploy":
                risk = max(risk, 0.6)
            elif domain_name in ("trade", "cost"):
                risk = max(risk, 0.5)
            elif domain_name == "debug":
                complexity = max(complexity, 0.6)

            scenarios.append({
                "query": query,
                "domain": domain_name,
                "query_complexity": round(complexity, 3),
                "domain_risk": round(risk, 3),
                "memory_recall_hits": random.randint(0, 10),
                "metacog_history": random.randint(50, 100),
            })

    return scenarios


# Global seed data
SEED_SCENARIOS = generate_seed_scenarios()


# ============================================================
# MCTSExplorationEnv - Gymnasium environment
# ============================================================
class MCTSExplorationEnv(gym.Env):
    """
    Gymnasium environment for MCTS pre-answer reasoning.

    Observation: [query_complexity, domain_risk, memory_recall_hits, metacog_history]
    Actions: explore_8branches, explore_16branches, critique_nl, merge_top3, converge_final

    Reward: 0.4*reasoning_accuracy + 0.3*exploration_diversity + 0.3*(1-answer_regret)
    """

    metadata = {"render_modes": ["human", "ansi"]}

    def __init__(self, render_mode: Optional[str] = None):
        super().__init__()

        self.render_mode = render_mode

        # Observation space: [query_complexity(0-1), domain_risk(0-1),
        #                     memory_recall_hits(0-10), metacog_history(0-100)]
        self.observation_space = spaces.Box(
            low=np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32),
            high=np.array([1.0, 1.0, 10.0, 100.0], dtype=np.float32),
            dtype=np.float32,
        )

        # Action space: 5 discrete actions
        self.action_space = spaces.Discrete(5)

        # Internal state
        self.current_obs: Optional[np.ndarray] = None
        self.mcts_root: Optional[MCTSNode] = None
        self.query_context: Dict = {}
        self.step_count: int = 0
        self.max_steps: int = 10
        self.branches_explored: int = 0
        self.reasoning_paths: List[str] = []
        self.actions_taken: List[int] = []
        self.done: bool = False

        # Episode stats
        self.episode_stats: Dict = {
            "branches_explored": 0,
            "regret_minimized": 0.0,
            "metacog_score": 0.0,
            "reasoning_accuracy": 0.0,
            "exploration_diversity": 0.0,
            "answer_regret": 0.0,
        }

        # Scenario pool
        self.scenarios = SEED_SCENARIOS
        self.scenario_idx = 0

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict] = None,
        query: Optional[str] = None,
    ) -> Tuple[np.ndarray, Dict]:
        """Reset environment for a new episode."""
        super().reset(seed=seed)

        if query is not None:
            # Parse query to extract observation
            self.query_context = self._parse_query(query)
        elif options and "scenario" in options:
            self.query_context = options["scenario"]
        else:
            # Pick next scenario from seed pool
            self.query_context = self.scenarios[self.scenario_idx % len(self.scenarios)]
            self.scenario_idx += 1

        # Build observation
        self.current_obs = np.array([
            self.query_context.get("query_complexity", 0.5),
            self.query_context.get("domain_risk", 0.5),
            float(self.query_context.get("memory_recall_hits", 0)),
            float(self.query_context.get("metacog_history", 50)),
        ], dtype=np.float32)

        # Initialize MCTS tree
        self.mcts_root = MCTSNode(
            state={
                "query": self.query_context.get("query", ""),
                "complexity": self.current_obs[0],
                "risk": self.current_obs[1],
            }
        )

        # Reset counters
        self.step_count = 0
        self.branches_explored = 0
        self.reasoning_paths = []
        self.actions_taken = []
        self.done = False
        self.episode_stats = {
            "branches_explored": 0,
            "regret_minimized": 0.0,
            "metacog_score": 0.0,
            "reasoning_accuracy": 0.0,
            "exploration_diversity": 0.0,
            "answer_regret": 0.0,
        }

        info = {
            "query": self.query_context.get("query", ""),
            "domain": self.query_context.get("domain", "unknown"),
            "auto_fire": self._should_auto_fire(),
        }

        return self.current_obs, info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """Execute one reasoning step."""
        if self.done:
            return self.current_obs, 0.0, True, False, self.episode_stats

        self.step_count += 1
        self.actions_taken.append(action)
        action_name = ACTION_NAMES.get(action, "unknown")

        # Execute action
        if action == ACTION_EXPLORE_8:
            self._expand_branches(8)
        elif action == ACTION_EXPLORE_16:
            self._expand_branches(16)
        elif action == ACTION_CRITIQUE_NL:
            self._critique_branches()
        elif action == ACTION_MERGE_TOP3:
            self._merge_top_branches(3)
        elif action == ACTION_CONVERGE_FINAL:
            self.done = True

        # Run MCTS simulations after each action
        if not self.done and self.mcts_root and self.mcts_root.children:
            self._run_simulations(min(NUM_SIMULATIONS, 10 + self.step_count * 5))

        # Update observation based on exploration progress
        exploration_progress = min(1.0, self.branches_explored / 16.0)
        self.current_obs = np.array([
            self.query_context.get("query_complexity", 0.5),
            self.query_context.get("domain_risk", 0.5),
            float(min(10, self.query_context.get("memory_recall_hits", 0) + self.branches_explored)),
            float(min(100, self.query_context.get("metacog_history", 50) + exploration_progress * 20)),
        ], dtype=np.float32)

        # Calculate reward
        reward = self._calculate_reward()

        # Check termination
        terminated = self.done or self.step_count >= self.max_steps
        truncated = self.step_count >= self.max_steps and not self.done

        if terminated or truncated:
            self.done = True
            self._finalize_episode_stats()

        info = {
            **self.episode_stats,
            "step": self.step_count,
            "action": action_name,
            "branches_explored": self.branches_explored,
        }

        return self.current_obs, reward, terminated, truncated, info

    def render(self) -> Optional[str]:
        """Render the MCTS tree structure."""
        if self.mcts_root is None:
            return None

        lines = []
        lines.append(f"=== MCTS Exploration Tree ===")
        lines.append(f"Query: {self.query_context.get('query', 'N/A')}")
        lines.append(f"Steps: {self.step_count} | Branches: {self.branches_explored}")
        lines.append(f"Metacog: {self.episode_stats.get('metacog_score', 0):.0f}/100")
        lines.append("")

        self._render_node(self.mcts_root, lines, prefix="", is_last=True)

        output = "\n".join(lines)
        if self.render_mode == "human":
            print(output)
        return output

    def _render_node(self, node: MCTSNode, lines: List[str], prefix: str, is_last: bool):
        """Recursively render a tree node."""
        connector = "`-- " if is_last else "|-- "
        action_str = ACTION_NAMES.get(node.action_taken, "root") if node.action_taken is not None else "root"
        ucb_str = f"UCB1={node.ucb1():.3f}" if node.visits > 0 else "unvisited"
        visit_str = f"v={node.visits}" if node.visits > 0 else ""
        reward_str = f"r={node.exploit_score:.3f}" if node.visits > 0 else ""

        label = f"{action_str} [{ucb_str} {visit_str} {reward_str}]".strip()
        if node.reasoning_path:
            label += f" \"{node.reasoning_path[:40]}...\""

        lines.append(f"{prefix}{connector}{label}")

        child_prefix = prefix + ("    " if is_last else "|   ")
        for i, child in enumerate(node.children):
            self._render_node(child, lines, child_prefix, i == len(node.children) - 1)

    # ============================================================
    # MCTS Core: Selection, Expansion, Simulation, Backpropagation
    # ============================================================

    def _run_simulations(self, num_sims: int):
        """Run full MCTS loop: select -> expand -> simulate -> backpropagate."""
        for _ in range(num_sims):
            # Selection: traverse tree using UCB1
            node = self._select(self.mcts_root)

            # Expansion: add a child if not terminal
            if not node.is_terminal() and node.visits > 0:
                node = self._expand(node)

            # Simulation: rollout from node
            reward = self._simulate(node)

            # Backpropagation: update ancestors
            self._backpropagate(node, reward)

    def _select(self, node: MCTSNode) -> MCTSNode:
        """Select leaf node by traversing tree with UCB1."""
        while not node.is_leaf() and not node.is_terminal():
            node = node.best_child(EXPLORATION_CONSTANT)
        return node

    def _expand(self, node: MCTSNode) -> MCTSNode:
        """Expand a node by adding one child with a random action."""
        # Pick an action not yet tried
        tried_actions = {c.action_taken for c in node.children}
        untried = [a for a in range(5) if a not in tried_actions]

        if not untried:
            # All actions tried, return existing child
            return node.best_child(EXPLORATION_CONSTANT) if node.children else node

        action = random.choice(untried)
        reasoning = self._generate_reasoning_path(node, action)

        child_state = {
            **node.state,
            "depth": node.depth + 1,
            "last_action": ACTION_NAMES[action],
        }

        child = node.add_child(child_state, action, reasoning)
        return child

    def _simulate(self, node: MCTSNode) -> float:
        """Simulate a rollout from node, return quality score 0-1."""
        return simulate_branch(node, self.query_context)

    def _backpropagate(self, node: MCTSNode, reward: float):
        """Backpropagate reward up to root."""
        while node is not None:
            node.visits += 1
            node.total_reward += reward
            node = node.parent

    # ============================================================
    # Action implementations
    # ============================================================

    def _expand_branches(self, num_branches: int):
        """Expand N reasoning branches from root."""
        for _ in range(num_branches):
            if self.mcts_root.is_terminal():
                break
            action = random.randint(0, 4)
            reasoning = self._generate_reasoning_path(self.mcts_root, action)
            child_state = {
                **self.mcts_root.state,
                "depth": 1,
                "last_action": ACTION_NAMES[action],
            }
            child = self.mcts_root.add_child(child_state, action, reasoning)
            # Simulate each branch
            reward = simulate_branch(child, self.query_context)
            self._backpropagate(child, reward)

        self.branches_explored += num_branches
        self.episode_stats["branches_explored"] = self.branches_explored

    def _critique_branches(self):
        """NL critique of existing branches."""
        if not self.mcts_root.children:
            return

        # Sort children by exploit score
        sorted_children = sorted(
            self.mcts_root.children,
            key=lambda c: c.exploit_score,
            reverse=True,
        )

        critiques = []
        for i, child in enumerate(sorted_children[:5]):
            action_name = ACTION_NAMES.get(child.action_taken, "?")
            score = child.exploit_score
            visits = child.visits

            if i == 0:
                critiques.append(
                    f"Branch {action_name} strongest (score={score:.3f}, v={visits}): "
                    f"Best exploration-exploitation balance"
                )
            else:
                regret = sorted_children[0].exploit_score - score
                critiques.append(
                    f"Branch {action_name} has regret {regret:.3f}: "
                    f"Lower reasoning quality (score={score:.3f})"
                )

        self.reasoning_paths.extend(critiques)

    def _merge_top_branches(self, n: int):
        """Merge top-N branches into unified reasoning context."""
        if not self.mcts_root.children:
            return

        sorted_children = sorted(
            self.mcts_root.children,
            key=lambda c: c.exploit_score,
            reverse=True,
        )

        top_n = sorted_children[:n]
        merged_reasoning = []
        for child in top_n:
            merged_reasoning.append(child.reasoning_path)

        self.reasoning_paths.append(
            f"[MERGED] Top-{n} branches combined: "
            + " | ".join(merged_reasoning[:3])
        )

    # ============================================================
    # Reward calculation
    # ============================================================

    def _calculate_reward(self) -> float:
        """
        Reward = 0.4 * reasoning_accuracy
               + 0.3 * exploration_diversity
               + 0.3 * (1 - answer_regret)
        """
        reasoning_accuracy = self._compute_reasoning_accuracy()
        exploration_diversity = self._compute_exploration_diversity()
        answer_regret = self._compute_answer_regret()

        reward = (
            0.4 * reasoning_accuracy
            + 0.3 * exploration_diversity
            + 0.3 * (1.0 - answer_regret)
        )

        self.episode_stats["reasoning_accuracy"] = reasoning_accuracy
        self.episode_stats["exploration_diversity"] = exploration_diversity
        self.episode_stats["answer_regret"] = answer_regret

        return reward

    def _compute_reasoning_accuracy(self) -> float:
        """Estimate reasoning accuracy from MCTS tree quality."""
        if not self.mcts_root or not self.mcts_root.children:
            return 0.0

        best_child = max(self.mcts_root.children, key=lambda c: c.exploit_score)
        accuracy = best_child.exploit_score

        # Boost if we've done critique and merge
        if ACTION_CRITIQUE_NL in self.actions_taken:
            accuracy = min(1.0, accuracy * 1.1)
        if ACTION_MERGE_TOP3 in self.actions_taken:
            accuracy = min(1.0, accuracy * 1.05)

        return min(1.0, accuracy)

    def _compute_exploration_diversity(self) -> float:
        """Measure how diverse the explored branches are."""
        if self.branches_explored == 0:
            return 0.0

        unique_actions = len(set(self.actions_taken))
        action_diversity = unique_actions / 5.0

        branch_diversity = min(1.0, self.branches_explored / 16.0)

        return 0.5 * action_diversity + 0.5 * branch_diversity

    def _compute_answer_regret(self) -> float:
        """Compute answer regret: difference between best and chosen path."""
        if not self.mcts_root or not self.mcts_root.children:
            return 1.0  # Max regret if no exploration

        scores = [c.exploit_score for c in self.mcts_root.children if c.visits > 0]
        if not scores:
            return 1.0

        best_score = max(scores)
        avg_score = sum(scores) / len(scores)

        # Regret = gap between best and average (normalized)
        regret = best_score - avg_score
        return min(1.0, max(0.0, regret))

    def _finalize_episode_stats(self):
        """Compute final episode statistics."""
        self.episode_stats["branches_explored"] = self.branches_explored

        # Regret minimized: improvement from initial to final
        initial_regret = 1.0
        final_regret = self.episode_stats.get("answer_regret", 1.0)
        regret_reduction = (initial_regret - final_regret) * 100
        self.episode_stats["regret_minimized"] = round(regret_reduction, 1)

        # Metacog score: composite of accuracy and diversity
        accuracy = self.episode_stats.get("reasoning_accuracy", 0.0)
        diversity = self.episode_stats.get("exploration_diversity", 0.0)
        metacog = (0.6 * accuracy + 0.4 * diversity) * 100
        self.episode_stats["metacog_score"] = round(min(100, metacog), 1)

    # ============================================================
    # Helpers
    # ============================================================

    def _parse_query(self, query: str) -> Dict:
        """Parse a natural language query into observation components."""
        query_lower = query.lower()
        context = {
            "query": query,
            "query_complexity": 0.5,
            "domain_risk": 0.3,
            "memory_recall_hits": 0,
            "metacog_history": 50,
            "domain": "general",
        }

        for keyword, values in DOMAIN_KEYWORDS.items():
            if keyword in query_lower:
                for k, v in values.items():
                    if k in ("query_complexity", "domain_risk"):
                        context[k] = max(context[k], v)
                    elif k == "domain":
                        context[k] = v

        # Question complexity heuristic
        if "?" in query:
            context["query_complexity"] = max(context["query_complexity"], 0.55)
        word_count = len(query.split())
        if word_count > 8:
            context["query_complexity"] = max(context["query_complexity"], 0.65)

        return context

    def _should_auto_fire(self) -> bool:
        """Check if MCTS should auto-fire based on observation."""
        if self.current_obs is None:
            return False
        query_complexity = self.current_obs[0]
        domain_risk = self.current_obs[1]
        return query_complexity > 0.6 or domain_risk > 0.5

    def _generate_reasoning_path(self, node: MCTSNode, action: int) -> str:
        """Generate a natural language reasoning path for a branch."""
        query = self.query_context.get("query", "unknown query")
        domain = self.query_context.get("domain", "general")
        action_name = ACTION_NAMES.get(action, "unknown")

        # Deterministic but varied reasoning based on action and domain
        seed = hashlib.md5(f"{query}{action}{node.depth}{random.random()}".encode()).hexdigest()

        templates = {
            ACTION_EXPLORE_8: [
                f"Exploring 8 parallel reasoning paths for {domain} domain",
                f"Branching into 8 alternative approaches to {query[:30]}",
                f"Generating 8 diverse perspectives on {domain} problem",
            ],
            ACTION_EXPLORE_16: [
                f"Deep exploration: 16 branches for complex {domain} scenario",
                f"Exhaustive search across 16 reasoning paths",
                f"Maximum breadth exploration for {query[:30]}",
            ],
            ACTION_CRITIQUE_NL: [
                f"Critiquing existing branches for logical consistency",
                f"Evaluating reasoning quality across explored paths",
                f"Identifying weaknesses and regret in current branches",
            ],
            ACTION_MERGE_TOP3: [
                f"Merging strongest 3 branches into unified context",
                f"Synthesizing top reasoning paths for {domain}",
                f"Combining complementary insights from best branches",
            ],
            ACTION_CONVERGE_FINAL: [
                f"Converging on final answer with minimal regret",
                f"Final convergence: selecting optimal path for {domain}",
                f"Committing to best-explored reasoning path",
            ],
        }

        options = templates.get(action, [f"Action {action_name} at depth {node.depth}"])
        idx = int(seed[:4], 16) % len(options)
        return options[idx]


def simulate_branch(node: MCTSNode, query_context: Dict) -> float:
    """
    Simulate a reasoning branch and return quality score 0-1.

    Scores based on:
    - Domain alignment (does action match domain needs?)
    - Depth appropriateness (deeper exploration for complex queries)
    - Action sequence quality
    """
    complexity = query_context.get("query_complexity", 0.5)
    risk = query_context.get("domain_risk", 0.5)
    action = node.action_taken if node.action_taken is not None else 0
    depth = node.depth

    # Base score from action-domain alignment
    base_score = 0.5

    # Exploration actions score higher for complex/risky queries
    if action in (ACTION_EXPLORE_8, ACTION_EXPLORE_16):
        base_score += 0.15 * complexity + 0.1 * risk
        if action == ACTION_EXPLORE_16 and complexity > 0.7:
            base_score += 0.1  # Bonus for deep exploration on complex queries

    # Critique scores well after exploration
    if action == ACTION_CRITIQUE_NL and depth > 1:
        base_score += 0.2

    # Merge scores well after sufficient exploration
    if action == ACTION_MERGE_TOP3 and depth >= 2:
        base_score += 0.15

    # Convergence: good at deep depth, penalized if too early
    if action == ACTION_CONVERGE_FINAL:
        if depth >= 3:
            base_score += 0.25
        elif depth <= 1:
            base_score -= 0.2

    # Depth bonus (deeper exploration generally better for complex queries)
    depth_bonus = min(0.15, depth * 0.05 * complexity)
    base_score += depth_bonus

    # Add controlled randomness for simulation variance
    noise = random.gauss(0, 0.08)
    score = max(0.0, min(1.0, base_score + noise))

    return score


# ============================================================
# Convenience: quick test
# ============================================================
if __name__ == "__main__":
    env = MCTSExplorationEnv(render_mode="human")

    # Test with query
    obs, info = env.reset(query="Optimal Render deploy?")
    print(f"Initial obs: {obs}")
    print(f"Auto-fire: {info['auto_fire']}")
    print(f"Domain: {info['domain']}")
    print()

    # Run episode
    actions = [ACTION_EXPLORE_8, ACTION_EXPLORE_16, ACTION_CRITIQUE_NL, ACTION_MERGE_TOP3, ACTION_CONVERGE_FINAL]
    total_reward = 0.0
    for a in actions:
        obs, reward, terminated, truncated, info = env.step(a)
        total_reward += reward
        print(f"Action: {ACTION_NAMES[a]} | Reward: {reward:.3f} | Branches: {info['branches_explored']}")
        if terminated or truncated:
            break

    print()
    env.render()
    print()

    regret_pct = info.get("regret_minimized", 0)
    metacog = info.get("metacog_score", 0)
    best_action = ACTION_NAMES.get(
        max(range(5), key=lambda a: sum(1 for x in env.actions_taken if x == a)),
        "explore_8branches"
    )
    print(
        f"[MCTS] Explored {info['branches_explored']} paths -> "
        f"Selected {best_action} (min regret +{regret_pct}%) "
        f"[Metacog {metacog}/100]"
    )
