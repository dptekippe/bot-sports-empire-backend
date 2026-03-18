// RL Hooks Test Suite - Jest/Vitest

import { describe, it, expect, beforeEach } from 'vitest';

interface Memory { content: string; embedding?: number[]; memory_type: string; tags: string[]; importance: number; project: string; reward?: number; episode?: number; step?: number; }
interface RLMemoryContext { episode: number; step: number; state: string; action: string; reward: number; done: boolean; }
interface MemorySearchResult extends Memory { similarity: number; }
interface MemoryConfig { connectionString: string; hybridWeights?: { similarity: number; importance: number; recency: number; }; }
type ActionType = 'tool_call' | 'message_response';
interface RLState { sessionId: string; channel: string; message: { id: string; content: string; author: { id: string; name: string; role: string }; timestamp: string }; history: Array<{ role: string; content: string; timestamp: string }>; similarEpisodes: MemorySearchResult[]; darwinSwarm: { candidates: Array<{ id: string; score: number; reasoning: string }>; selected: string | null; phase: 'generation' | 'selection' | 'execution'; iteration: number; }; neuralFusion: { stage: number; traces: string[]; fusedEmbedding: number[] } | null; episode: number; step: number; featureVector: number[]; }
interface DiscreteAction { type: ActionType; payload: string; }
interface RewardShaper { compute(state: RLState, action: DiscreteAction, nextState: RLState, done: boolean): number; }
const CFR_TEMPORAL_WEIGHTS: number[] = [0.12, 0.25, 0.20, 0.15, 0.12, 0.08, 0.08];
interface RewardHypothesis { id: string; signal: number; source: 'advantage' | 'cfr' | 'neural_fusion' | 'darwin'; confidence: number; reasoning: string; }
interface BiasCheckResult { isBiased: boolean; biasScore: number; flaggedHypotheses: string[]; }
interface RLAction_Hook { action: string | number; confidence: number; }
interface EpisodeStats { episode: number; total_reward: number; steps: number; duration_ms: number; actions: RLAction_Hook[]; rewards: number[]; }

// pgvector mocks
function hybrid_search_scoring(memory: Memory, queryEmbedding: number[], config: MemoryConfig) {
  const w = config.hybridWeights || { similarity: 0.5, importance: 0.3, recency: 0.2 };
  let sim = 0;
  if (memory.embedding && queryEmbedding.length === memory.embedding.length) {
    const dot = memory.embedding.reduce((s, v, i) => s + v * queryEmbedding[i], 0);
    const nA = Math.sqrt(memory.embedding.reduce((s, v) => s + v * v, 0));
    const nB = Math.sqrt(queryEmbedding.reduce((s, v) => s + v * v, 0));
    sim = nA && nB ? dot / (nA * nB) : 0;
  }
  return { hybrid_score: w.similarity * sim + w.importance * ((memory.importance || 5) / 10) + w.recency * 0.8, memory };
}
async function rl_recall(episode: number, step: number): Promise<RLMemoryContext | null> {
  if (episode > 0 && step >= 0) return { episode, step, state: '{}', action: '{}', reward: episode * 0.1 + step * 0.01, done: false };
  return null;
}
async function rl_experience_storage(ctx: RLMemoryContext) {
  if (ctx.episode < 0) throw new Error('Invalid episode');
  return { success: true };
}

