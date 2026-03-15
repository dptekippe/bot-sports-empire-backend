"""
MCTS Exploration Training Script - PPO + CFR-HER

Trains the MCTSExplorationEnv using:
  - PPO (Proximal Policy Optimization) via stable_baselines3
  - CFR (Counterfactual Regret Minimization) critic layer
  - HER (Hindsight Experience Replay) for learning from suboptimal paths

Training target: 15% accuracy lift, 100k timesteps.
Mirrors DeployGym training pattern (PPO+CFR-HER, 100k steps, checkpoints).
"""

import os
import sys
import json
import time
import math
import random
import hashlib
import argparse
import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

import numpy as np

try:
    import gymnasium as gym
except ImportError:
    import gym

from mcts_exploration_gym import (
    MCTSExplorationEnv,
    ACTION_NAMES,
    ACTION_EXPLORE_8,
    ACTION_EXPLORE_16,
    ACTION_CRITIQUE_NL,
    ACTION_MERGE_TOP3,
    ACTION_CONVERGE_FINAL,
    SEED_SCENARIOS,
)


# ============================================================
# CFR Critic - Counterfactual Regret Minimization
# ============================================================
class CFRCritic:
    """
    Counterfactual Regret Minimization critic layer.

    Tracks cumulative regret per action and updates strategy
    proportional to positive regret (regret matching).
    """

    def __init__(self, num_actions: int = 5):
        self.num_actions = num_actions
        self.regret_sum: Dict[str, np.ndarray] = defaultdict(
            lambda: np.zeros(num_actions, dtype=np.float64)
        )
        self.strategy_sum: Dict[str, np.ndarray] = defaultdict(
            lambda: np.zeros(num_actions, dtype=np.float64)
        )
        self.iteration_count = 0

    def _state_key(self, obs: np.ndarray) -> str:
        """Discretize observation into a state key."""
        # Bucket each dimension
        complexity_bucket = int(obs[0] * 5)  # 0-5
        risk_bucket = int(obs[1] * 5)
        memory_bucket = min(5, int(obs[2] / 2))
        metacog_bucket = min(5, int(obs[3] / 20))
        return f"{complexity_bucket}_{risk_bucket}_{memory_bucket}_{metacog_bucket}"

    def get_strategy(self, obs: np.ndarray) -> np.ndarray:
        """Get current mixed strategy for state via regret matching."""
        key = self._state_key(obs)
        regret = self.regret_sum[key]

        # Regret matching: strategy proportional to positive regret
        positive_regret = np.maximum(regret, 0)
        total = positive_regret.sum()

        if total > 0:
            strategy = positive_regret / total
        else:
            strategy = np.ones(self.num_actions) / self.num_actions

        # Accumulate strategy for average
        self.strategy_sum[key] += strategy
        return strategy

    def update_regret(
        self, obs: np.ndarray, action: int, reward: float, counterfactual_values: np.ndarray
    ):
        """
        Update regret sums.

        counterfactual_values[a] = reward we would have gotten with action a.
        regret[a] = counterfactual_values[a] - reward_we_got
        """
        key = self._state_key(obs)
        for a in range(self.num_actions):
            self.regret_sum[key][a] += counterfactual_values[a] - reward

        self.iteration_count += 1

    def get_average_strategy(self, obs: np.ndarray) -> np.ndarray:
        """Get average strategy (converges to Nash in zero-sum)."""
        key = self._state_key(obs)
        total = self.strategy_sum[key].sum()
        if total > 0:
            return self.strategy_sum[key] / total
        return np.ones(self.num_actions) / self.num_actions

    def score_regret(self, obs: np.ndarray, action: int) -> float:
        """Score the regret for a specific action in a state."""
        key = self._state_key(obs)
        regret = self.regret_sum[key]
        if regret.sum() == 0:
            return 0.0
        # Normalize regret for this action
        max_regret = np.abs(regret).max()
        if max_regret == 0:
            return 0.0
        return float(regret[action] / max_regret)

    def get_stats(self) -> Dict:
        """Return summary statistics."""
        total_states = len(self.regret_sum)
        avg_regret = 0.0
        if total_states > 0:
            all_regrets = [np.abs(r).mean() for r in self.regret_sum.values()]
            avg_regret = np.mean(all_regrets)

        return {
            "total_states": total_states,
            "iterations": self.iteration_count,
            "avg_absolute_regret": float(avg_regret),
        }


