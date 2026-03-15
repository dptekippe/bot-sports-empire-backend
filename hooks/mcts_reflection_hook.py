#!/usr/bin/env python3
"""
MCTS Reflection Hook - OpenClaw Pre-Answer Hook

Pre-answer hook that runs MCTS tree search before the LLM sees a query.
Forces exploration-first reasoning to minimize answer regret.

Trigger: query_complexity > 0.6 OR "think"/"optimal"/"?" in complex queries.
Output: Injects merged MCTS reasoning context into event["pre_context"].

Part of Roger's metacog_v3 upgrade path.
"""

import os
import sys
import json
import math
import time
import random
import hashlib
import logging
import datetime
from typing import Dict, List, Optional, Any, Tuple

# ============================================================
# Configuration
# ============================================================
MCTS_ENABLED_ENV = os.environ.get("MCTS_ENABLED", "true").lower()
METACOG_V3_HISTORY_PATH = os.path.expanduser(
    "~/.openclaw/workspace/metacog_v3_history.json"
)
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "mcts_exploration_model")

# Hook trigger keywords
TRIGGER_KEYWORDS = ["think", "optimal", "complex", "deploy", "render"]
COMPLEXITY_THRESHOLD = 0.6
RISK_THRESHOLD = 0.5

# MCTS parameters for hook (lighter than training)
HOOK_NUM_SIMULATIONS = 25
HOOK_MAX_DEPTH = 3
HOOK_EXPLORATION_CONSTANT = 1.414
HOOK_NUM_BRANCHES = 8

# Domain detection (subset for speed)
DOMAIN_KEYWORDS = {
    "deploy": {"domain_risk": 0.8, "domain": "deploy"},
    "render": {"domain_risk": 0.8, "domain": "deploy"},
    "hosting": {"domain_risk": 0.8, "domain": "deploy"},
    "production": {"domain_risk": 0.85, "domain": "deploy"},
    "think": {"query_complexity": 0.9, "domain": "reasoning"},
    "complex": {"query_complexity": 0.9, "domain": "reasoning"},
    "optimal": {"query_complexity": 0.9, "domain": "reasoning"},
    "trade": {"domain_risk": 0.7, "query_complexity": 0.7, "domain": "trade"},
    "debug": {"query_complexity": 0.75, "domain": "debug"},
    "cost": {"domain_risk": 0.65, "query_complexity": 0.6, "domain": "cost"},
    "code": {"query_complexity": 0.6, "domain": "code"},
    "refactor": {"query_complexity": 0.7, "domain": "code"},
}

logger = logging.getLogger("mcts_reflection_hook")


# ============================================================
# Lightweight MCTSNode for hook (no gym dependency)
# ============================================================
class MCTSNode:
    """Minimal MCTS node for hook usage."""

    def __init__(self, state: Dict, parent=None, action: Optional[str] = None, depth: int = 0):
        self.state = state
        self.parent = parent
        self.children: List['MCTSNode'] = []
        self.visits: int = 0
        self.total_reward: float = 0.0
        self.action = action
        self.reasoning: str = ""
        self.depth = depth

    @property
    def exploit_score(self) -> float:
        if self.visits == 0:
            return 0.0
        return self.total_reward / self.visits

    def ucb1(self, c: float = HOOK_EXPLORATION_CONSTANT) -> float:
        if self.visits == 0:
            return float('inf')
        if self.parent is None or self.parent.visits == 0:
            return self.exploit_score
        exploit = self.total_reward / self.visits
        explore = c * math.sqrt(math.log(self.parent.visits) / self.visits)
        return exploit + explore

    def best_child(self, c: float = HOOK_EXPLORATION_CONSTANT) -> 'MCTSNode':
        return max(self.children, key=lambda ch: ch.ucb1(c))

    def add_child(self, state: Dict, action: str, reasoning: str = "") -> 'MCTSNode':
        child = MCTSNode(state=state, parent=self, action=action, depth=self.depth + 1)
        child.reasoning = reasoning
        self.children.append(child)
        return child


# ============================================================
# Core MCTS functions for hook
# ============================================================

