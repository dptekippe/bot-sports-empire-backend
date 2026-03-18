/**
 * RL Reward Shaper - TypeScript Implementation
 * 
 * PPO-style advantage estimation with CFR counterfactual reasoning,
 * neural memory fusion, and Darwin-swarm evolutionary hypothesis selection.
 * 
 * Integrates with:
 *   - pgvector_memory_hook (rl:recall, rl:remember)
 *   - rl_harness_env (RewardShaper interface)
 *   - biascheck-gym (bias detection)
 *   - futureself (temporal projection model)
 * 
 * CFR temporal weights (7 slices): [0.12, 0.25, 0.20, 0.15, 0.12, 0.08, 0.08]
 */

// ============ TYPES & INTERFACES ============

export const CFR_TEMPORAL_WEIGHTS: number[] = [0.12, 0.25, 0.20, 0.15, 0.12, 0.08, 0.08];

export interface CFRTrace {
  action: string;
  alternatives: string[];
  temporalSlices: CFRTemporalSlice[];
  expectedValue: number;
  counterfactualDelta: number;
  biasDetected: boolean;
}

export interface CFRTemporalSlice {
  sliceIndex: number;
  weight: number;
  projectedReward: number;
  confidence: number;
}

export interface RewardHypothesis {
  id: string;
  signal: number;
  source: 'advantage' | 'cfr' | 'neural_fusion' | 'darwin';
  confidence: number;
  reasoning: string;
}

export interface NeuralFusionResult {
  fusedSignal: number;
  attentionWeights: number[];
  memoryContribution: number;
  stateContribution: number;
}

export interface AdvantageResult {
  rawReward: number;
  baseline: number;
  advantage: number;
  similarEpisodeCount: number;
}

export interface BiasCheckResult {
  isBiased: boolean;
  biasScore: number;
  groupDeltas: Record<string, number>;
  flaggedHypotheses: string[];
}

export interface ShapedReward {
  shaped: number;
  components: {
    advantage: number;
    cfr: number;
    neuralFusion: number;
    darwinSelection: number;
  };
  biasCheck: BiasCheckResult;
  metadata: {
    episode: number;
    step: number;
    cfrTrace: CFRTrace | null;
    selectedHypothesis: string | null;
    neuralFusion: NeuralFusionResult | null;
  };
}