// RL harness env mock
class MockRLHarnessEnv {
  private episode = 0; private stepCount = 0; private darwinPhase: 'generation' | 'selection' | 'execution' = 'generation';
  constructor(private maxSteps = 50, private rewardShaper: RewardShaper = { compute: () => 0 }) {}
  reset(ctx: { sessionId: string; channel: string; message: RLState['message'] }) {
    this.episode++; this.stepCount = 0; this.darwinPhase = 'generation';
    return { sessionId: ctx.sessionId, channel: ctx.channel, message: ctx.message, history: [], similarEpisodes: [], darwinSwarm: { candidates: [{ id: 'plan-1', score: 0.5, reasoning: 'Primary' }], selected: null, phase: 'generation', iteration: 0 }, neuralFusion: { stage: 2, traces: [], fusedEmbedding: Array(768).fill(0.1) }, episode: this.episode, step: 0, featureVector: [] };
  }
  step(action: DiscreteAction) {
    this.stepCount++;
    if (this.darwinPhase === 'generation') this.darwinPhase = 'selection';
    else if (this.darwinPhase === 'selection') this.darwinPhase = 'execution';
    const ns: RLState = { sessionId: 's1', channel: 'webchat', message: { id: 'm2', content: 'resp', author: { id: 'agent', name: 'Roger', role: 'assistant' }, timestamp: new Date().toISOString() }, history: [], similarEpisodes: [], darwinSwarm: { phase: this.darwinPhase, selected: this.darwinPhase === 'execution' ? 'plan-1' : null, candidates: [], iteration: this.stepCount }, neuralFusion: null, episode: this.episode, step: this.stepCount, featureVector: [] };
    return { state: ns, reward: this.rewardShaper.compute(ns, action, ns, false), done: false, truncated: this.stepCount >= this.maxSteps, info: {} };
  }
  getEpisode() { return this.episode; }
}

// RL reward shaper mocks
function biascheck_gym(sr: number, comp: Record<string, number>, hs: RewardHypothesis[]): BiasCheckResult {
  const flags: string[] = [];
  const vals = Object.values(comp); const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
  const variance = vals.reduce((s, v) => s + (v - mean) ** 2, 0) / vals.length;
  if (variance > 2.0) flags.push('high-component-variance');
  if (Math.abs(sr) > 4.0) flags.push('extreme-reward');
  if (Math.abs(comp.cfr || 0) > 2.5) flags.push('cfr-bias');
  if (Math.abs(comp.neuralFusion || 0) > 2.0) flags.push('neural-bias');
  const sc: Record<string, number> = {}; for (const h of hs) sc[h.source] = (sc[h.source] || 0) + 1;
  if (Math.max(...Object.values(sc), 0) === hs.length && hs.length > 2) flags.push('darwin-groupthink');
  return { isBiased: flags.length > 0, biasScore: Math.min(1, flags.length * 0.15), flaggedHypotheses: flags };
}
function select_reward_hypothesis(hs: RewardHypothesis[]): RewardHypothesis {
  if (hs.length === 0) return { id: 'h-default', signal: 0, source: 'advantage', confidence: 0, reasoning: '' };
  if (hs.length === 1) return hs[0];
  return hs.reduce((b, h) => h.signal > b.signal ? h : b);
}

// RL harness hook mock
class MockRLHarnessHook {
  constructor(private factcheck = true) {}
  async run_episode(_ag: any, ec: any) {
    const t0 = Date.now(); const env = new MockRLHarnessEnv(ec.max_steps || 10);
    env.reset({ sessionId: 'test', channel: 'test', message: { id: 'm1', content: 'test', author: { id: 'a', name: 'A', role: 'user' }, timestamp: new Date().toISOString() } });
    const rews: number[] = [];
    for (let i = 0; i < (ec.max_steps || 10); i++) { const r = env.step({ type: 'message_response', payload: 'test' }); rews.push(r.reward); if (r.done) break; }
    return { episode: 1, total_reward: rews.reduce((a, b) => a + b, 0), steps: rews.length, duration_ms: Date.now() - t0, actions: [], rewards: rews };
  }
  async mcts_simulate(_s: any, d: number) {
    return { best_action: { action: 'a1', confidence: 0.85 }, explored_branches: Array.from({ length: Math.min(d, 5) }, (_, i) => `branch-${i}`), expected_value: 0.5, confidence: 0.8 };
  }
  async factcheck_validate(_s: any, a: RLAction_Hook) {
    if (!this.factcheck) return { valid: true, confidence: 1, issues: [], suggestions: [] };
    const issues: string[] = []; if (a.confidence < 0.5) issues.push('Low confidence');
    return { valid: issues.length === 0, confidence: issues.length === 0 ? 0.9 : 0.5, issues, suggestions: [] };
  }
  async self_improve_report(st: EpisodeStats) {
    return { adjusted_params: { lr: 0.001 }, improvements: st.total_reward < 0 ? ['Increase rewards'] : [], confidence: 0.7 };
  }
}