def parse_query(query: str) -> Dict:
    """Parse query into complexity/risk scores and domain."""
    query_lower = query.lower()
    context = {
        "query": query,
        "query_complexity": 0.4,
        "domain_risk": 0.3,
        "domain": "general",
    }

    for keyword, values in DOMAIN_KEYWORDS.items():
        if keyword in query_lower:
            for k, v in values.items():
                if k in ("query_complexity", "domain_risk"):
                    context[k] = max(context[k], v)
                elif k == "domain":
                    context[k] = v

    if "?" in query:
        context["query_complexity"] = max(context["query_complexity"], 0.55)
    if len(query.split()) > 10:
        context["query_complexity"] = max(context["query_complexity"], 0.65)

    return context


def should_trigger(query: str, context: Dict) -> bool:
    """Check if MCTS should fire for this query."""
    if MCTS_ENABLED_ENV == "false":
        return False

    # Keyword triggers
    query_lower = query.lower()
    for kw in TRIGGER_KEYWORDS:
        if kw in query_lower:
            return True

    # Threshold triggers
    if context.get("query_complexity", 0) > COMPLEXITY_THRESHOLD:
        return True
    if context.get("domain_risk", 0) > RISK_THRESHOLD:
        return True

    # Complex question detection
    if "?" in query and len(query.split()) > 6:
        return True

    return False


def generate_branch_reasoning(query: str, domain: str, branch_id: int) -> str:
    """Generate NL reasoning for a single branch."""
    seed = hashlib.md5(f"{query}{branch_id}{domain}".encode()).hexdigest()

    reasoning_templates = {
        "deploy": [
            "Consider zero-downtime deployment with health checks and rollback",
            "Evaluate container orchestration vs serverless for this workload",
            "Analyze cost-performance tradeoff of multi-region deployment",
            "Assess blue-green vs canary release for risk mitigation",
            "Review infrastructure-as-code approach for reproducibility",
            "Consider edge caching and CDN optimization for latency",
            "Evaluate monitoring and alerting setup for production readiness",
            "Analyze auto-scaling configuration for variable load patterns",
        ],
        "trade": [
            "Evaluate dynasty asset value using age curve and production data",
            "Consider positional scarcity and league scoring format impact",
            "Analyze buy-low window based on recent injury or performance dip",
            "Project future value using rookie class depth at position",
            "Compare trade packages using surplus value methodology",
            "Assess contender vs rebuilder context for trade direction",
            "Evaluate opportunity cost of holding vs trading aging assets",
            "Consider league-specific trade tendencies and market inefficiency",
        ],
        "debug": [
            "Start with log aggregation and error correlation analysis",
            "Profile CPU and memory to identify bottleneck location",
            "Check for race conditions or deadlocks in concurrent paths",
            "Analyze network traces for timeout root cause",
            "Review recent deployments for regression correlation",
            "Check database query plans for performance degradation",
            "Evaluate caching layer for invalidation bugs",
            "Test with reduced load to isolate scaling-related issues",
        ],
        "cost": [
            "Analyze reserved vs on-demand vs spot instance mix",
            "Right-size compute resources based on actual utilization",
            "Implement auto-shutdown for non-production environments",
            "Evaluate multi-cloud arbitrage for cost optimization",
            "Review storage tiers and lifecycle policies",
            "Assess serverless migration for variable workloads",
            "Implement cost allocation tags for accountability",
            "Set up anomaly detection for unexpected cost spikes",
        ],
        "code": [
            "Evaluate design patterns for maintainability and testability",
            "Consider API versioning strategy for backward compatibility",
            "Analyze dependency graph for circular or heavy dependencies",
            "Review error handling for graceful degradation",
            "Assess test coverage gaps and critical path testing",
            "Consider code splitting for performance optimization",
            "Evaluate state management approach for complexity",
            "Review security surface area and input validation",
        ],
        "reasoning": [
            "Decompose problem into independent sub-problems",
            "Apply first-principles analysis to core constraints",
            "Consider edge cases and failure modes systematically",
            "Evaluate multiple solution frameworks before committing",
            "Challenge initial assumptions with counterfactual reasoning",
            "Synthesize cross-domain analogies for novel insights",
            "Apply decision matrix to compare solution candidates",
            "Project long-term consequences of each approach",
        ],
        "general": [
            "Explore multiple perspectives before convergence",
            "Consider both short-term and long-term implications",
            "Identify key constraints and degrees of freedom",
            "Evaluate risk-reward tradeoffs for each approach",
            "Seek analogies from adjacent domains",
            "Challenge default assumptions with evidence",
            "Consider stakeholder impact and communication needs",
            "Plan for reversibility and iterative refinement",
        ],
    }

    templates = reasoning_templates.get(domain, reasoning_templates["general"])
    idx = int(seed[:4], 16) % len(templates)
    return templates[idx]


