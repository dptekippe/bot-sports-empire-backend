/**
 * RL Harness Environment - Integration Examples
 * 
 * Demonstrates 3 usage patterns for rl_harness_env.ts
 * Uses OpenClaw hook integration with pgvector_memory_hook.
 */

import {
  RLHarnessEnv,
  createRLEnvironment,
  RLState,
  DiscreteAction,
  ActionType,
  RewardShaper
} from './rl_harness_env';

// ============ EXAMPLE 1: Basic Episode Collection ============

async function exampleBasicEpisodeCollection(): Promise<void> {
  console.log('=== Example 1: Basic Episode Collection ===');

  const env = createRLEnvironment({
    connectionString: process.env.DATABASE_URL || 'postgresql://user:pass@localhost:5432/memories',
    maxStepsPerEpisode: 20,
    darwinSwarmEnabled: true,
    neuralFusionEnabled: true
  });

  // Reset environment with OpenClaw message context
  const initialState = env.reset({
    sessionId: 'session-123',
    channel: 'webchat',
    message: {
      id: 'msg-001',
      content: 'What is the weather in Chicago?',
      author: { id: 'user-1', name: 'Daniel', role: 'user' },
      timestamp: new Date().toISOString()
    },
    history: []
  });

  console.log('Initial state episode:', initialState.episode);
  console.log('Similar episodes found:', initialState.similarEpisodes.length);
  console.log('Darwin-swarm phase:', initialState.darwinSwarm.phase);
  console.log('NeuralFusion stage:', initialState.neuralFusion?.stage);

  // Simulate action loop
  const actions: DiscreteAction[] = [
    { type: ActionType.TOOL_CALL, payload: 'weather', toolArgs: { location: 'Chicago' } },
    { type: ActionType.MESSAGE_RESPONSE, payload: 'The weather in Chicago is sunny and 72°F.' }
  ];

  for (const action of actions) {
    const result = env.step(action);
    console.log(`Action: ${action.type} | Reward: ${result.reward} | Done: ${result.done}`);
    
    if (result.done) break;
  }

  console.log('Episode complete. Total steps:', env.getStep());
}

// ============ EXAMPLE 2: Custom Reward Shaper Integration ============

async function exampleCustomRewardShaper(): Promise<void> {
  console.log('\n=== Example 2: Custom Reward Shaper ===');

  // Custom reward shaper (placeholder - will integrate with rl_reward_shaper.ts)
  const customShaper: RewardShaper = {
    compute(state, action, nextState, done) {
      let reward = 0.0;

      // Reward for tool calls (exploration)
      if (action.type === ActionType.TOOL_CALL) {
        reward += 0.1;
      }

      // Reward for successful message response
      if (action.type === ActionType.MESSAGE_RESPONSE && action.payload.length > 10) {
        reward += 0.2;
      }

      // Bonus for using similar episode context
      if (state.similarEpisodes.length > 0) {
        reward += 0.05 * state.similarEpisodes.length;
      }

      // Bonus for darwin-swarm progress
      if (nextState.darwinSwarm.phase !== state.darwinSwarm.phase) {
        reward += 0.15;
      }

      // Large reward for episode completion
      if (done) {
        reward += 1.0;
      }

      return reward;
    }
  };

  const env = createRLEnvironment({
    rewardShaper: customShaper,
    darwinSwarmEnabled: true,
    neuralFusionEnabled: false
  });

  const state = env.reset({
    sessionId: 'session-456',
    channel: 'webchat',
    message: {
      id: 'msg-002',
      content: 'Search for DynastyDroid on GitHub',
      author: { id: 'user-2', name: 'Roger', role: 'bot' },
      timestamp: new Date().toISOString()
    },
    history: [
      { role: 'user', content: 'Hello', timestamp: new Date().toISOString() }
    ]
  });

  console.log('State features dimensions:', state.featureVector.length);

  const action: DiscreteAction = {
    type: ActionType.TOOL_CALL,
    payload: 'web_search',
    toolArgs: { query: 'DynastyDroid GitHub' }
  };

  const result = env.step(action);
  console.log('Custom reward:', result.reward);
  console.log('Info:', result.info);
}

// ============ EXAMPLE 3: Full RL Loop with Episode Storage ============

async function exampleFullRLLoop(): Promise<void> {
  console.log('\n=== Example 3: Full RL Loop with Episode Storage ===');

  const env = createRLEnvironment({
    connectionString: process.env.DATABASE_URL || 'postgresql://user:pass@localhost:5432/memories',
    maxStepsPerEpisode: 50,
    darwinSwarmEnabled: true,
    neuralFusionEnabled: true
  });

  // Simulate a conversation loop
  const conversation = [
    { role: 'user', content: 'What bots are registered on DynastyDroid?' },
    { role: 'assistant', content: 'I can search for that.' },
    { role: 'user', content: 'Find Roger the Robot' }
  ];

  const state = env.reset({
    sessionId: 'session-789',
    channel: 'webchat',
    message: {
      id: 'msg-003',
      content: conversation[2].content,
      author: { id: 'user-3', name: 'Daniel', role: 'user' },
      timestamp: new Date().toISOString()
    },
    history: conversation.slice(0, 2).map((c, i) => ({
      ...c,
      timestamp: new Date(Date.now() - (2 - i) * 60000).toISOString()
    }))
  });

  console.log('Episode:', state.episode);
  console.log('Darwin-swarm candidates:', state.darwinSwarm.candidates.length);

  // RL action loop
  let totalReward = 0;
  let step = 0;
  const maxSteps = 5;

  while (step < maxSteps) {
    // Policy: choose action based on state (placeholder)
    const action: DiscreteAction = step % 2 === 0
      ? { type: ActionType.TOOL_CALL, payload: 'memory:search', toolArgs: { query: state.message.content } }
      : { type: ActionType.MESSAGE_RESPONSE, payload: `Found information about ${state.message.content}` };

    const result = env.step(action);
    totalReward += result.reward;
    step++;

    console.log(`Step ${step}: action=${action.type}, reward=${result.reward.toFixed(3)}, done=${result.done}`);

    if (result.done) {
      console.log('Episode terminated.');
      break;
    }
  }

  console.log(`Episode ${state.episode} complete. Total reward: ${totalReward.toFixed(3)}`);
  console.log('Episodes stored in pgvector via embed_episode()');
}

// ============ RUN EXAMPLES ============

async function main(): Promise<void> {
  console.log('RL Harness Environment - Integration Examples\n');

  try {
    await exampleBasicEpisodeCollection();
    await exampleCustomRewardShaper();
    await exampleFullRLLoop();
    
    console.log('\n✓ All examples completed');
  } catch (error) {
    console.error('Example failed:', error);
  }
}

// Run if executed directly
main().catch(console.error);

export {
  exampleBasicEpisodeCollection,
  exampleCustomRewardShaper,
  exampleFullRLLoop
};