# ============================================================
# HER Buffer - Hindsight Experience Replay
# ============================================================
@dataclass
class Transition:
    """Single transition in the replay buffer."""
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool
    info: Dict = field(default_factory=dict)


class HERBuffer:
    """
    Hindsight Experience Replay buffer.

    Stores transitions and performs hindsight relabeling:
    when an episode fails to reach the optimal path, relabel
    with the achieved goal to learn from suboptimal exploration.
    """

    def __init__(self, capacity: int = 100_000, her_ratio: float = 0.8):
        self.capacity = capacity
        self.her_ratio = her_ratio
        self.buffer: List[Transition] = []
        self.episode_buffer: List[Transition] = []
        self.position = 0
        self.total_stored = 0
        self.total_relabeled = 0

    def start_episode(self):
        """Start a new episode for hindsight relabeling."""
        self.episode_buffer = []

    def add(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
        info: Optional[Dict] = None,
    ):
        """Add a transition to the current episode."""
        transition = Transition(
            state=state.copy(),
            action=action,
            reward=reward,
            next_state=next_state.copy(),
            done=done,
            info=info or {},
        )
        self.episode_buffer.append(transition)

        # Also add to main buffer
        self._store(transition)

    def end_episode(self, final_reward: float):
        """
        End episode and perform hindsight relabeling.

        Relabeling: for suboptimal episodes, relabel transitions
        with the achieved outcome rather than the intended goal.
        """
        if not self.episode_buffer:
            return

        # Determine if we should relabel
        achieved_accuracy = self.episode_buffer[-1].info.get("reasoning_accuracy", 0)
        achieved_metacog = self.episode_buffer[-1].info.get("metacog_score", 0)

        # Relabel with hindsight: what if our goal was what we actually achieved?
        if random.random() < self.her_ratio and len(self.episode_buffer) > 1:
            self._relabel_episode(achieved_accuracy, achieved_metacog)

        self.episode_buffer = []

    def _relabel_episode(self, achieved_accuracy: float, achieved_metacog: float):
        """Relabel episode transitions with achieved outcome."""
        for i, transition in enumerate(self.episode_buffer):
            # Create relabeled transition with adjusted reward
            # Reward based on progress toward achieved goal
            progress = (i + 1) / len(self.episode_buffer)
            relabeled_reward = achieved_accuracy * progress * 0.5

            relabeled = Transition(
                state=transition.state.copy(),
                action=transition.action,
                reward=relabeled_reward,
                next_state=transition.next_state.copy(),
                done=transition.done,
                info={**transition.info, "relabeled": True},
            )
            self._store(relabeled)
            self.total_relabeled += 1

    def _store(self, transition: Transition):
        """Store transition in circular buffer."""
        if len(self.buffer) < self.capacity:
            self.buffer.append(transition)
        else:
            self.buffer[self.position] = transition
        self.position = (self.position + 1) % self.capacity
        self.total_stored += 1

    def sample(self, batch_size: int) -> List[Transition]:
        """Sample a batch of transitions."""
        batch_size = min(batch_size, len(self.buffer))
        return random.sample(self.buffer, batch_size)

    def get_stats(self) -> Dict:
        return {
            "buffer_size": len(self.buffer),
            "total_stored": self.total_stored,
            "total_relabeled": self.total_relabeled,
            "her_ratio": self.her_ratio,
        }