// State types from rl_harness_env
interface RLState {
  sessionId: string;
  channel: string;
  message: {
    id: string;
    content: string;
    author: { id: string; name: string; role: string };
    timestamp: string;
  };
  history: Array<{
    role: string;
    content: string;
    timestamp: string;
  }>;
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
    candidates: Array<{
      id: string;
      score: number;
      reasoning: string;
    }>;
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

interface MemorySearchResult {
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
}

interface RLMemoryContext {
  episode: number;
  step: number;
  state: string;
  action: string;
  reward: number;
  done: boolean;
}

interface BiasCheckConfig {
  enabled: boolean;
  threshold?: number;
  protectedGroups?: string[];
}

// ============ CORE FUNCTIONS ============

/**
 * Compute shaped reward integrating all RL signals
 */
export function shape_reward(
  state: RLState,
  action: DiscreteAction,
  raw_reward: number,
  pgvector_context: {
    db: any;
    embedder: any;
    connectionString: string;
  }
): ShapedReward {
  const hypothesis: RewardHypothesis[] = [];

  // 1. PPO-style advantage from pgvector historical patterns
  const advantageResult = advantage_from_pgvector(state, raw_reward, pgvector_context);
  hypothesis.push({
    id: 'h-advantage',
    signal: advantageResult.advantage,
    source: 'advantage',
    confidence: Math.min(advantageResult.similarEpisodeCount * 0.2, 0.9),
    reasoning: `Baseline ${advantageResult.baseline.toFixed(3)} vs raw ${raw_reward.toFixed(3)}`
  });

  // 2. CFR counterfactual reasoning via futureself
  const cfrTrace = compute_cfr_trace(
    action.payload,
    state.similarEpisodes.slice(0, 3).map(e => e.content),
    state
  );
  hypothesis.push({
    id: 'h-cfr',
    signal: cfrTrace.expectedValue,
    source: 'cfr',
    confidence: cfrTrace.temporalSlices.length / CFR_TEMPORAL_WEIGHTS.length,
    reasoning: `CFR delta: ${cfrTrace.counterfactualDelta.toFixed(3)}`
  });

  // 3. NeuralFusion reward signal
  const neuralResult = neural_fuse(state.featureVector, state.neuralFusion?.fusedEmbedding || []);
  hypothesis.push({
    id: 'h-neural',
    signal: neuralResult.fusedSignal,
    source: 'neural_fusion',
    confidence: 0.7,
    reasoning: `Mem:${neuralResult.memoryContribution.toFixed(2)} State:${neuralResult.stateContribution.toFixed(2)}`
  });

  // 4. Darwin-swarm selection
  const selectedHypothesis = select_reward_hypothesis(hypothesis);
  const darwinSignal = selectedHypothesis.signal;

  // Compute components
  const components = {
    advantage: advantageResult.advantage,
    cfr: cfrTrace.expectedValue,
    neuralFusion: neuralResult.fusedSignal,
    darwinSelection: darwinSignal
  };

  // Weighted combination with bias check
  const shaped = compute_shaped_reward(components);
  const biasCheck = biascheck_gym(shaped, components, hypothesis);

  return {
    shaped: biasCheck.isBiased ? shaped * (1 - biasCheck.biasScore * 0.5) : shaped,
    components,
    biasCheck,
    metadata: {
      episode: state.episode,
      step: state.step,
      cfrTrace,
      selectedHypothesis: selectedHypothesis.id,
      neuralFusion: neuralResult
    }
  };
}

/**
 * PPO-style advantage estimation: raw_reward - baseline (from pgvector)
 */
export function advantage_from_pgvector(
  state: RLState,
  raw_reward: number,
  pgvector_context: {
    db: any;
    embedder: any;
    connectionString: string;
  }
): AdvantageResult {
  const similarEpisodes = state.similarEpisodes || [];

  // Compute baseline from similar historical episodes
  let baseline = 0.0;
  if (similarEpisodes.length > 0) {
    // Weighted average of rewards from similar states (by cosine similarity)
    let weightSum = 0.0;
    let weightedSum = 0.0;
    for (const ep of similarEpisodes) {
      const sim = ep.similarity || 0.5;
      const rew = ep.reward ?? 0;
      const weight = sim * (ep.importance ?? 5) / 10;
      weightedSum += rew * weight;
      weightSum += weight;
    }
    baseline = weightSum > 0 ? weightedSum / weightSum : raw_reward;
  }

  // PPO-style advantage: clip raw reward to prevent blowup
  const rawAdvantage = raw_reward - baseline;
  const clippedAdvantage = Math.max(-5, Math.min(5, rawAdvantage));

  return {
    rawReward: raw_reward,
    baseline,
    advantage: clippedAdvantage,
    similarEpisodeCount: similarEpisodes.length
  };
}

/**
 * CFR (Counterfactual Reasoning) trace using futureself temporal model
 */
export function compute_cfr_trace(
  action: string,
  alternatives: string[],
  state: RLState
): CFRTrace {
  const temporalSlices: CFRTemporalSlice[] = [];

  // Query futureself for each temporal slice (simulated)
  for (let i = 0; i < CFR_TEMPORAL_WEIGHTS.length; i++) {
    const projectedReward = query_futureself(action, alternatives, state, i);
    temporalSlices.push({
      sliceIndex: i,
      weight: CFR_TEMPORAL_WEIGHTS[i],
      projectedReward,
      confidence: CFR_TEMPORAL_WEIGHTS[i] * 1.2 // confidence proportional to weight
    });
  }

  // Compute expected value across temporal slices
  let expectedValue = 0.0;
  for (const slice of temporalSlices) {
    expectedValue += slice.weight * slice.projectedReward;
  }

  // Counterfactual delta: difference between chosen action and best alternative
  const actionReward = query_futureself(action, [], state, -1);
  let counterfactualDelta = 0.0;
  if (alternatives.length > 0) {
    const bestAlternative = Math.max(
      ...alternatives.map(alt => query_futureself(alt, [], state, -1))
    );
    counterfactualDelta = actionReward - bestAlternative;
  }

  // Check for bias indicators in CFR
  const biasDetected = Math.abs(counterfactualDelta) > 2.0 ||
    temporalSlices.some(s => Math.abs(s.projectedReward) > 3.0);

  return {
    action,
    alternatives,
    temporalSlices,
    expectedValue,
    counterfactualDelta,
    biasDetected
  };
}

/**
 * Query futureself model for temporal projections (simulated endpoint)
 */
async function query_futureself(
  action: string,
  _alternatives: string[],
  state: RLState,
  temporalSlice: number
): Promise<number> {
  // In production, this calls the actual futureself temporal model endpoint
  // For now, simulate based on state/action features
  const baseReward = state.similarEpisodes.reduce(
    (sum, ep) => sum + (ep.reward ?? 0) * (ep.similarity ?? 0.5),
    0
  ) / Math.max(state.similarEpisodes.length, 1);

  // Apply temporal weighting if slice is specified
  const sliceWeight = temporalSlice >= 0 ? CFR_TEMPORAL_WEIGHTS[temporalSlice] || 1.0 : 1.0;

  // Simulate futureself projection
  const actionHash = action.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
  const stateHash = state.message.content.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
  const noise = ((actionHash * 31 + stateHash) % 100 - 50) / 50; // -1 to 1

  return (baseReward + noise * 0.5) * sliceWeight;
}

/**
 * NeuralFusion: fuse memory embeddings + current state into reward signal
 */
export function neural_fuse(
  state_embedding: number[],
  memory_embedding: number[]
): NeuralFusionResult {
  const dim = state_embedding.length || 768;

  // Use zero vectors if embeddings not provided
  const stateEmb = state_embedding.length === dim ? state_embedding : zero_vector(dim);
  const memEmb = memory_embedding.length === dim ? memory_embedding : zero_vector(dim);

  // Compute attention weights via dot product similarity
  const attentionWeights: number[] = [];
  let attentionSum = 0.0;

  for (let i = 0; i < Math.min(stateEmb.length, 10); i++) {
    const w = Math.exp(dot_product(stateEmb.slice(i * 10, (i + 1) * 10), memEmb.slice(i * 10, (i + 1) * 10)));
    attentionWeights.push(w);
    attentionSum += w;
  }

  // Normalize attention
  const normalizedWeights = attentionWeights.map(w => w / (attentionSum || 1));

  // Compute fused signal as weighted combination
  const fusedSignal = normalizedWeights.reduce(
    (sum, w, i) => sum + w * (stateEmb[i] + memEmb[i]) / 2,
    0
  ) * 2; // Scale up

  // Compute contributions
  const stateContribution = normalizedWeights.reduce(
    (sum, w, i) => sum + w * stateEmb[i],
    0
  );
  const memoryContribution = normalizedWeights.reduce(
    (sum, w, i) => sum + w * memEmb[i],
    0
  );

  return {
    fusedSignal: Math.max(-3, Math.min(3, fusedSignal)),
    attentionWeights: normalizedWeights,
    memoryContribution,
    stateContribution
  };
}

/**
 * Darwin-swarm evolutionary selection of reward hypothesis
 */
export function select_reward_hypothesis(hypotheses: RewardHypothesis[]): RewardHypothesis {
  if (hypotheses.length === 0) {
    return {
      id: 'h-default',
      signal: 0.0,
      source: 'advantage',
      confidence: 0.0,
      reasoning: 'No hypotheses available'
    };
  }

  if (hypotheses.length === 1) {
    return hypotheses[0];
  }

  // Darwin-swarm: evolutionary selection based on confidence-weighted signal
  // Higher confidence = more likely to be selected (natural selection)
  const totalWeight = hypotheses.reduce(
    (sum, h) => sum + h.confidence * h.confidence,
    0
  );

  // Fitness-proportionate selection
  let random = Math.random() * totalWeight;
  for (const hypothesis of hypotheses) {
    random -= hypothesis.confidence * hypothesis.confidence;
    if (random <= 0) {
      return hypothesis;
    }
  }

  // Fallback: return highest signal
  return hypotheses.reduce((best, h) => h.signal > best.signal ? h : best);
}

/**
 * biascheck-gym: detect if reward shaping introduces bias
 */
export function biascheck_gym(
  shaped_reward: number,
  components: Record<string, number>,
  hypotheses: RewardHypothesis[]
): BiasCheckResult {
  const flaggedHypotheses: string[] = [];
  const groupDeltas: Record<string, number> = {};

  // Check component variance for bias indicators
  const componentValues = Object.values(components);
  const mean = componentValues.reduce((a, b) => a + b, 0) / componentValues.length;
  const variance = componentValues.reduce((sum, v) => sum + (v - mean) ** 2, 0) / componentValues.length;

  // High variance suggests potential bias
  if (variance > 2.0) {
    flaggedHypotheses.push('high-component-variance');
  }

  // Check for extreme rewards (potential reward hacking)
  if (Math.abs(shaped_reward) > 4.0) {
    flaggedHypotheses.push('extreme-reward');
  }

  // Check CFR bias indicator
  if (components.cfr && Math.abs(components.cfr) > 2.5) {
    flaggedHypotheses.push('cfr-bias');
  }

  // Check neural fusion contribution imbalance
  if (Math.abs(components.neuralFusion) > 2.0) {
    flaggedHypotheses.push('neural-bias');
  }

  // Check darwin swarm unanimity (could indicate groupthink)
  const sourceCounts: Record<string, number> = {};
  for (const h of hypotheses) {
    sourceCounts[h.source] = (sourceCounts[h.source] || 0) + 1;
  }
  const maxSourceCount = Math.max(...Object.values(sourceCounts));
  if (maxSourceCount === hypotheses.length && hypotheses.length > 2) {
    flaggedHypotheses.push('darwin-groupthink');
  }

  // Compute bias score
  const biasScore = Math.min(1.0, (
    flaggedHypotheses.length * 0.15 +
    variance * 0.1 +
    (Math.abs(shaped_reward) > 3 ? 0.2 : 0)
  ));

  return {
    isBiased: biasScore > 0.3,
    biasScore,
    groupDeltas,
    flaggedHypotheses
  };
}

// ============ UTILITY FUNCTIONS ============

function zero_vector(dim: number): number[] {
  return Array(dim).fill(0);
}

function dot_product(a: number[], b: number[]): number {
  return a.reduce((sum, val, i) => sum + val * (b[i] || 0), 0);
}

function cosine_similarity(a: number[], b: number[]): number {
  const dot = dot_product(a, b);
  const normA = Math.sqrt(dot_product(a, a));
  const normB = Math.sqrt(dot_product(b, b));
  return normA && normB ? dot / (normA * normB) : 0;
}

function compute_shaped_reward(components: Record<string, number>): number {
  // Weighted combination of all reward components
  const weights = {
    advantage: 0.40,
    cfr: 0.25,
    neuralFusion: 0.20,
    darwinSelection: 0.15
  };

  return (
    weights.advantage * (components.advantage || 0) +
    weights.cfr * (components.cfr || 0) +
    weights.neuralFusion * (components.neuralFusion || 0) +
    weights.darwinSelection * (components.darwinSelection || 0)
  );
}

// ============ REWARD SHAPER CLASS (implements rl_harness_env interface) ============

export class RewardShaperImpl {
  private futureselfEndpoint: string;
  private db: any;
  private embedder: any;
  private biasCheckConfig: BiasCheckConfig;

