/**
 * RL Reward Shaper - Integration Examples
 * 
 * 3 complete integration examples showing:
 * 1. Basic reward shaping with PPO advantage + CFR
 * 2. Multi-hypothesis Darwin-swarm selection
 * 3. Full episode loop with bias detection
 */

import {
  shape_reward,
  advantage_from_pgvector,
  compute_cfr_trace,
  neural_fuse,
  select_reward_hypothesis,
  biascheck_gym,
  RewardShaperImpl,
  CFR_TEMPORAL_WEIGHTS,
  type ShapedReward,
  type RewardHypothesis,
  type CFRTrace,
  type AdvantageResult
} from '../hooks/rl_reward_shaper';

// ============ MOCK STATE BUILDER ============

function buildMockState(overrides: Partial<RLState> = {}): RLState {
  return {
    sessionId: 'session-123',
    channel: 'webchat',
    message: {
      id: 'msg-456',
      content: 'What is the weather in Chicago?',
      author: { id: 'user-789', name: 'Daniel', role: 'user' },
      timestamp: new Date().toISOString()
    },
    history: [
      { role: 'user', content: 'Hello there', timestamp: new Date().toISOString() }
    ],
    similarEpisodes: [
      {
        id: 'ep-1',
        content: 'Weather query for New York → response with sunny forecast',
        reward: 0.8,
        similarity: 0.85,
        importance: 7,
        episode: 10,
        step: 3
      },
      {
        id: 'ep-2',
        content: 'Weather query for Boston → response with rain forecast',
        reward: 0.6,
        similarity: 0.72,
        importance: 6,
        episode: 8,
        step: 5
      },
      {
        id: 'ep-3',
        content: 'Weather query for LA → response with cloudy forecast',
        reward: 0.5,
        similarity: 0.65,
        importance: 5,
        episode: 12,
        step: 1
      }
    ],
    darwinSwarm: {
      candidates: [
        { id: 'candidate-1', score: 0.8, reasoning: 'Use weather API tool' },
        { id: 'candidate-2', score: 0.6, reasoning: 'Use cached weather data' },
        { id: 'candidate-3', score: 0.4, reasoning: 'Generic weather response' }
      ],
      selected: null,
      phase: 'generation',
      iteration: 0
    },
    neuralFusion: {
      stage: 2,
      traces: [
        'ep-10: weather_query → tool_call → success',
        'ep-8: weather_query → tool_call → partial'
      ],
      fusedEmbedding: Array(768).fill(0).map(() => Math.random() * 0.1)
    },
    episode: 15,
    step: 2,
    featureVector: Array(768).fill(0).map((_, i) => i < 10 ? 0.5 : 0),
    ...overrides
  };
}

function buildMockAction(type: 'tool_call' | 'message_response' = 'tool_call'): DiscreteAction {
  return {
    type,
    payload: 'get_weather',
    toolArgs: { location: 'Chicago', format: 'fahrenheit' }
  };
}

interface RLState {
  sessionId: string;
  channel: string;
  message: {
    id: string;
    content: string;
    author: { id: string; name: string; role: string };
    timestamp: string;
  };
  history: Array<{ role: string; content: string; timestamp: string }>;
  similarEpisodes: Array<{
    id?: string;
    content: string;
    embedding?: number[];
    memory_type?: string;
    tags?: string[];
    importance?: number;
    reward?: number;
    episode?: number;
    step?: number;
    similarity?: number;
  }>;
  darwinSwarm: {
    candidates: Array<{ id: string; score: number; reasoning: string }>;
    selected: string | null;
    phase: 'generation' | 'selection' | 'execution';
    iteration: number;
  };
  neuralFusion: {
    stage: number;
    traces: string[];
    fusedEmbedding: number[];
  } | null;
  episode: number;
  step: number;
  featureVector: number[];
}

interface DiscreteAction {
  type: 'tool_call' | 'message_response';
  payload: string;
  toolArgs?: Record<string, unknown>;
}

// ============ EXAMPLE 1: BASIC REWARD SHAPING ============