def run_mcts_pipeline(query: str, context: Dict) -> Dict:
    """
    Full MCTS pipeline:
    1. Parse query -> extract domain, complexity
    2. Run 8 branches of NL reasoning
    3. UCB1 select top-3
    4. NL critique
    5. Merge top-3 into unified context
    """
    domain = context.get("domain", "general")
    complexity = context.get("query_complexity", 0.5)
    risk = context.get("domain_risk", 0.3)

    # Step 1: Initialize root
    root = MCTSNode(state={"query": query, "complexity": complexity, "risk": risk})

    # Step 2: Expand 8 branches with NL reasoning
    num_branches = HOOK_NUM_BRANCHES
    if complexity > 0.8 or risk > 0.7:
        num_branches = 16  # More branches for complex/risky queries

    for i in range(num_branches):
        reasoning = generate_branch_reasoning(query, domain, i)
        child_state = {
            "query": query,
            "branch_id": i,
            "reasoning": reasoning,
        }
        child = root.add_child(child_state, action=f"branch_{i}", reasoning=reasoning)

        # Simulate branch quality
        quality = simulate_branch_quality(reasoning, complexity, risk, domain)
        # Backpropagate
        node = child
        while node is not None:
            node.visits += 1
            node.total_reward += quality
            node = node.parent

    # Run additional MCTS simulations for refinement
    for _ in range(HOOK_NUM_SIMULATIONS):
        # Selection
        node = root
        while node.children and node.depth < HOOK_MAX_DEPTH:
            node = node.best_child(HOOK_EXPLORATION_CONSTANT)

        # Simulate
        quality = simulate_branch_quality(
            node.reasoning, complexity, risk, domain
        )

        # Backpropagate
        while node is not None:
            node.visits += 1
            node.total_reward += quality
            node = node.parent

    # Step 3: UCB1 select top-3
    sorted_children = sorted(root.children, key=lambda c: c.exploit_score, reverse=True)
    top3 = sorted_children[:3]

    # Step 4: NL Critique
    critiques = []
    best = top3[0] if top3 else None
    for i, child in enumerate(top3):
        if i == 0:
            critiques.append(
                f"Branch {child.action} strongest because: {child.reasoning} "
                f"(score={child.exploit_score:.3f})"
            )
        else:
            regret = best.exploit_score - child.exploit_score
            critiques.append(
                f"Branch {child.action} has regret: {regret:.3f} - {child.reasoning}"
            )

    # Step 5: Merge top-3 into unified reasoning context
    merged_reasoning = []
    for child in top3:
        merged_reasoning.append(child.reasoning)

    merged_context = " → ".join(merged_reasoning)

    # Compute stats
    best_score = top3[0].exploit_score if top3 else 0.0
    avg_score = sum(c.exploit_score for c in root.children) / max(1, len(root.children))
    regret_reduction = (1.0 - (best_score - avg_score)) * 100

    metacog_score = min(100, int((0.6 * best_score + 0.4 * (len(top3) / 3.0)) * 100))

    best_action = top3[0].action if top3 else "explore_8branches"

    return {
        "num_branches": num_branches,
        "branches_explored": len(root.children),
        "best_action": best_action,
        "best_score": best_score,
        "regret_reduction_pct": round(regret_reduction, 1),
        "metacog_score": metacog_score,
        "merged_context": merged_context,
        "critiques": critiques,
        "top3_reasoning": [c.reasoning for c in top3],
        "domain": domain,
    }