  constructor(
    futureselfEndpoint: string = process.env.FUTURESELF_URL || 'http://localhost:8080/futureself',
    db: any = null,
    embedder: any = null,
    biasCheckConfig: BiasCheckConfig = { enabled: true, threshold: 0.3 }
  ) {
    this.futureselfEndpoint = futureselfEndpoint;
    this.db = db;
    this.embedder = embedder;
    this.biasCheckConfig = biasCheckConfig;
  }

  compute(
    state: RLState,
    action: DiscreteAction,
    _nextState: RLState,
    _done: boolean
  ): number {
    // Derive raw reward from state if not explicitly provided
    const raw_reward = this.derive_raw_reward(state);

    const pgvector_context = {
      db: this.db,
      embedder: this.embedder,
      connectionString: process.env.DATABASE_URL || ''
    };

    const shaped = shape_reward(state, action, raw_reward, pgvector_context);

    // Return the shaped reward
    return shaped.shaped;
  }

  private derive_raw_reward(state: RLState): number {
    // Base reward for taking an action
    let reward = 0.1;

    // Bonus for similar episode completion
    if (state.similarEpisodes.length > 0) {
      reward += state.similarEpisodes.reduce(
        (sum, ep) => sum + (ep.similarity || 0) * 0.05,
        0
      );
    }

    // Bonus for NeuralFusion convergence
    if (state.neuralFusion) {
      reward += 0.1 * Math.min(state.neuralFusion.traces.length / 5, 1);
    }

    // Darwin-swarm progress bonus
    if (state.darwinSwarm.phase === 'execution') {
      reward += 0.15;
    } else if (state.darwinSwarm.phase === 'selection') {
      reward += 0.08;
    }

    // Penalize repeated actions (via history)
    const recentActions = state.history.slice(-5);
    const duplicates = recentActions.filter(
      h => h.content === state.message.content
    ).length;
    reward -= duplicates * 0.02;

    return Math.max(-2, Math.min(3, reward));
  }

  // Convenience method for full shaping analysis
  analyze(state: RLState, action: DiscreteAction): ShapedReward {
    const raw_reward = this.derive_raw_reward(state);

    const pgvector_context = {
      db: this.db,
      embedder: this.embedder,
      connectionString: process.env.DATABASE_URL || ''
    };

    return shape_reward(state, action, raw_reward, pgvector_context);
  }
}

// ============ DEFAULT EXPORT ============

export const DefaultRewardShaper = new RewardShaperImpl();

export default RewardShaperImpl;
