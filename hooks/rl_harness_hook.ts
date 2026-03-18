/**
 * RL Harness Hook - TypeScript for OpenClaw
 * 
 * Main orchestrator that chains:
 * - rl_harness_env: state → action → pgvector flow
 * - rl_reward_shaper: PPO/CFR reward shaping via futureself + NeuralFusion
 * - self-improve: self-improvement hook for parameter adjustment
 * - mcts-reflection: Monte Carlo Tree Search for decision simulation
 * - factcheck-swarm: pre-action staleness gate + post-response critique
 * 
 * RL Loop:
 * - run_episode(agent, env_config) → executes full RL episode
 * - train(n_episodes) → runs multiple episodes with self-improve
 * - get_policy() → returns learned policy from pgvector
 * 
 * Trigger: "rl"/"train"/"reinforce"/"policy" in events or explicit calls
 */

import { Pool } from 'pg';

// ============ TYPE DEFINITIONS ============

// Forward declarations for env and shaper (import when available)
interface RLState {
  observation: number[];
  info: Record<string, any>;
  timestamp: number;
}

interface RLAction {
  action: string | number;
  confidence: number;
  reasoning?: string;
}

interface RLStepResult {
  state: RLState;
  action: RLAction;
  reward: number;
  done: boolean;
  info: Record<string, any>;
}

interface RLEnvironmentConfig {
  name: string;
  state_dim: number;
  action_space: string; // 'discrete' | 'continuous'
  n_actions?: number;
  max_steps: number;
  reward_fn?: string; // reference to reward function
}

interface EpisodeStats {
  episode: number;
  total_reward: number;
  steps: number;
  duration_ms: number;
  actions: RLAction[];
  rewards: number[];
  final_state: RLState;
}

interface Policy {
  id: string;
  name: string;
  version: number;
  created_at: Date;
  parameters: Record<string, any>;
  embeddings: number[];
}

interface FactCheckResult {
  valid: boolean;
  confidence: number;
  issues: string[];
  suggestions: string[];
}

interface MCTSResult {
  best_action: RLAction;
  explored_branches: string[];
  expected_value: number;
  confidence: number;
}

// Self-improve hook response
interface SelfImproveResponse {
  adjusted_params: Record<string, any>;
  improvements: string[];
  confidence: number;
}

// ============ CONFIGURATION ============

interface RLHarnessConfig {
  // Database
  connectionString: string;
  
  // RL Parameters
  learning_rate: number;
  gamma: number; // discount factor
  epsilon: number; // exploration rate
  epsilon_decay: number;
  epsilon_min: number;
  
  // MCTS
  mcts_simulations: number;
  mcts_max_depth: number;
  
  // Factcheck
  factcheck_enabled: boolean;
  factcheck_strictness: number; // 0-1
  
  // Self-improve
  self_improve_enabled: boolean;
  self_improve_threshold: number;
  
  // Training
  batch_size: number;
  target_update_interval: number;
}

const DEFAULT_CONFIG: RLHarnessConfig = {
  connectionString: process.env.DATABASE_URL || 'postgresql://user:pass@localhost:5432/rl_agent',
  learning_rate: 0.001,
  gamma: 0.99,
  epsilon: 1.0,
  epsilon_decay: 0.995,
  epsilon_min: 0.01,
  mcts_simulations: 25,
  mcts_max_depth: 3,
  factcheck_enabled: true,
  factcheck_strictness: 0.7,
  self_improve_enabled: true,
  self_improve_threshold: 0.6,
  batch_size: 32,
  target_update_interval: 100
};

// ============ EMBEDDING SERVICE ============

class EmbeddingService {
  private model: string;
  private dimensions: number;

  constructor(model: string = 'all-mpnet-base-v2', dimensions: number = 768) {
    this.model = model;
    this.dimensions = dimensions;
  }