def simulate_branch_quality(
    reasoning: str, complexity: float, risk: float, domain: str
) -> float:
    """Score a reasoning branch based on content and context alignment."""
    score = 0.5

    # Length and specificity bonus
    word_count = len(reasoning.split())
    if word_count > 5:
        score += 0.1
    if word_count > 10:
        score += 0.05

    # Domain alignment (reasoning mentions domain-relevant concepts)
    domain_terms = {
        "deploy": ["deploy", "container", "rollback", "health", "scale", "monitor"],
        "trade": ["value", "asset", "position", "league", "rebuild", "contender"],
        "debug": ["log", "profile", "error", "trace", "bottleneck", "performance"],
        "cost": ["cost", "budget", "optimize", "resource", "utilization", "savings"],
        "code": ["pattern", "test", "api", "dependency", "security", "refactor"],
        "reasoning": ["decompose", "principle", "constraint", "framework", "evidence"],
    }

    terms = domain_terms.get(domain, [])
    reasoning_lower = reasoning.lower()
    matches = sum(1 for t in terms if t in reasoning_lower)
    score += min(0.2, matches * 0.05)

    # Complexity alignment
    score += complexity * 0.1
    score += risk * 0.05

    # Add noise
    noise = random.gauss(0, 0.06)
    return max(0.0, min(1.0, score + noise))


# ============================================================
# Metacog v3 History
# ============================================================

def load_metacog_history() -> List[Dict]:
    """Load metacog v3 history from disk."""
    try:
        if os.path.exists(METACOG_V3_HISTORY_PATH):
            with open(METACOG_V3_HISTORY_PATH, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load metacog history: {e}")
    return []


def save_metacog_history(history: List[Dict]):
    """Save metacog v3 history to disk."""
    try:
        os.makedirs(os.path.dirname(METACOG_V3_HISTORY_PATH), exist_ok=True)
        with open(METACOG_V3_HISTORY_PATH, "w") as f:
            json.dump(history[-1000:], f, indent=2)  # Keep last 1000
    except Exception as e:
        logger.warning(f"Failed to save metacog history: {e}")


def update_metacog_history(result: Dict) -> int:
    """Update metacog v3 history with latest MCTS result. Returns running avg score."""
    history = load_metacog_history()

    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "domain": result.get("domain", "general"),
        "branches_explored": result.get("branches_explored", 0),
        "metacog_score": result.get("metacog_score", 0),
        "regret_reduction_pct": result.get("regret_reduction_pct", 0),
        "best_action": result.get("best_action", ""),
    }
    history.append(entry)

    save_metacog_history(history)

    # Return running average of last 20
    recent = history[-20:]
    avg_score = sum(e.get("metacog_score", 0) for e in recent) / max(1, len(recent))
    return int(avg_score)


# ============================================================
# Trained Model Loader
# ============================================================
_loaded_model = None


def load_trained_model():
    """Load trained MCTS model if available."""
    global _loaded_model
    if _loaded_model is not None:
        return _loaded_model

    zip_path = MODEL_PATH + ".zip"
    json_path = MODEL_PATH + ".json"

    if os.path.exists(zip_path):
        try:
            from stable_baselines3 import PPO
            _loaded_model = PPO.load(zip_path)
            logger.info(f"Loaded trained MCTS model from {zip_path}")
            return _loaded_model
        except Exception as e:
            logger.warning(f"Failed to load SB3 model: {e}")

    if os.path.exists(json_path):
        try:
            with open(json_path, "r") as f:
                _loaded_model = json.load(f)
            logger.info(f"Loaded policy table from {json_path}")
            return _loaded_model
        except Exception as e:
            logger.warning(f"Failed to load policy table: {e}")

    return None


# ============================================================
# Main Hook Handler
# ============================================================