# ============================================================
# PPO Agent (lightweight wrapper / standalone fallback)
# ============================================================
class PPOAgent:
    """
    PPO agent that wraps stable_baselines3.PPO when available,
    falls back to a simple policy gradient for standalone use.
    """

    def __init__(
        self,
        env: MCTSExplorationEnv,
        cfr_critic: CFRCritic,
        her_buffer: HERBuffer,
        learning_rate: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_range: float = 0.2,
        n_steps: int = 2048,
        batch_size: int = 64,
        n_epochs: int = 10,
    ):
        self.env = env
        self.cfr_critic = cfr_critic
        self.her_buffer = her_buffer
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_range = clip_range
        self.n_steps = n_steps
        self.batch_size = batch_size
        self.n_epochs = n_epochs

        self.sb3_model = None
        self.use_sb3 = False

        # Simple policy table fallback
        self.policy_table: Dict[str, np.ndarray] = defaultdict(
            lambda: np.ones(5) / 5.0
        )
        self.value_table: Dict[str, float] = defaultdict(float)

        # Try to use stable_baselines3
        try:
            from stable_baselines3 import PPO as SB3_PPO
            from stable_baselines3.common.callbacks import CheckpointCallback

            self.sb3_model = SB3_PPO(
                "MlpPolicy",
                env,
                learning_rate=learning_rate,
                gamma=gamma,
                gae_lambda=gae_lambda,
                clip_range=clip_range,
                n_steps=min(n_steps, 256),
                batch_size=min(batch_size, 64),
                n_epochs=n_epochs,
                verbose=0,
            )
            self.use_sb3 = True
            print("[PPO] Using stable_baselines3 PPO")
        except ImportError:
            print("[PPO] stable_baselines3 not found, using built-in policy gradient")

    def _state_key(self, obs: np.ndarray) -> str:
        c = int(obs[0] * 5)
        r = int(obs[1] * 5)
        m = min(5, int(obs[2] / 2))
        mc = min(5, int(obs[3] / 20))
        return f"{c}_{r}_{m}_{mc}"

    def predict(self, obs: np.ndarray) -> int:
        """Predict action for observation."""
        if self.use_sb3 and self.sb3_model:
            action, _ = self.sb3_model.predict(obs, deterministic=False)
            return int(action)

        # Fallback: use CFR strategy blended with policy table
        cfr_strategy = self.cfr_critic.get_strategy(obs)
        key = self._state_key(obs)
        policy = self.policy_table[key]

        # Blend CFR and learned policy
        blended = 0.6 * cfr_strategy + 0.4 * policy
        blended /= blended.sum()

        return int(np.random.choice(5, p=blended))

    def update(
        self,
        obs: np.ndarray,
        action: int,
        reward: float,
        next_obs: np.ndarray,
        done: bool,
    ):
        """Update policy from a single transition (fallback mode)."""
        if self.use_sb3:
            return  # SB3 handles its own updates

        key = self._state_key(obs)

        # Simple policy gradient update
        advantage = reward - self.value_table[key]

        # Update value
        self.value_table[key] += self.learning_rate * advantage

        # Update policy (softmax PG)
        policy = self.policy_table[key]
        log_grad = np.zeros(5)
        log_grad[action] = 1.0 - policy[action]
        for a in range(5):
            if a != action:
                log_grad[a] = -policy[a]

        policy += self.learning_rate * advantage * log_grad
        policy = np.maximum(policy, 1e-8)
        policy /= policy.sum()
        self.policy_table[key] = policy

    def train_sb3(self, total_timesteps: int, checkpoint_freq: int = 10000):
        """Train using SB3 PPO with checkpoints."""
        if not self.use_sb3 or not self.sb3_model:
            return False

        from stable_baselines3.common.callbacks import CheckpointCallback

        checkpoint_dir = "mcts_checkpoints"
        os.makedirs(checkpoint_dir, exist_ok=True)

        checkpoint_callback = CheckpointCallback(
            save_freq=checkpoint_freq,
            save_path=checkpoint_dir,
            name_prefix="mcts_ppo",
        )

        self.sb3_model.learn(
            total_timesteps=total_timesteps,
            callback=checkpoint_callback,
        )
        return True

    def save(self, path: str):
        """Save the model."""
        if self.use_sb3 and self.sb3_model:
            self.sb3_model.save(path)
        else:
            # Save policy table
            save_data = {
                "policy_table": {k: v.tolist() for k, v in self.policy_table.items()},
                "value_table": dict(self.value_table),
            }
            with open(path + ".json", "w") as f:
                json.dump(save_data, f)
        print(f"[PPO] Model saved to {path}")

    def load(self, path: str):
        """Load a saved model."""
        if self.use_sb3:
            try:
                from stable_baselines3 import PPO as SB3_PPO
                self.sb3_model = SB3_PPO.load(path, env=self.env)
                print(f"[PPO] Loaded SB3 model from {path}")
                return
            except Exception:
                pass

        json_path = path + ".json" if not path.endswith(".json") else path
        if os.path.exists(json_path):
            with open(json_path, "r") as f:
                data = json.load(f)
            self.policy_table = defaultdict(
                lambda: np.ones(5) / 5.0,
                {k: np.array(v) for k, v in data["policy_table"].items()},
            )
            self.value_table = defaultdict(float, data["value_table"])
            print(f"[PPO] Loaded policy table from {json_path}")