// =============================================================================
// SUITE 1: pgvector_memory_hook
// =============================================================================
describe('Suite 1: pgvector_memory_hook', () => {
  const cfg: MemoryConfig = { connectionString: 'postgres://test', hybridWeights: { similarity: 0.5, importance: 0.3, recency: 0.2 } };

  describe('hybrid_search_scoring', () => {
    it('computes hybrid score', () => {
      const m: Memory = { content: 'test', embedding: Array(10).fill(0.5), memory_type: 'fact', tags: [], importance: 8, project: 'test' };
      const r = hybrid_search_scoring(m, Array(10).fill(0.5), cfg);
      expect(r.hybrid_score).toBeGreaterThan(0);
    });
    it('handles missing embedding', () => {
      const m: Memory = { content: 'test', embedding: undefined, memory_type: 'fact', tags: [], importance: 5, project: 'test' };
      expect(() => hybrid_search_scoring(m, Array(10).fill(0.5), cfg)).not.toThrow();
    });
  });

  describe('rl_experience_storage', () => {
    it('stores valid experience', async () => {
      const r = await rl_experience_storage({ episode: 1, step: 5, state: '{}', action: '{}', reward: 0.8, done: false });
      expect(r.success).toBe(true);
    });
    it('throws on invalid episode', async () => {
      await expect(rl_experience_storage({ episode: -1, step: 0, state: '', action: '', reward: 0, done: false })).rejects.toThrow('Invalid episode');
    });
  });

  describe('rl_recall_query', () => {
    it('recalls valid episode', async () => {
      const r = await rl_recall(1, 5);
      expect(r).not.toBeNull();
      expect(r!.episode).toBe(1);
    });
    it('returns null for non-existent episode', async () => {
      expect(await rl_recall(-999, -999)).toBeNull();
    });
  });
});

// =============================================================================
// SUITE 2: rl_harness_env
// =============================================================================
describe('Suite 2: rl_harness_env', () => {
  const mkCtx = () => ({ sessionId: 's1', channel: 'c1', message: { id: 'm1', content: 'hello', author: { id: 'u1', name: 'U', role: 'user' }, timestamp: '2026-03-18T10:00:00Z' } });

  describe('test_env_reset', () => {
    it('initializes state', () => {
      const env = new MockRLHarnessEnv();
      const state = env.reset(mkCtx());
      expect(state.sessionId).toBe('s1');
      expect(state.episode).toBe(1);
      expect(state.step).toBe(0);
    });
    it('starts darwin-swarm in generation phase', () => {
      const env = new MockRLHarnessEnv();
      const state = env.reset(mkCtx());
      expect(state.darwinSwarm.phase).toBe('generation');
    });
  });

  describe('test_env_step', () => {
    it('advances step on message_response', () => {
      const env = new MockRLHarnessEnv();
      env.reset(mkCtx());
      const r = env.step({ type: 'message_response', payload: 'Hi' });
      expect(r.state.step).toBe(1);
    });
    it('sets truncated when maxSteps reached', () => {
      const env = new MockRLHarnessEnv(2);
      env.reset(mkCtx());
      env.step({ type: 'message_response', payload: 'p1' });
      const r = env.step({ type: 'message_response', payload: 'p2' });
      expect(r.truncated).toBe(true);
    });
  });

  describe('test_darwin_swarm_phases', () => {
    it('transitions generation->selection->execution', () => {
      const env = new MockRLHarnessEnv();
      env.reset(mkCtx());
      expect(env.reset(mkCtx()).darwinSwarm.phase).toBe('generation');
      const g = env.step({ type: 'message_response', payload: 'p1' });
      expect(g.state.darwinSwarm.phase).toBe('selection');
      const s = env.step({ type: 'message_response', payload: 'p2' });
      expect(s.state.darwinSwarm.phase).toBe('execution');
    });
    it('selects plan-1 in execution', () => {
      const env = new MockRLHarnessEnv();
      env.reset(mkCtx());
      env.step({ type: 'message_response', payload: 'p1' });
      const e = env.step({ type: 'message_response', payload: 'p2' });
      expect(e.state.darwinSwarm.selected).toBe('plan-1');
    });
  });

  describe('test_neural_fusion', () => {
    it('initializes stage 2 with 768-dim embedding', () => {
      const env = new MockRLHarnessEnv();
      const state = env.reset(mkCtx());
      expect(state.neuralFusion).not.toBeNull();
      expect(state.neuralFusion!.stage).toBe(2);
      expect(state.neuralFusion!.fusedEmbedding.length).toBe(768);
    });
  });
});