export function example1_BasicRewardShaping(): void {
  console.log('\n========== EXAMPLE 1: Basic Reward Shaping ==========\n');

  // Setup
  const state = buildMockState({ episode: 1, step: 1 });
  const action = buildMockAction('tool_call');
  const raw_reward = 1.0; // Environment gives positive reward

  const pgvector_context = {
    db: null,
    embedder: null,
    connectionString: 'postgresql://user:pass@localhost:5432/memories'
  };

  // Compute shaped reward
  const result: ShapedReward = shape_reward(state, action, raw_reward, pgvector_context);

  console.log('Raw Reward:', raw_reward);
  console.log('Shaped Reward:', result.shaped.toFixed(4));
  console.log('\nComponents:');
  console.log('  Advantage:', result.components.advantage.toFixed(4));
  console.log('  CFR:', result.components.cfr.toFixed(4));
  console.log('  NeuralFusion:', result.components.neuralFusion.toFixed(4));
  console.log('  Darwin:', result.components.darwinSelection.toFixed(4));

  console.log('\nBias Check:');
  console.log('  Is Biased:', result.biasCheck.isBiased);
  console.log('  Bias Score:', result.biasCheck.biasScore.toFixed(4));
  console.log('  Flagged:', result.biasCheck.flaggedHypotheses);

  console.log('\nCFR Trace:');
  if (result.metadata.cfrTrace) {
    const cfr = result.metadata.cfrTrace;
    console.log('  Expected Value:', cfr.expectedValue.toFixed(4));
    console.log('  Counterfactual Delta:', cfr.counterfactualDelta.toFixed(4));
    console.log('  Temporal Slices:', cfr.temporalSlices.length);
    cfr.temporalSlices.forEach((slice, i) => {
      console.log(`    Slice ${i}: weight=${slice.weight}, reward=${slice.projectedReward.toFixed(3)}`);
    });
  }

  console.log('\n✓ Basic reward shaping complete\n');
}

// ============ EXAMPLE 2: MULTI-HYPOTHESIS DARWIN-SWARM ============

export function example2_MultiHypothesisDarwinSwarm(): void {
  console.log('\n========== EXAMPLE 2: Multi-Hypothesis Darwin-Swarm ==========\n');

  // Create multiple reward hypotheses
  const hypotheses: RewardHypothesis[] = [
    {
      id: 'h-ppo',
      signal: 0.75,
      source: 'advantage',
      confidence: 0.9,
      reasoning: 'Strong advantage from similar historical episodes'
    },
    {
      id: 'h-cfr',
      signal: 0.45,
      source: 'cfr',
      confidence: 0.6,
      reasoning: 'Moderate counterfactual benefit from alternative actions'
    },
    {
      id: 'h-neural',
      signal: 0.90,
      source: 'neural_fusion',
      confidence: 0.7,
      reasoning: 'High neural fusion alignment with memory patterns'
    },
    {
      id: 'h-darwin',
      signal: 0.30,
      source: 'darwin',
      confidence: 0.5,
      reasoning: 'Lower Darwin selection due to recent failures'
    }
  ];

  console.log('Hypotheses:');
  hypotheses.forEach(h => {
    console.log(`  [${h.id}] signal=${h.signal.toFixed(2)}, confidence=${h.confidence.toFixed(2)}`);
  });

  // Run Darwin-swarm selection (10 times to show randomness)
  console.log('\nDarwin-Swarm Selection (10 runs):');
  const selections: Record<string, number> = {};
  for (let i = 0; i < 10; i++) {
    const selected = select_reward_hypothesis(hypotheses);
    selections[selected.id] = (selections[selected.id] || 0) + 1;
    console.log(`  Run ${i + 1}: Selected ${selected.id} (${selected.source})`);
  }

  console.log('\nSelection Distribution:');
  Object.entries(selections).forEach(([id, count]) => {
    console.log(`  ${id}: ${count}/10 (${(count * 10)}%)`);
  });

  // Now test with all high confidence (groupthink scenario)
  const unanimousHypotheses = hypotheses.map(h => ({ ...h, confidence: 0.95 }));
  console.log('\nBias Check (unanimous high confidence):');
  const components = {
    advantage: 0.75,
    cfr: 0.45,
    neuralFusion: 0.90,
    darwinSelection: 0.30
  };
  const biasResult = biascheck_gym(0.6, components, unanimousHypotheses);
  console.log('  Is Biased:', biasResult.isBiased);
  console.log('  Bias Score:', biasResult.biasScore.toFixed(4));
  console.log('  Flagged:', biasResult.flaggedHypotheses);

  console.log('\n✓ Darwin-swarm selection complete\n');
}

// ============ EXAMPLE 3: FULL EPISODE LOOP WITH BIAS DETECTION ============

