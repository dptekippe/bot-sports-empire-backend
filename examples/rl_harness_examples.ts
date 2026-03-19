/**
 * RL Harness Examples - TypeScript for OpenClaw
 * 
 * Usage examples for the RL harness hook.
 * Demonstrates:
 * - Single episode execution
 * - Training loop
 * - Policy retrieval
 * - Custom environment configuration
 * - Integration with OpenClaw events
 */

import { RLHarness, RLHarnessConfig, RLEnvironmentConfig, EpisodeStats, Policy } from '../hooks/rl_harness_hook';

// ============ EXAMPLE 1: Basic Single Episode ============

export async function example_single_episode(): Promise<EpisodeStats> {
  // Configuration
  const config: Partial<RLHarnessConfig> = {
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

  // Environment configuration
  const env_config: RLEnvironmentConfig = {
    name: 'fantasy-draft',
    state_dim: 128,
    action_space: 'discrete',
    n_actions: 4, // explore, exploit, wait, adapt
    max_steps: 50,
    reward_fn: 'draft_optimization'
  };

  // Create harness
  const harness = new RLHarness(config);

  try {
    // Initialize environment
    harness.initialize_env(env_config);

    // Run single episode
    const stats = await harness.run_episode(null, env_config);

    console.log('Episode Results:');
    console.log(`  Episode: ${stats.episode}`);
    console.log(`  Total Reward: ${stats.total_reward.toFixed(2)}`);
    console.log(`  Steps: ${stats.steps}`);
    console.log(`  Duration: ${stats.duration_ms}ms`);

    return stats;
  } finally {
    await harness.close();
  }
}

// ============ EXAMPLE 2: Training Loop ============

export async function example_training(): Promise<EpisodeStats[]> {
  const config: Partial<RLHarnessConfig> = {
    connectionString: process.env.DATABASE_URL || 'postgresql://user:pass@localhost:5432/rl_agent',
    learning_rate: 0.001,
    gamma: 0.99,
    epsilon: 1.0,
    epsilon_decay: 0.995,
    epsilon_min: 0.01,
    factcheck_enabled: true,
    self_improve_enabled: true
  };

  const env_config: RLEnvironmentConfig = {
    name: 'trade-evaluation',
    state_dim: 256,
    action_space: 'discrete',
    n_actions: 5, // buy, sell, hold, research, pass
    max_steps: 100,
    reward_fn: 'trade_value'
  };

  const harness = new RLHarness(config);

  try {
    harness.initialize_env(env_config);

    // Train for 50 episodes
    const results = await harness.train(50, env_config);

    console.log('\n📊 Training Summary:');
    console.log(`  Total Episodes: ${results.length}`);
    console.log(`  Final Avg Reward: ${results.reduce((s, e) => s + e.total_reward, 0) / results.length.toFixed(2)}`);
    console.log(`  Best Episode: ${Math.max(...results.map(r => r.total_reward)).toFixed(2)}`);
    console.log(`  Worst Episode: ${Math.min(...results.map(r => r.total_reward)).toFixed(2)}`);

    return results;
  } finally {
    await harness.close();
  }
}

// ============ EXAMPLE 3: Policy Retrieval ============

export async function example_get_policy(): Promise<Policy> {
  const harness = new RLHarness();

  try {
    // Get current policy (from training if done)
    const policy = await harness.get_policy();

    console.log('\n📋 Policy Details:');
    console.log(`  ID: ${policy.id}`);
    console.log(`  Name: ${policy.name}`);
    console.log(`  Version: ${policy.version}`);
    console.log(`  Created: ${policy.created_at}`);
    console.log(`  Parameters:`);
    console.log(`    Epsilon: ${policy.parameters.epsilon}`);
    console.log(`    Learning Rate: ${policy.parameters.learning_rate}`);
    console.log(`    Best Action: ${policy.parameters.best_action}`);

    return policy;
  } finally {
    await harness.close();
  }
}

// ============ EXAMPLE 4: Custom Reward Function ============

export async function example_custom_reward(): Promise<void> {
  // Create harness with custom config
  const harness = new RLHarness({
    connectionString: process.env.DATABASE_URL || 'postgresql://user:pass@localhost:5432/rl_agent',
    learning_rate: 0.0005, // Slower learning for fine-tuning
    gamma: 0.995, // Longer horizon
    epsilon: 0.3, // Less exploration
    factcheck_enabled: true,
    factcheck_strictness: 0.9, // Stricter validation
    self_improve_enabled: true,
    self_improve_threshold: 0.4 // Lower threshold for improvements
  });

  const env_config: RLEnvironmentConfig = {
    name: 'dynasty-pick',
    state_dim: 512,
    action_space: 'discrete',
    n_actions: 3, // draft_qb, draft_rb, draft_wr
    max_steps: 20,
    reward_fn: 'player_value'
  };

  try {
    harness.initialize_env(env_config);

    // Run episode with custom settings
    const stats = await harness.run_episode(null, env_config);

    console.log('Custom Reward Episode:', stats.total_reward.toFixed(2));
  } finally {
    await harness.close();
  }
}

// ============ EXAMPLE 5: OpenClaw Event Integration ============

/**
 * Example of how the hook integrates with OpenClaw events
 * This would be used in the OpenClaw hooks system
 */
export async function example_event_integration(): Promise<any> {
  // Simulated OpenClaw event
  const event = {
    type: 'rl:train',
    agent: { id: 'agent-123', name: 'DraftBot' },
    rl_config: {
      learning_rate: 0.001,
      gamma: 0.99,
      epsilon: 1.0,
      factcheck_enabled: true,
      self_improve_enabled: true
    },
    env_config: {
      name: 'mock-draft',
      state_dim: 128,
      action_space: 'discrete',
      n_actions: 4,
      max_steps: 50
    },
    n_episodes: 10,
    messages: [],
    context: {}
  };

  // Import and call the handler
  // const handler = require('../hooks/rl_harness_hook').default;
  // const result = await handler(event);

  console.log('Event Integration Example:');
  console.log('  Input Event:', event.type);
  console.log('  Episodes:', event.n_episodes);

  // Simulate response
  const response = {
    status: 'training_complete',
    n_episodes: event.n_episodes,
    avg_reward: 12.5,
    final_policy: {
      id: 'policy-v10',
      name: 'learned-policy',
      version: 10,
      parameters: {
        epsilon: 0.6,
        best_action: 'exploit'
      }
    }
  };

  console.log('  Response:', JSON.stringify(response, null, 2));

  return response;
}

// ============ EXAMPLE 6: Fantasy Sports Draft Scenario ============

export async function example_fantasy_draft(): Promise<EpisodeStats[]> {
  console.log('\n🏈 Fantasy Draft RL Training Scenario');

  const harness = new RLHarness({
    connectionString: process.env.DATABASE_URL || 'postgresql://user:pass@localhost:5432/rl_agent',
    learning_rate: 0.002,
    gamma: 0.98,
    epsilon: 1.0,
    epsilon_decay: 0.99,
    epsilon_min: 0.05,
    mcts_simulations: 30,
    factcheck_enabled: true,
    factcheck_strictness: 0.8,
    self_improve_enabled: true,
    self_improve_threshold: 0.5
  });

  // Fantasy draft environment
  const env_config: RLEnvironmentConfig = {
    name: 'fantasy-football-draft',
    state_dim: 256,
    action_space: 'discrete',
    n_actions: 5, // draft_best_available, draft_qb, draft_rb, draft_wr, draft_te
    max_steps: 20, // 20-round draft
    reward_fn: 'projected_points'
  };

  try {
    harness.initialize_env(env_config);

    // Train for 100 drafts
    console.log('Training on 100 mock drafts...');
    const results = await harness.train(100, env_config);

    // Get learned policy
    const policy = await harness.get_policy();

    console.log('\n🎯 Draft Policy Learned:');
    console.log(`  Best Strategy: ${policy.parameters.best_action}`);
    console.log(`  Action Distribution:`, policy.parameters.action_distribution);
    console.log(`  Exploration Rate (ε): ${policy.parameters.epsilon.toFixed(3)}`);

    return results;
  } finally {
    await harness.close();
  }
}

// ============ EXAMPLE 7: Debug Mode (No External Dependencies) ============

export async function example_debug_mode(): Promise<void> {
  // Debug mode uses fallback embeddings and in-memory storage
  const harness = new RLHarness({
    // Use invalid connection to trigger debug/fallback mode
    connectionString: 'postgresql://debug:debug@localhost:5432/debug',
    learning_rate: 0.001,
    gamma: 0.99,
    epsilon: 1.0,
    factcheck_enabled: false, // Disable for faster testing
    self_improve_enabled: false
  });

  const env_config: RLEnvironmentConfig = {
    name: 'debug-env',
    state_dim: 16,
    action_space: 'discrete',
    n_actions: 2,
    max_steps: 5
  };

  try {
    harness.initialize_env(env_config);

    // Quick single episode
    const stats = await harness.run_episode(null, env_config);

    console.log('\n🔍 Debug Episode:');
    console.log(`  Steps: ${stats.steps}`);
    console.log(`  Total Reward: ${stats.total_reward.toFixed(4)}`);
    console.log(`  Actions: ${stats.actions.map(a => a.action).join(', ')}`);
  } finally {
    await harness.close();
  }
}

// ============ RUN ALL EXAMPLES ============

export async function run_all_examples(): Promise<void> {
  console.log('='.repeat(50));
  console.log('RL Harness Examples');
  console.log('='.repeat(50));

  try {
    await example_single_episode();
    // await example_training();
    // await example_get_policy();
    // await example_custom_reward();
    // await example_event_integration();
    // await example_fantasy_draft();
    // await example_debug_mode();
  } catch (error) {
    console.error('Example error:', error);
  }
}

// Run if called directly
// run_all_examples();