// =============================================================================
// SUITE 3: rl_reward_shaper
// =============================================================================
describe('Suite 3: rl_reward_shaper', () => {
  describe('test_cfr_temporal_weights', () => {
    it('sums to 1.0', () => expect(CFR_TEMPORAL_WEIGHTS.reduce((a, b) => a + b, 0)).toBeCloseTo(1.0, 2));
    it('has 7 slices', () => expect(CFR_TEMPORAL_WEIGHTS.length).toBe(7));
    it('all weights positive and less than 1', () => CFR_TEMPORAL_WEIGHTS.forEach(w => { expect(w).toBeGreaterThan(0); expect(w).toBeLessThan(1); }));
  });

  describe('test_biascheck_gym_flags', () => {
    it('flags high-component-variance', () => {
      const bc = biascheck_gym(2, { advantage: 5, cfr: -4, neuralFusion: 3, darwinSelection: -3 }, []);
      expect(bc.flaggedHypotheses).toContain('high-component-variance');
    });
    it('flags extreme-reward', () => {
      const bc = biascheck_gym(5, { advantage: 0, cfr: 0, neuralFusion: 0, darwinSelection: 0 }, []);
      expect(bc.flaggedHypotheses).toContain('extreme-reward');
    });
    it('flags cfr-bias', () => {
      const bc = biascheck_gym(1, { advantage: 0, cfr: 3, neuralFusion: 0, darwinSelection: 0 }, []);
      expect(bc.flaggedHypotheses).toContain('cfr-bias');
    });
    it('flags neural-bias', () => {
      const bc = biascheck_gym(1, { advantage: 0, cfr: 0, neuralFusion: 2.5, darwinSelection: 0 }, []);
      expect(bc.flaggedHypotheses).toContain('neural-bias');
    });
    it('flags darwin-groupthink', () => {
      const hs: RewardHypothesis[] = [
        { id: 'h1', signal: 1, source: 'advantage', confidence: 0.8, reasoning: '' },
        { id: 'h2', signal: 1, source: 'advantage', confidence: 0.7, reasoning: '' },
        { id: 'h3', signal: 1, source: 'advantage', confidence: 0.6, reasoning: '' }
      ];
      const bc = biascheck_gym(1, { advantage: 1, cfr: 1, neuralFusion: 1, darwinSelection: 1 }, hs);
      expect(bc.flaggedHypotheses).toContain('darwin-groupthink');
    });
  });

  describe('test_select_reward_hypothesis', () => {
    it('returns default for empty', () => expect(select_reward_hypothesis([]).id).toBe('h-default'));
    it('returns single as-is', () => expect(select_reward_hypothesis([{ id: 'h1', signal: 0.8, source: 'advantage', confidence: 0.5, reasoning: '' }]).id).toBe('h1'));
    it('selects from multiple', () => expect(['h1', 'h2']).toContain(select_reward_hypothesis([{ id: 'h1', signal: 0.5, source: 'advantage', confidence: 0.3, reasoning: '' }, { id: 'h2', signal: 0.8, source: 'cfr', confidence: 0.9, reasoning: '' }]).id));
  });
});