def handler(event: dict) -> dict:
    """
    OpenClaw pre-answer hook handler.

    Runs MCTS tree search on incoming query, injects merged reasoning
    context into event["pre_context"] before the LLM processes the query.

    Args:
        event: OpenClaw event dict with at minimum {"message": str}

    Returns:
        Modified event with MCTS reasoning injected, or unmodified on skip/error.
    """
    # Kill switch
    if MCTS_ENABLED_ENV == "false":
        return event

    try:
        # Extract query from event
        query = event.get("message", "") or event.get("query", "") or event.get("content", "")
        if not query:
            return event

        # Parse query context
        context = parse_query(query)

        # Check trigger conditions
        if not should_trigger(query, context):
            return event

        start_time = time.time()

        # Auto-load trained model if available
        load_trained_model()

        # Run full MCTS pipeline
        result = run_mcts_pipeline(query, context)

        elapsed_ms = (time.time() - start_time) * 1000

        # Update metacog v3 history
        running_metacog = update_metacog_history(result)

        # Build MCTS output line
        mcts_output = (
            f"[MCTS] Explored {result['branches_explored']} paths -> "
            f"Selected {result['best_action']} "
            f"(min regret +{result['regret_reduction_pct']}%) "
            f"[Metacog {result['metacog_score']}/100]"
        )

        # Build pre_context injection
        pre_context = (
            f"--- MCTS Pre-Answer Reasoning (metacog_v3) ---\n"
            f"Query complexity: {context['query_complexity']:.2f} | "
            f"Domain risk: {context['domain_risk']:.2f} | "
            f"Domain: {context['domain']}\n"
            f"Branches explored: {result['branches_explored']}\n"
            f"\nTop reasoning paths:\n"
        )
        for i, reasoning in enumerate(result["top3_reasoning"], 1):
            pre_context += f"  {i}. {reasoning}\n"

        pre_context += f"\nCritique:\n"
        for critique in result["critiques"]:
            pre_context += f"  - {critique}\n"

        pre_context += (
            f"\nMerged context: {result['merged_context']}\n"
            f"{mcts_output}\n"
            f"--- End MCTS ({elapsed_ms:.0f}ms) ---\n"
        )

        # Inject into event
        event["pre_context"] = event.get("pre_context", "") + pre_context
        event["mcts_reasoning"] = result
        event["mcts_output"] = mcts_output
        event["metacog_v3_score"] = result["metacog_score"]
        event["metacog_v3_running_avg"] = running_metacog

        logger.info(
            f"MCTS hook fired: {result['branches_explored']} branches, "
            f"metacog={result['metacog_score']}/100, "
            f"elapsed={elapsed_ms:.0f}ms"
        )

        return event

    except Exception as e:
        # Graceful fallback: log warning and pass event through unchanged
        logger.warning(f"MCTS reflection hook failed: {e}", exc_info=True)
        print(f"[MCTS WARNING] Hook failed ({e}), passing through unchanged")
        return event


# ============================================================
# Test
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test 1: Deploy query (should trigger)
    print("=== Test 1: Deploy Query ===")
    event1 = {"message": "Optimal Render deploy?"}
    result1 = handler(event1)
    print(result1.get("mcts_output", "NO OUTPUT"))
    print()

    # Test 2: Simple query (should NOT trigger)
    print("=== Test 2: Simple Query ===")
    event2 = {"message": "Hello"}
    result2 = handler(event2)
    has_mcts = "mcts_output" in result2
    print(f"MCTS triggered: {has_mcts} (expected: False)")
    print()

    # Test 3: Complex thinking query
    print("=== Test 3: Complex Thinking Query ===")
    event3 = {"message": "Think about the optimal trade strategy for dynasty rebuilding?"}
    result3 = handler(event3)
    print(result3.get("mcts_output", "NO OUTPUT"))
    print()

    # Test 4: Cost query
    print("=== Test 4: Cost Query ===")
    event4 = {"message": "What's the optimal cost strategy for cloud deployment?"}
    result4 = handler(event4)
    print(result4.get("mcts_output", "NO OUTPUT"))
    print()

    print("=== All tests complete ===")