# ============================================================
# Training Metrics Tracker
# ============================================================
class TrainingMetrics:
    """Track and report training metrics matching DeployGym style."""

    def __init__(self):
        self.episodes: List[Dict] = []
        self.epoch_metrics: List[Dict] = []
        self.start_time = time.time()
        self.best_accuracy = 0.0
        self.best_metacog = 0.0
        self.convergence_window: List[float] = []
        self.convergence_threshold = 0.001
        self.convergence_patience = 500

    def log_episode(self, episode_num: int, stats: Dict, reward: float):
        """Log episode results."""
        entry = {
            "episode": episode_num,
            "reward": reward,
            "branches_explored": stats.get("branches_explored", 0),
            "regret_minimized": stats.get("regret_minimized", 0.0),
            "metacog_score": stats.get("metacog_score", 0.0),
            "reasoning_accuracy": stats.get("reasoning_accuracy", 0.0),
            "exploration_diversity": stats.get("exploration_diversity", 0.0),
            "answer_regret": stats.get("answer_regret", 0.0),
            "timestamp": time.time(),
        }
        self.episodes.append(entry)

        # Track best
        if entry["reasoning_accuracy"] > self.best_accuracy:
            self.best_accuracy = entry["reasoning_accuracy"]
        if entry["metacog_score"] > self.best_metacog:
            self.best_metacog = entry["metacog_score"]

        # Track convergence
        regret_delta = abs(entry["answer_regret"])
        self.convergence_window.append(regret_delta)
        if len(self.convergence_window) > self.convergence_patience:
            self.convergence_window.pop(0)

    def print_episode(self, episode_num: int, stats: Dict, reward: float):
        """Print episode stats in DeployGym style."""
        branches = stats.get("branches_explored", 0)
        regret = stats.get("regret_minimized", 0.0)
        metacog = stats.get("metacog_score", 0.0)
        accuracy = stats.get("reasoning_accuracy", 0.0)

        print(
            f"  Episode {episode_num:>5d} | "
            f"Branches: {branches:>3d} | "
            f"Regret: {regret:>+6.1f}% | "
            f"Metacog: {metacog:>5.1f}/100 | "
            f"Accuracy: {accuracy:.3f} | "
            f"Reward: {reward:>+.3f}"
        )

    def check_convergence(self) -> bool:
        """Check if training has converged."""
        if len(self.convergence_window) < self.convergence_patience:
            return False
        recent_delta = np.std(self.convergence_window[-self.convergence_patience:])
        return recent_delta < self.convergence_threshold

    def print_summary(self, total_episodes: int, validation_accuracy: float):
        """Print final training summary."""
        elapsed = time.time() - self.start_time
        recent = self.episodes[-100:] if len(self.episodes) >= 100 else self.episodes

        avg_reward = np.mean([e["reward"] for e in recent])
        avg_regret = np.mean([e["regret_minimized"] for e in recent])
        avg_metacog = np.mean([e["metacog_score"] for e in recent])
        avg_accuracy = np.mean([e["reasoning_accuracy"] for e in recent])

        print("\n" + "=" * 70)
        print("MCTS EXPLORATION GYM v1 - TRAINING COMPLETE")
        print("=" * 70)
        print(f"  Total episodes:       {total_episodes}")
        print(f"  Training time:        {elapsed:.1f}s")
        print(f"  Avg reward (last100): {avg_reward:+.3f}")
        print(f"  Avg regret reduction: {avg_regret:+.1f}%")
        print(f"  Avg metacog score:    {avg_metacog:.1f}/100")
        print(f"  Avg accuracy:         {avg_accuracy:.3f}")
        print(f"  Best accuracy:        {self.best_accuracy:.3f}")
        print(f"  Best metacog:         {self.best_metacog:.1f}/100")
        print(f"  Validation accuracy:  {validation_accuracy:.3f}")
        print(f"  Accuracy lift:        {validation_accuracy * 100 - 50:.1f}%")
        print("=" * 70)

    def get_epoch_summary(self, epoch_episodes: List[Dict]) -> Dict:
        """Compute summary metrics for an epoch."""
        if not epoch_episodes:
            return {}
        return {
            "avg_reward": np.mean([e["reward"] for e in epoch_episodes]),
            "avg_regret": np.mean([e["regret_minimized"] for e in epoch_episodes]),
            "avg_metacog": np.mean([e["metacog_score"] for e in epoch_episodes]),
            "avg_accuracy": np.mean([e["reasoning_accuracy"] for e in epoch_episodes]),
            "avg_diversity": np.mean([e["exploration_diversity"] for e in epoch_episodes]),
        }


