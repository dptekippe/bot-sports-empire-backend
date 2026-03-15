/**
 * EchoChamber Hook - Anti-bias via contra-analysis
 * Trigger: after_model_response
 */

const DOMAIN_WEIGHTS: Record<string, number> = {
  "fantasy_football": 1.5,
  "chess": 1.2,
  "deployment": 1.0,
  "general": 0.8
};

const ACTION_NAMES: Record<number, string> = {
  0: "accept_primary",
  1: "steelman_contra1",
  2: "steelman_contra2",
  3: "hybrid_synthesis",
  4: "escalate_PC",
  5: "memory_commit_debate"
};

function buildState(context: any): number[] {
  const responseMeta = context.response_metadata || {};
  const confScore = parseFloat(responseMeta.confidence) || 0.5;
  
  const contraMemories = context.contra_memories || [];
  const contraHits = Math.min(contraMemories.length, 10);
  
  const debateDepth = parseFloat(context.debate_depth) || 0;
  
  // Memory freshness (days)
  let memFreshness = 30.0;
  if (contraMemories.length > 0 && contraMemories[0].created_at) {
    const created = new Date(contraMemories[0].created_at);
    const now = new Date();
    const age = (now.getTime() - created.getTime()) / (1000 * 60 * 60 * 24);
    memFreshness = Math.min(memFreshness, age);
  }
  
  const domain = context.domain || "general";
  const domainWeight = DOMAIN_WEIGHTS[domain] || 0.8;
  
  // User feedback
  const feedbackHistory = context.user_feedback_history || [];
  const userFeedback = feedbackHistory.length > 0 
    ? feedbackHistory.slice(-20).reduce((a: number, b: number) => a + b, 0) / Math.min(feedbackHistory.length, 20)
    : 0.5;
  
  // Metacog bias
  let metacogBias: number;
  if (contraHits <= 0) {
    metacogBias = Math.min(confScore, 1.0);
  } else {
    const damping = Math.min(contraHits / 5.0, 1.0);
    metacogBias = Math.max(0.0, Math.min(confScore * (1.0 - damping * 0.6), 1.0));
  }
  
  return [confScore, contraHits, debateDepth, memFreshness, domainWeight, userFeedback, metacogBias];
}

function computeMetacogScore(state: number[], nSteelmans: number = 0): number {
  const [conf, contra, depth, , domainW, , bias] = state;
  
  let base = 50.0;
  base += Math.min(contra, 5) * 6.0;
  base += Math.min(depth, 4) * 5.0;
  base -= bias * 20.0;
  base += (1.0 - conf) * 10.0;
  base *= Math.min(domainW / 1.0, 1.5);
  base += nSteelmans * 5.0;
  
  return Math.max(0, Math.min(100, Math.floor(base)));
}

function steelman(contraContent: string, primaryAnswer: string): string {
  if (!contraContent) return primaryAnswer;
  return `Still ${primaryAnswer.slice(0, 40).trim()} (acknowledging: ${contraContent.slice(0, 80).trim()})`;
}

function hybridSynthesis(primary: string, steelmans: string[]): string {
  if (steelmans.length === 0) return primary;
  
  const parts = [`Primary: ${primary.slice(0, 120)}`];
  steelmans.forEach((sm, i) => {
    parts.push(`Contra-steelman ${i+1}: ${sm.slice(0, 120)}`);
  });
  parts.push("Synthesis: Weighted merge favouring strongest evidence.");
  
  return parts.join(" | ");
}

export default async function handler(event: any): Promise<any> {
  console.log('🔄 echochamber:', event.type);
  
  const validEvents = ['after_model_response', 'response:complete'];
  if (!validEvents.includes(event.type)) return event;
  
  try {
    // Build state from context
    const state = buildState(event);
    const contraMemories = event.contra_memories || [];
    
    // Simple rule-based action (PPO model would be loaded in full version)
    let action = 0;
    const conf = state[0];
    const contraHits = state[1];
    
    // Action logic: higher confidence + more contra = more scrutiny
    if (conf > 0.8 && contraHits > 0) {
      action = 3; // hybrid_synthesis
    } else if (conf > 0.7 && contraHits > 1) {
      action = 1; // steelman_contra1
    } else if (conf < 0.6) {
      action = 2; // steelman_contra2
    }
    
    let steelmans: string[] = [];
    const primary = event.response_text || event.message || '';
    
    if (action === 1 || action === 2) {
      const idx = action - 1;
      if (idx < contraMemories.length) {
        const sm = steelman(contraMemories[idx].content || '', primary);
        steelmans.push(sm);
      }
    }
    
    if (action === 3) {
      if (contraMemories.length > 0) {
        const sm = steelman(contraMemories[0].content || '', primary);
        steelmans.push(sm);
      }
      const synthesis = hybridSynthesis(primary, steelmans);
      event.synthesis = synthesis;
    }
    
    if (action === 4) {
      event.escalate_pc = true;
    }
    
    // Compute metacog score
    const mcScore = computeMetacogScore(state, steelmans.length);
    
    // Build annotation
    const contraSummary = contraMemories[0]?.content?.slice(0, 60) || '';
    const steelmanText = steelmans[steelmans.length - 1] || primary.slice(0, 40);
    
    const annotation = `[EchoChamber] Contra: ${contraSummary}... Steelman: ${steelmanText} (${mcScore}/100 metacog)`;
    
    // Inject annotation
    if (action > 0) {
      event.response_text = `${annotation}\n\n${primary}`;
      event.metacog_score = mcScore;
      event.metacog_annotation = annotation;
    }
    
    event.echochamber_action = ACTION_NAMES[action] || "unknown";
    
    console.log('🔄 EchoChamber:', ACTION_NAMES[action], 'metacog:', mcScore);
    
  } catch (error) {
    console.error('EchoChamber error:', error);
  }
  
  return event;
}