// =============================================================================
// SUITE 4: rl_harness_hook
// =============================================================================
describe('Suite 4: rl_harness_hook', () => {
  let hook: MockRLHarnessHook;
  beforeEach(() => { hook = new MockRLHarnessHook(true); });

  describe('test_run_episode', () => {
    it('executes episode and returns stats', async () => {
      const stats = await hook.run_episode({}, { max_steps: 5 });
      expect(stats.episode).toBe(1);
      expect(stats.steps).toBeGreaterThan(0);
    });
  });

  describe('test_mcts_simulate', () => {
    it('returns valid action with branches', async () => {
      const r = await hook.mcts_simulate({}, 3);
      expect(r.best_action.confidence).toBeGreaterThan(0);
      expect(r.explored_branches.length).toBeGreaterThan(0);
    });
  });

  describe('test_factcheck_validate', () => {
    it('valid for high confidence', async () => {
      const r = await hook.factcheck_validate({}, { action: 'a', confidence: 0.9 });
      expect(r.valid).toBe(true);
    });
    it('flags low confidence', async () => {
      const r = await hook.factcheck_validate({}, { action: 'a', confidence: 0.3 });
      expect(r.valid).toBe(false);
      expect(r.issues).toContain('Low confidence');
    });
  });

  describe('test_self_improve_report', () => {
    it('returns improvements for negative reward', async () => {
      const r = await hook.self_improve_report({ episode: 1, total_reward: -0.5, steps: 5, duration_ms: 100, actions: [], rewards: [] });
      expect(r.improvements.length).toBeGreaterThan(0);
    });
  });
});

// =============================================================================
// SUITE 5: Integration flows
// =============================================================================
describe('Suite 5: Integration flows', () => {
  describe('test_fantasy_draft_flow', () => {
    it('draft pick -> evaluate -> shape reward -> store', async () => {
      const env = new MockRLHarnessEnv(10);
      const state = env.reset({ sessionId: 'ds', channel: 'draft', message: { id: 'dm1', content: 'Draft Bijan', author: { id: 'c', name: 'Commish', role: 'user' }, timestamp: new Date().toISOString() } });
      const result = env.step({ type: 'message_response', payload: 'Draft Bijan 1.01' });
      expect(result.state.step).toBe(1);
      const bc = biascheck_gym(1.0, { advantage: 0.5, cfr: 0.3, neuralFusion: 0.1, darwinSelection: 0.2 }, []);
      expect(typeof bc.biasScore).toBe('number');
      expect(env.getEpisode()).toBe(1);
    });
  });

  describe('test_trade_evaluation_flow', () => {
    it('evaluate trade -> shape reward -> store', async () => {
      const env = new MockRLHarnessEnv(10);
      const state = env.reset({ sessionId: 'ts', channel: 'trade', message: { id: 'tm1', content: 'Trade: K Walker', author: { id: 'u', name: 'User', role: 'user' }, timestamp: new Date().toISOString() } });
      const result = env.step({ type: 'message_response', payload: 'K Walker for Charbonnet+2.01' });
      expect(result.state.step).toBe(1);
      const h = new MockRLHarnessHook(true);
      const r = await h.self_improve_report({ episode: 1, total_reward: 0.7, steps: 1, duration_ms: 50, actions: [], rewards: [] });
      expect(r.adjusted_params).toBeDefined();
    });
  });

  describe('test_code_review_flow', () => {
    it('review PR -> feedback -> learn', async () => {
      const hook = new MockRLHarnessHook(true);
      const r = await hook.mcts_simulate({}, 3);
      expect(r.best_action).toBeDefined();
      const fc = await hook.factcheck_validate({}, { action: 'approve', confidence: 0.85 });
      expect(fc.valid).toBe(true);
    });
  });
});