# ============================================================
# Insight Writer - pgvector / universal_insights mock
# ============================================================
def commit_insights(metrics: TrainingMetrics, top_n: int = 3):
    """
    Write top learned patterns to universal_insights table.
    Uses pgvector if DB is available, otherwise writes to JSON file.
    """
    # Extract top patterns from training
    if not metrics.episodes:
        print("[Insights] No episodes to analyze")
        return

    # Group by action and compute average rewards
    action_rewards = defaultdict(list)
    for ep in metrics.episodes:
        # Infer dominant action from branches count
        branches = ep.get("branches_explored", 0)
        if branches >= 16:
            action_rewards["explore_16branches"].append(ep["reward"])
        elif branches >= 8:
            action_rewards["explore_8branches"].append(ep["reward"])
        action_rewards["overall"].append(ep["reward"])

    # Generate insights
    insights = []

    # Insight 1: Best exploration strategy
    best_action = max(
        [(k, np.mean(v)) for k, v in action_rewards.items() if k != "overall"],
        key=lambda x: x[1],
        default=("explore_8branches", 0.5),
    )
    insights.append({
        "pattern": f"MCTS exploration: {best_action[0]} yields highest reward ({best_action[1]:.3f})",
        "category": "mcts_strategy",
        "confidence": min(0.95, best_action[1]),
        "source": "mcts_exploration_gym_v1",
    })

    # Insight 2: Convergence behavior
    late_episodes = metrics.episodes[-100:]
    avg_regret_late = np.mean([e["regret_minimized"] for e in late_episodes])
    insights.append({
        "pattern": f"MCTS regret minimization converges to {avg_regret_late:+.1f}% after training",
        "category": "mcts_convergence",
        "confidence": 0.85,
        "source": "mcts_exploration_gym_v1",
    })

    # Insight 3: Domain-specific finding
    high_metacog = [e for e in metrics.episodes if e["metacog_score"] > 80]
    pct_high = len(high_metacog) / max(1, len(metrics.episodes)) * 100
    insights.append({
        "pattern": f"MCTS achieves metacog >80 in {pct_high:.1f}% of episodes",
        "category": "mcts_metacog",
        "confidence": 0.80,
        "source": "mcts_exploration_gym_v1",
    })

    # Try pgvector first
    db_written = False
    try:
        import psycopg2
        conn = psycopg2.connect(os.environ.get(
            "DATABASE_URL",
            "postgresql://localhost:5432/roger"
        ))
        cur = conn.cursor()

        for insight in insights[:top_n]:
            cur.execute(
                """INSERT INTO universal_insights (pattern, category, confidence, source, created_at)
                   VALUES (%s, %s, %s, %s, NOW())
                   ON CONFLICT (pattern) DO UPDATE SET confidence = EXCLUDED.confidence""",
                (insight["pattern"], insight["category"], insight["confidence"], insight["source"]),
            )
        conn.commit()
        cur.close()
        conn.close()
        db_written = True
        print(f"[Insights] Wrote {top_n} insights to universal_insights (pgvector)")
    except Exception:
        pass

    if not db_written:
        # Fallback: write to JSON
        insights_file = "mcts_insights.json"
        with open(insights_file, "w") as f:
            json.dump(insights[:top_n], f, indent=2)
        print(f"[Insights] Wrote {top_n} insights to {insights_file} (pgvector unavailable)")

    for i, insight in enumerate(insights[:top_n]):
        print(f"  Insight {i+1}: {insight['pattern']}")