  async embed(text: string): Promise<number[]> {
    const response = await fetch(`${process.env.EMBEDDING_API_URL || 'http://localhost:11434'}/api/embeddings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: this.model,
        prompt: text
      })
    });

    if (!response.ok) {
      // Fallback: simple hash-based embedding for development
      return this.fallbackEmbed(text);
    }

    const data = await response.json() as { embedding?: number[] };
    
    if (!data.embedding || data.embedding.length !== this.dimensions) {
      return this.fallbackEmbed(text);
    }

    return data.embedding;
  }

  private fallbackEmbed(text: string): number[] {
    // Simple deterministic fallback for development
    const embedding = new Array(this.dimensions).fill(0);
    let hash = 0;
    for (let i = 0; i < text.length; i++) {
      hash = ((hash << 5) - hash) + text.charCodeAt(i);
      hash = hash & hash;
    }
    const seed = Math.abs(hash);
    for (let i = 0; i < this.dimensions; i++) {
      embedding[i] = Math.sin(seed * (i + 1)) * 0.5;
    }
    return embedding;
  }
}

// ============ RL ENVIRONMENT (rl_harness_env.ts integration) ============

class RLEnvironment {
  private config: RLEnvironmentConfig;
  private current_step: number = 0;
  private state: RLState | null = null;

  constructor(config: RLEnvironmentConfig) {
    this.config = config;
  }

  reset(): RLState {
    this.current_step = 0;
    this.state = {
      observation: new Array(this.config.state_dim).fill(0).map(() => Math.random() * 2 - 1),
      info: { episode: 0 },
      timestamp: Date.now()
    };
    return this.state;
  }

  step(action: RLAction): RLStepResult {
    if (!this.state) {
      throw new Error('Environment not reset. Call reset() first.');
    }

    this.current_step++;
    
    // Simulate environment response (replace with actual env in production)
    const reward = this.computeReward(this.state, action);
    const done = this.current_step >= this.config.max_steps;
    
    // Next state
    const next_obs = this.state.observation.map((v, i) => 
      Math.tanh(v + action.action === 'explore' ? Math.random() * 0.5 : 0.1)
    );
    
    this.state = {
      observation: next_obs,
      info: { step: this.current_step, action: action.action },
      timestamp: Date.now()
    };

    return {
      state: this.state,
      action,
      reward,
      done,
      info: { step: this.current_step }
    };
  }

  private computeReward(state: RLState, action: RLAction): number {
    // Default reward function - can be overridden
    const exploration_bonus = action.action === 'explore' ? 0.1 : 0;
    const step_penalty = -0.01;
    return exploration_bonus + step_penalty;
  }

  get_config(): RLEnvironmentConfig {
    return this.config;
  }
}

// ============ REWARD SHAPING (rl_reward_shaper.ts integration) ============

class RewardShaper {
  private config: RLHarnessConfig;
  private futureself_model: string;
  private neural_fusion_endpoint: string;

  constructor(config: RLHarnessConfig) {
    this.config = config;
    this.futureself_model = process.env.FUTURESELF_MODEL || 'futureself-v1';
    this.neural_fusion_endpoint = process.env.NEURAL_FUSION_URL || 'http://localhost:8080/fusion';
  }

  async shape_reward(
    state: RLState,
    action: RLAction,
    raw_reward: number,
    episode_history: EpisodeStats
  ): Promise<number> {
    // Step 1: Futureself alignment bonus
    const futureself_bonus = await this.computeFutureselfBonus(state, action, episode_history);
    
    // Step 2: NeuralFusion shaping
    const neural_shaping = await this.computeNeuralFusionShaping(state, action, raw_reward);
    
    // Step 3: PPO-style advantage estimation
    const advantage = this.computeAdvantage(episode_history.rewards, raw_reward);
    
    // Combined shaped reward
    const shaped_reward = raw_reward + futureself_bonus + neural_shaping + advantage * this.config.learning_rate;
    
    return shaped_reward;
  }

  private async computeFutureselfBonus(
    state: RLState,
    action: RLAction,
    history: EpisodeStats
  ): Promise<number> {
    // Simulated futureself alignment
    // In production, this would query a futureself model
    const recent_actions = history.actions.slice(-5);
    const consistency = recent_actions.filter(a => a.action === action.action).length / Math.max(1, recent_actions.length);
    
    // Bonus for consistent, thoughtful actions
    return consistency * 0.1 + (action.confidence || 0.5) * 0.05;
  }

  private async computeNeuralFusionShaping(
    state: RLState,
    action: RLAction,
    raw_reward: number
  ): Promise<number> {
    // NeuralFusion shaping (simplified)
    // In production, this would call the neural_fusion_endpoint
    const state_norm = Math.sqrt(state.observation.reduce((sum, v) => sum + v * v, 0));
    const action_magnitude = typeof action.action === 'number' ? Math.abs(action.action) : 0.5;
    
    // Shaping based on state-action alignment
    return (state_norm * action_magnitude * 0.01);
  }

  private computeAdvantage(rewards: number[], current_reward: number): number {
    if (rewards.length === 0) return 0;
    
    const baseline = rewards.reduce((a, b) => a + b, 0) / rewards.length;
    return current_reward - baseline;
  }
}

// ============ FACTCHECK SWARM ============

class FactCheckSwarm {
  private strictness: number;
  private memory_pool: Pool;

  constructor(strictness: number, connectionString: string) {
    this.strictness = strictness;
    this.memory_pool = new Pool({ connectionString });
  }

  // Pre-action: staleness gate
  async checkStaleness(context: string): Promise<boolean> {
    try {
      // Query recent memories to check context validity
      const result = await this.memory_pool.query(
        `SELECT created_at, content FROM memories 
         WHERE content ILIKE $1 
         ORDER BY created_at DESC LIMIT 5`,
        [`%${context.substring(0, 50)}%`]
      );

      if (result.rows.length === 0) return true; // No history, assume valid

      const latest = result.rows[0].created_at;
      const staleness_ms = Date.now() - new Date(latest).getTime();
      const staleness_hours = staleness_ms / (1000 * 60 * 60);

      // Context is stale if older than (1 - strictness) * 24 hours
      const max_staleness = (1 - this.strictness) * 24;
      return staleness_hours > max_staleness;
    } catch {
      return true; // On error, allow action
    }
  }

  // Post-response: critique loop
  async validateAction(state: RLState, action: RLAction): Promise<FactCheckResult> {
    const result: FactCheckResult = {
      valid: true,
      confidence: 1.0,
      issues: [],
      suggestions: []
    };

    // Check action against known facts in memory
    try {
      const action_str = JSON.stringify(action);
      const result_db = await this.memory_pool.query(
        `SELECT content, importance FROM memories 
         WHERE memory_type = 'fact' 
         ORDER BY importance DESC LIMIT 10`
      );

      for (const row of result_db.rows) {
        // Simple keyword conflict detection
        const conflict = this.detectConflict(action_str, row.content);
        if (conflict) {
          result.issues.push(`Potential conflict with: ${row.content.substring(0, 50)}...`);
          result.valid = false;
          result.confidence *= 0.5;
        }
      }
    } catch {
      // Database not available, skip validation
    }

    return result;
  }

  private detectConflict(action_str: string, fact: string): boolean {
    // Simplified conflict detection
    const action_lower = action_str.toLowerCase();
    const fact_lower = fact.toLowerCase();
    
    // Check for direct contradictions (simplified)
    const negations = ['not', 'no', 'never', 'false', 'wrong'];
    for (const neg of negations) {
      if (action_lower.includes(neg) && fact_lower.includes(neg)) {
        return true;
      }
    }
    return false;
  }
}

// ============ MCTS REFLECTION ============

class MCTSReflection {
  private simulations: number;
  private max_depth: number;

  constructor(simulations: number = 25, max_depth: number = 3) {
    this.simulations = simulations;
    this.max_depth = max_depth;
  }

  async reflect(
    state: RLState,
    available_actions: string[]
  ): Promise<MCTSResult> {
    // Simplified MCTS for action selection
    const branches = available_actions.slice(0, 8);
    
    let best_action = available_actions[0];
    let best_value = -Infinity;
    const explored: string[] = [];

    for (const branch of branches) {
      const value = await this.simulateBranch(state, branch);
      explored.push(`${branch}:${value.toFixed(2)}`);
      
      if (value > best_value) {
        best_value = value;
        best_action = branch;
      }
    }

    return {
      best_action: {
        action: best_action,
        confidence: Math.min(0.95, 0.5 + (this.simulations / 100)),
        reasoning: `MCTS selected ${best_action} with expected value ${best_value.toFixed(2)}`
      },
      explored_branches: explored,
      expected_value: best_value,
      confidence: Math.min(0.95, 0.5 + (this.simulations / 100))
    };
  }

  private async simulateBranch(state: RLState, action: string): Promise<number> {
    // Simplified simulation
    const state_magnitude = Math.sqrt(state.observation.reduce((sum, v) => sum + v * v, 0));
    const action_hash = action.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
    
    return state_magnitude * (action_hash % 100) / 100 + 0.5;
  }
}

// ============ SELF-IMPROVE INTEGRATION ============

class SelfImprove {
  private enabled: boolean;
  private threshold: number;
  private improvement_history: Array<{episode: number; delta: number}> = [];

  constructor(enabled: boolean, threshold: number) {
    this.enabled = enabled;
    this.threshold = threshold;
  }

  async improve(episode_stats: EpisodeStats): Promise<SelfImproveResponse> {
    if (!this.enabled) {
      return { adjusted_params: {}, improvements: [], confidence: 1.0 };
    }

    const return_value = episode_stats.total_reward;
    const baseline = this.getBaseline();
    
    // Calculate improvement
    const delta = (return_value - baseline) / Math.max(1, Math.abs(baseline));
    
    this.improvement_history.push({ episode: episode_stats.episode, delta });

    const adjustments: Record<string, any> = {};
    const improvements: string[] = [];

    // Adjust learning rate based on improvement
    if (delta < -this.threshold) {
      adjustments.learning_rate = Math.max(0.0001, adjustments.learning_rate || 0.001 * 0.5);
      improvements.push('Reduced learning rate due to performance decline');
    } else if (delta > this.threshold) {
      adjustments.learning_rate = Math.min(0.01, (adjustments.learning_rate || 0.001) * 1.2);
      improvements.push('Increased learning rate due to strong performance');
    }

    // Adjust exploration
    if (episode_stats.steps < 10 && return_value < 0) {
      adjustments.epsilon = Math.min(1.0, (adjustments.epsilon || 1.0) * 1.5);
      improvements.push('Increased exploration due to early termination');
    }

    // Update baseline
    this.updateBaseline(return_value);

    return {
      adjusted_params: adjustments,
      improvements,
      confidence: Math.min(1.0, Math.abs(delta) + 0.5)
    };
  }

  private getBaseline(): number {
    if (this.improvement_history.length < 5) return 0;
    const recent = this.improvement_history.slice(-10);
    return recent.reduce((sum, x) => sum + x.delta, 0) / recent.length;
  }

  private updateBaseline(return_value: number): void {
    // Sliding window baseline update
    if (this.improvement_history.length > 20) {
      this.improvement_history = this.improvement_history.slice(-20);
    }
  }
}

// ============ MAIN RL HARNESS ORCHESTRATOR ============

export class RLHarness {
  private config: RLHarnessConfig;
  private env: RLEnvironment | null = null;
  private shaper: RewardShaper;
  private factcheck: FactCheckSwarm;
  private mcts: MCTSReflection;
  private self_improve: SelfImprove;
  private embedding: EmbeddingService;
  private memory_pool: Pool;
  
  private policy: Policy | null = null;
  private episode_history: EpisodeStats[] = [];
  private current_episode: number = 0;

  constructor(config: Partial<RLHarnessConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.shaper = new RewardShaper(this.config);
    this.factcheck = new FactCheckSwarm(this.config.factcheck_strictness, this.config.connectionString);
    this.mcts = new MCTSReflection(this.config.mcts_simulations, this.config.mcts_max_depth);
    this.self_improve = new SelfImprove(this.config.self_improve_enabled, this.config.self_improve_threshold);
    this.embedding = new EmbeddingService();
    this.memory_pool = new Pool({ connectionString: this.config.connectionString });
  }

  // Initialize environment
  initialize_env(env_config: RLEnvironmentConfig): void {
    this.env = new RLEnvironment(env_config);
    console.log(`🎮 RL Environment initialized: ${env_config.name}`);
  }

  // Run a single episode
  async run_episode(agent: any, env_config?: RLEnvironmentConfig): Promise<EpisodeStats> {
    if (!this.env && env_config) {
      this.initialize_env(env_config);
    }
    if (!this.env) {
      throw new Error('Environment not initialized. Provide env_config.');
    }

    const start_time = Date.now();
    const episode = ++this.current_episode;
    
    const state = this.env.reset();
    let total_reward = 0;
    let step = 0;
    const actions: RLAction[] = [];
    const rewards: number[] = [];

    console.log(`📊 Episode ${episode} starting...`);

    while (true) {
      // Step 1: MCTS Reflection before decision
      const available_actions = ['explore', 'exploit', 'wait', 'adapt'];
      const mcts_result = await this.mcts.reflect(state, available_actions);
      const selected_action = mcts_result.best_action;

      // Step 2: Factcheck Swarm - Pre-action validation
      if (this.config.factcheck_enabled) {
        const context = JSON.stringify({ state, action: selected_action });
        const is_stale = await this.factcheck.checkStaleness(context);
        
        if (is_stale) {
          console.log('⚠️ Context stale, refreshing...');
          // Could trigger memory refresh here
        }

        const validation = await this.factcheck.validateAction(state, selected_action);
        if (!validation.valid && validation.confidence < this.config.factcheck_strictness) {
          console.log(`❌ Action rejected by factcheck: ${validation.issues.join(', ')}`);
          // Fallback to safe action
          selected_action.action = 'wait';
          selected_action.confidence *= 0.5;
        }
      }

      // Step 3: Execute action in environment
      const step_result = this.env.step(selected_action);
      
      // Step 4: Shape reward using rl_reward_shaper
      const shaped_reward = await this.shaper.shape_reward(
        state,
        selected_action,
        step_result.reward,
        { episode, total_reward, steps: step, duration_ms: 0, actions, rewards, final_state: state }
      );

      // Step 5: Store in memory (pgvector)
      await this.store_transition(state, selected_action, shaped_reward, episode, step);

      // Accumulate
      actions.push(selected_action);
      rewards.push(shaped_reward);
      total_reward += shaped_reward;
      step++;

      // Check termination
      if (step_result.done) break;
      if (step >= (this.env.get_config().max_steps || 100)) break;
      
      // Update state
      state = step_result.state;
    }

    // Episode complete
    const duration_ms = Date.now() - start_time;
    const stats: EpisodeStats = {
      episode,
      total_reward,
      steps: step,
      duration_ms,
      actions,
      rewards,
      final_state: state
    };

    this.episode_history.push(stats);
    console.log(`✅ Episode ${episode} complete: reward=${total_reward.toFixed(2)}, steps=${step}`);

    // Step 6: Self-improve hook
    if (this.config.self_improve_enabled) {
      const improvement = await this.self_improve.improve(stats);
      if (improvement.improvements.length > 0) {
        console.log(`🔧 Self-improve: ${improvement.improvements.join(', ')}`);
        // Apply adjustments to config
        Object.assign(this.config, improvement.adjusted_params);
      }
    }

    // Decay epsilon
    this.config.epsilon = Math.max(
      this.config.epsilon_min,
      this.config.epsilon * this.config.epsilon_decay
    );

    return stats;
  }

  // Train for multiple episodes
  async train(n_episodes: number, env_config?: RLEnvironmentConfig): Promise<EpisodeStats[]> {
    console.log(`🚀 Starting training for ${n_episodes} episodes...`);
    
    const results: EpisodeStats[] = [];
    
    for (let i = 0; i < n_episodes; i++) {
      const stats = await this.run_episode(null, env_config);
      results.push(stats);
      
      // Log progress
      if ((i + 1) % 10 === 0) {
        const recent = results.slice(-10);
        const avg_reward = recent.reduce((sum, s) => sum + s.total_reward, 0) / recent.length;
        console.log(`📈 Progress: ${i + 1}/${n_episodes} | Avg reward: ${avg_reward.toFixed(2)} | ε: ${this.config.epsilon.toFixed(3)}`);
      }
    }

    // Update policy after training
    await this.update_policy();
    
    console.log(`🎉 Training complete! Final avg reward: ${results.reduce((s, e) => s + e.total_reward, 0) / results.length.toFixed(2)}`);
    
    return results;
  }

  // Get learned policy
  async get_policy(): Promise<Policy> {
    if (!this.policy) {
      await this.update_policy();
    }
    return this.policy!;
  }

  // Store transition in pgvector
  private async store_transition(
    state: RLState,
    action: RLAction,
    reward: number,
    episode: number,
    step: number
  ): Promise<void> {
    try {
      const embedding = await this.embedding.embed(
        `state:${JSON.stringify(state.observation)} action:${action.action} reward:${reward}`
      );

      await this.memory_pool.query(
        `INSERT INTO rl_transitions (episode, step, state_embedding, action, reward, created_at)
         VALUES ($1, $2, $3, $4, $5, NOW())`,
        [episode, step, JSON.stringify(embedding), JSON.stringify(action), reward]
      );
    } catch (err) {
      // Table might not exist, create it
      await this.create_tables();
    }
  }

  private async create_tables(): Promise<void> {
    await this.memory_pool.query(`
      CREATE TABLE IF NOT EXISTS rl_transitions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        episode INTEGER NOT NULL,
        step INTEGER NOT NULL,
        state_embedding JSONB,
        action JSONB,
        reward REAL,
        created_at TIMESTAMP DEFAULT NOW()
      )
    `);
  }

  private async update_policy(): Promise<void> {
    // Compute policy from episode history
    const recent = this.episode_history.slice(-100);
    
    if (recent.length === 0) {
      this.policy = {
        id: 'default',
        name: 'default-policy',
        version: 1,
        created_at: new Date(),
        parameters: { epsilon: this.config.epsilon },
        embeddings: []
      };
      return;
    }

    // Aggregate best actions per state cluster
    const action_counts: Record<string, number> = {};
    for (const episode of recent) {
      for (const action of episode.actions) {
        const key = String(action.action);
        action_counts[key] = (action_counts[key] || 0) + 1;
      }
    }

    // Get embedding for policy
    const policy_text = `policy:${JSON.stringify(action_counts)}`;
    const policy_embedding = await this.embedding.embed(policy_text);

    // Find best actions
    const best_action = Object.entries(action_counts)
      .sort(([, a], [, b]) => b - a)[0]?.[0] || 'explore';

    this.policy = {
      id: `policy-v${this.current_episode}`,
      name: `learned-policy-${Date.now()}`,
      version: this.current_episode,
      created_at: new Date(),
      parameters: {
        epsilon: this.config.epsilon,
        learning_rate: this.config.learning_rate,
        gamma: this.config.gamma,
        best_action,
        action_distribution: action_counts
      },
      embeddings: policy_embedding
    };

    // Store policy in database
    try {
      await this.memory_pool.query(
        `INSERT INTO rl_policies (id, name, version, parameters, embeddings, created_at)
         VALUES ($1, $2, $3, $4, $5, NOW())`,
        [this.policy.id, this.policy.name, this.policy.version, JSON.stringify(this.policy.parameters), JSON.stringify(this.policy.embeddings)]
      );
    } catch {
      // Table might not exist
      await this.memory_pool.query(`
        CREATE TABLE IF NOT EXISTS rl_policies (
          id UUID PRIMARY KEY,
          name TEXT,
          version INTEGER,
          parameters JSONB,
          embeddings JSONB,
          created_at TIMESTAMP DEFAULT NOW()
        )
      `);
    }
  }

  // Get episode history
  get_history(): EpisodeStats[] {
    return this.episode_history;
  }

  // Cleanup
  async close(): Promise<void> {
    await this.memory_pool.end();
  }
}

// ============ OPENCLAW HOOK EXPORT ============

export default async function handler(event: any): Promise<any> {
  console.log('🎯 rl-harness:', event.type);

  // Supported event types
  const validEvents = [
    'rl:run_episode',
    'rl:train',
    'rl:get_policy',
    'rl:initialize',
    'action:rl_train',
    'action:rl_run'
  ];

  // Check if this is an RL-related event
  const isRlEvent = validEvents.includes(event.type) || 
    (event.action && event.action.startsWith('rl_'));

  if (!isRlEvent) {
    return event;
  }

  // Extract configuration
  const config: Partial<RLHarnessConfig> = event.rl_config || {};
  const env_config: RLEnvironmentConfig = event.env_config || {
    name: 'default',
    state_dim: 128,
    action_space: 'discrete',
    n_actions: 4,
    max_steps: 50
  };

  // Create harness
  const harness = new RLHarness(config);

  try {
    switch (event.type) {
      case 'rl:initialize':
      case 'action:rl_init':
        harness.initialize_env(env_config);
        event.response = { status: 'initialized', env: env_config.name };
        break;

      case 'rl:run_episode':
      case 'action:rl_run':
        const episode_stats = await harness.run_episode(event.agent, env_config);
        event.response = {
          status: 'episode_complete',
          stats: {
            episode: episode_stats.episode,
            total_reward: episode_stats.total_reward,
            steps: episode_stats.steps,
            duration_ms: episode_stats.duration_ms
          }
        };
        break;

      case 'rl:train':
      case 'action:rl_train':
        const n_episodes = event.n_episodes || 10;
        const training_results = await harness.train(n_episodes, env_config);
        event.response = {
          status: 'training_complete',
          n_episodes: training_results.length,
          avg_reward: training_results.reduce((s, e) => s + e.total_reward, 0) / training_results.length,
          final_policy: await harness.get_policy()
        };
        break;

      case 'rl:get_policy':
        const policy = await harness.get_policy();
        event.response = { policy };
        break;

      default:
        event.response = { status: 'unknown_action' };
    }
  } catch (error: any) {
    console.error('❌ RL Harness error:', error);
    event.response = { status: 'error', error: error.message };
  } finally {
    await harness.close();
  }

  return event;
}