export function example3_FullEpisodeLoop(): void {
  console.log('\n========== EXAMPLE 3: Full Episode Loop with Bias Detection ==========\n');

  // Initialize reward shaper
  const rewardShaper = new RewardShaperImpl(
    'http://localhost:8080/futureself',
    null,
    null,
    { enabled: true, threshold: 0.3 }
  );

  // Simulate episode with 5 steps
  const episodeSteps = [
    { step: 1, message: 'Hello bot!', action: 'tool_call', expected_reward: 0.1 },
    { step: 2, message: 'What is DynastyDroid?', action: 'tool_call', expected_reward: 0.3 },
    { step: 3, message: 'Show me leagues', action: 'tool_call', expected_reward: 0.5 },
    { step: 4, message: 'Who won last week?', action: 'tool_call', expected_reward: 0.4 },
    { step: 5, message: 'Thanks!', action: 'message_response', expected_reward: 0.2 }
  ];

  let totalReward = 0;
  const episodeRewards: number[] = [];
  const biasFlags: string[][] = [];

  console.log('Episode 42 - Step-by-Step Reward Shaping:\n');
  console.log('Step | Raw R | Shaped R | Bias Score | Flags');
  console.log('-----|-------|----------|------------|------');

  for (const stepData of episodeSteps) {
    const state = buildMockState({
      episode: 42,
      step: stepData.step,
      message: {
        ...buildMockState().message,
        content: stepData.message
      },
      darwinSwarm: {
        candidates: [
          { id: 'candidate-1', score: 0.8, reasoning: 'Tool approach' },
          { id: 'candidate-2', score: 0.5, reasoning: 'Direct response' }
        ],
        selected: stepData.step > 2 ? 'candidate-1' : null,
        phase: stepData.step > 3 ? 'execution' : 'selection',
        iteration: stepData.step
      }
    });

    const action = buildMockAction(stepData.action as 'tool_call' | 'message_response');

    // Full analysis
    const analysis = rewardShaper.analyze(state, action);

    totalReward += analysis.shaped;
    episodeRewards.push(analysis.shaped);
    biasFlags.push(analysis.biasCheck.flaggedHypotheses);

    console.log(
      `  ${stepData.step}  | ${stepData.expected_reward.toFixed(2)}  |   ${analysis.shaped.toFixed(3)}  |    ${analysis.biasCheck.biasScore.toFixed(2)}   | ${
        analysis.biasCheck.flaggedHypotheses.length > 0
          ? analysis.biasCheck.flaggedHypotheses.join(', ')
          : '-'
      }`
    );
  }

  console.log('\n--- Episode Summary ---');
  console.log('Total Shaped Reward:', totalReward.toFixed(3));
  console.log('Average Reward:', (totalReward / episodeSteps.length).toFixed(3));
  console.log('Max Reward:', Math.max(...episodeRewards).toFixed(3));
  console.log('Min Reward:', Math.min(...episodeRewards).toFixed(3));

  // Analyze bias patterns
  const allFlags = biasFlags.flat();
  const flagCounts: Record<string, number> = {};
  allFlags.forEach(f => { flagCounts[f] = (flagCounts[f] || 0) + 1; });

  console.log('\nBias Pattern Analysis:');
  if (Object.keys(flagCounts).length === 0) {
    console.log('  No bias detected across episode');
  } else {
    Object.entries(flagCounts).forEach(([flag, count]) => {
      console.log(`  ${flag}: ${count}/${episodeSteps.length} steps`);
    });
  }

  // PPO Advantage Analysis
  console.log('\nPPO Advantage Analysis:');
  const state = buildMockState();
  const advantageResult = advantage_from_pgvector(state, 0.5, {
    db: null,
    embedder: null,
    connectionString: ''
  });
  console.log('  Baseline:', advantageResult.baseline.toFixed(4));
  console.log('  Raw Reward:', advantageResult.rawReward.toFixed(4));
  console.log('  Advantage:', advantageResult.advantage.toFixed(4));
  console.log('  Similar Episodes:', advantageResult.similarEpisodeCount);

  // CFR Trace Analysis
  console.log('\nCFR Temporal Weights:');
  CFR_TEMPORAL_WEIGHTS.forEach((w, i) => {
    console.log(`  Slice ${i}: ${w}`);
  });

  console.log('\n✓ Full episode loop complete\n');
}

// ============ RUN ALL EXAMPLES ============

export function runAllExamples(): void {
  console.log('\n========================================');
  console.log('RL REWARD SHAPER - INTEGRATION EXAMPLES');
  console.log('========================================');

  example1_BasicRewardShaping();
  example2_MultiHypothesisDarwinSwarm();
  example3_FullEpisodeLoop();

  console.log('========================================');
  console.log('All examples completed successfully!');
  console.log('========================================\n');
}

// Run if executed directly
if (require.main === module) {
  runAllExamples();
}