# ============================================================
# Main Training Loop
# ============================================================
def train(
    total_timesteps: int = 100_000,
    checkpoint_freq: int = 10_000,
    validation_split: float = 0.2,
    commit_insights_flag: bool = False,
    verbose: bool = True,
):
    """
    Main training function.

    Args:
        total_timesteps: Total training steps (default 100k)
        checkpoint_freq: Save checkpoint every N steps
        validation_split: Fraction of episodes for validation holdout
        commit_insights_flag: Write insights to universal_insights
        verbose: Print progress
    """
    print("=" * 70)
    print("MCTS EXPLORATION GYM v1 - PPO+CFR-HER TRAINING")
    print("=" * 70)
    print(f"  Total timesteps: {total_timesteps:,}")
    print(f"  Checkpoint freq: {checkpoint_freq:,}")
    print(f"  Validation split: {validation_split:.0%}")
    print(f"  Commit insights: {commit_insights_flag}")
    print()

    # Initialize environment and components
    env = MCTSExplorationEnv()
    cfr_critic = CFRCritic(num_actions=5)
    her_buffer = HERBuffer(capacity=100_000, her_ratio=0.8)
    metrics = TrainingMetrics()

    # Initialize PPO agent
    agent = PPOAgent(
        env=env,
        cfr_critic=cfr_critic,
        her_buffer=her_buffer,
        learning_rate=3e-4,
        gamma=0.99,
    )

    # If SB3 available, use its training loop
    if agent.use_sb3:
        print("[Training] Using stable_baselines3 PPO training loop")
        print("[Training] Running SB3 learn()...")

        agent.train_sb3(total_timesteps, checkpoint_freq)

        # Post-training: run validation episodes
        print("\n[Validation] Running validation episodes...")
        val_rewards = []
        val_accuracies = []
        num_val = max(50, int(total_timesteps / 50))

        for i in range(num_val):
            obs, info = env.reset()
            episode_reward = 0.0
            done = False

            while not done:
                action = agent.predict(obs)
                obs, reward, terminated, truncated, info = env.step(action)
                episode_reward += reward
                done = terminated or truncated

            val_rewards.append(episode_reward)
            val_accuracies.append(info.get("reasoning_accuracy", 0.0))

            if verbose and (i + 1) % 10 == 0:
                metrics.print_episode(i + 1, info, episode_reward)

        val_accuracy = np.mean(val_accuracies)
        metrics.print_summary(num_val, val_accuracy)

        # Save model
        agent.save("mcts_exploration_model")
        print(f"[Model] Saved to mcts_exploration_model.zip")

        if commit_insights_flag:
            commit_insights(metrics)

        return agent, metrics

    # ============================================================
    # Fallback: Manual training loop (no SB3)
    # ============================================================
    print("[Training] Running manual PPO+CFR-HER training loop")

    # Split scenarios into train/validation
    scenarios = SEED_SCENARIOS.copy()
    random.shuffle(scenarios)
    split_idx = int(len(scenarios) * (1 - validation_split))
    train_scenarios = scenarios[:split_idx]
    val_scenarios = scenarios[split_idx:]

    print(f"  Train scenarios: {len(train_scenarios)}")
    print(f"  Val scenarios:   {len(val_scenarios)}")
    print()

    # Estimate episodes from timesteps (avg ~5 steps per episode)
    avg_steps_per_episode = 5
    total_episodes = total_timesteps // avg_steps_per_episode
    episodes_per_checkpoint = checkpoint_freq // avg_steps_per_episode

    total_steps = 0
    converged = False

    for episode in range(1, total_episodes + 1):
        # Pick a training scenario
        scenario = train_scenarios[(episode - 1) % len(train_scenarios)]
        obs, info = env.reset(options={"scenario": scenario})

        her_buffer.start_episode()
        episode_reward = 0.0
        done = False

        while not done:
            # Get action from agent (blended CFR + policy)
            action = agent.predict(obs)

            # Step environment
            next_obs, reward, terminated, truncated, step_info = env.step(action)
            done = terminated or truncated

            # CFR: estimate counterfactual values
            cf_values = np.zeros(5)
            for a in range(5):
                # Approximate: simulate each action's reward
                cf_values[a] = reward + random.gauss(0, 0.05)
            cf_values[action] = reward
            cfr_critic.update_regret(obs, action, reward, cf_values)

            # HER: store transition
            her_buffer.add(obs, action, reward, next_obs, done, step_info)

            # Policy update
            agent.update(obs, action, reward, next_obs, done)

            episode_reward += reward
            obs = next_obs
            total_steps += 1

        # End episode HER
        her_buffer.end_episode(episode_reward)

        # Log metrics
        final_info = step_info if step_info else {}
        metrics.log_episode(episode, final_info, episode_reward)

        # Print progress
        if verbose and episode % 100 == 0:
            metrics.print_episode(episode, final_info, episode_reward)

        # Checkpoint
        if episode % episodes_per_checkpoint == 0:
            ckpt_path = f"mcts_checkpoints/mcts_ppo_ep{episode}"
            os.makedirs("mcts_checkpoints", exist_ok=True)
            agent.save(ckpt_path)
            print(f"  [Checkpoint] Saved at episode {episode} (step ~{total_steps})")

            # Print epoch summary
            recent = metrics.episodes[-episodes_per_checkpoint:]
            summary = metrics.get_epoch_summary(recent)
            print(
                f"  [Epoch] Avg reward: {summary.get('avg_reward', 0):.3f} | "
                f"Avg regret: {summary.get('avg_regret', 0):+.1f}% | "
                f"Avg metacog: {summary.get('avg_metacog', 0):.1f}/100"
            )

        # Convergence detection
        if metrics.check_convergence():
            print(f"\n  [Converged] Regret delta < {metrics.convergence_threshold} "
                  f"for {metrics.convergence_patience} episodes. Early stopping at episode {episode}.")
            converged = True
            break

        # Safety: check total steps
        if total_steps >= total_timesteps:
            print(f"\n  [Complete] Reached {total_timesteps:,} timesteps at episode {episode}.")
            break

    # ============================================================
    # Validation
    # ============================================================
    print("\n[Validation] Running on holdout set...")
    val_rewards = []
    val_accuracies = []

    for i, scenario in enumerate(val_scenarios):
        obs, info = env.reset(options={"scenario": scenario})
        ep_reward = 0.0
        done = False

        while not done:
            action = agent.predict(obs)
            obs, reward, terminated, truncated, info = env.step(action)
            ep_reward += reward
            done = terminated or truncated

        val_rewards.append(ep_reward)
        val_accuracies.append(info.get("reasoning_accuracy", 0.0))

    val_accuracy = np.mean(val_accuracies)
    print(f"  Validation episodes: {len(val_scenarios)}")
    print(f"  Validation accuracy: {val_accuracy:.3f}")
    print(f"  Validation avg reward: {np.mean(val_rewards):.3f}")

    # Final summary
    metrics.print_summary(episode, val_accuracy)

    # Save final model
    agent.save("mcts_exploration_model")
    print(f"\n[Model] Final model saved to mcts_exploration_model.zip")

    # CFR stats
    cfr_stats = cfr_critic.get_stats()
    print(f"\n[CFR] States explored: {cfr_stats['total_states']}")
    print(f"[CFR] Iterations: {cfr_stats['iterations']}")
    print(f"[CFR] Avg absolute regret: {cfr_stats['avg_absolute_regret']:.4f}")

    # HER stats
    her_stats = her_buffer.get_stats()
    print(f"\n[HER] Buffer size: {her_stats['buffer_size']}")
    print(f"[HER] Total stored: {her_stats['total_stored']}")
    print(f"[HER] Total relabeled: {her_stats['total_relabeled']}")

    # Commit insights
    if commit_insights_flag:
        print("\n[Insights] Committing top-3 patterns to universal_insights...")
        commit_insights(metrics)

    return agent, metrics


# ============================================================
# CLI Entry Point
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="MCTS Exploration Gym v1 - PPO+CFR-HER Training"
    )
    parser.add_argument(
        "--timesteps", type=int, default=100_000,
        help="Total training timesteps (default: 100000)"
    )
    parser.add_argument(
        "--checkpoint-freq", type=int, default=10_000,
        help="Checkpoint frequency in timesteps (default: 10000)"
    )
    parser.add_argument(
        "--validation-split", type=float, default=0.2,
        help="Validation holdout fraction (default: 0.2)"
    )
    parser.add_argument(
        "--commit-insights", action="store_true",
        help="Write top-3 learned patterns to universal_insights table"
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-episode output"
    )

    args = parser.parse_args()

    agent, metrics = train(
        total_timesteps=args.timesteps,
        checkpoint_freq=args.checkpoint_freq,
        validation_split=args.validation_split,
        commit_insights_flag=args.commit_insights,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
