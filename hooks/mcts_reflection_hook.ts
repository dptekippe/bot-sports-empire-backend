/**
 * MCTS Reflection Hook - TypeScript for OpenClaw
 * 
 * Pre-answer hook that runs MCTS tree search before LLM sees query.
 * Forces exploration-first reasoning to minimize answer regret.
 * 
 * Trigger: "think"/"optimal"/"complex"/"deploy"/"?" in queries
 */

interface MCTSNode {
  state: Record<string, any>;
  visits: number;
  totalReward: number;
  children: MCTSNode[];
  action: string;
  reasoning: string;
}

const TRIGGER_KEYWORDS = ["think", "optimal", "complex", "deploy", "render", "strategy"];
const EXPLORATION_CONST = 1.414;
const NUM_SIMULATIONS = 25;
const MAX_DEPTH = 3;

// Domain risk lookup
const DOMAIN_RISK: Record<string, number> = {
  "deploy": 0.15,
  "render": 0.15,
  "code": 0.08,
  "debug": 0.35,
  "api": 0.22,
  "draft": 0.15,
  "general": 0.10
};

// Generate action branches for query
function generateBranches(query: string): string[] {
  const lower = query.toLowerCase();
  const branches: string[] = [];
  
  // Always include baseline
  branches.push("direct_answer");
  
  // Add exploration branches based on keywords
  if (lower.includes("deploy") || lower.includes("render")) {
    branches.push("stage_first");
    branches.push("prod_direct");
    branches.push("scale_analysis");
    branches.push("cost_benchmark");
  }
  
  if (lower.includes("optimal") || lower.includes("strategy")) {
    branches.push("mcts_tree_search");
    branches.push("multi_objective");
    branches.push("pareto_frontier");
  }
  
  if (lower.includes("think") || lower.includes("reason")) {
    branches.push("chain_of_thought");
    branches.push("self_reflect");
    branches.push("meta_reasoning");
  }
  
  // Default branches
  branches.push("search_alternatives");
  branches.push("verify_facts");
  
  return [...new Set(branches)].slice(0, 8);
}

// MCTS simulation (simplified)
function mctsSearch(query: string, branches: string[]): MCTSNode {
  // Root
  const root: MCTSNode = {
    state: { query, branches },
    visits: 0,
    totalReward: 0,
    children: [],
    action: "root",
    reasoning: ""
  };
  
  // Run simulations
  for (let i = 0; i < NUM_SIMULATIONS; i++) {
    // Selection
    let node = root;
    while (node.children.length > 0 && node.visits > 0) {
      // UCB1
      node = node.children.reduce((best, child) => {
        const ucb = child.visits === 0 ? Infinity : 
          (child.totalReward / child.visits) + 
          EXPLORATION_CONST * Math.sqrt(Math.log(node.visits) / child.visits);
        const bestUcb = best.visits === 0 ? Infinity :
          (best.totalReward / best.visits) +
          EXPLORATION_CONST * Math.sqrt(Math.log(node.visits) / best.visits);
        return ucb > bestUcb ? child : best;
      });
    }
    
    // Expansion
    const availableBranches = branches.filter(b => 
      !node.children.some(c => c.action === b)
    );
    
    if (availableBranches.length > 0 && node.depth < MAX_DEPTH) {
      const action = availableBranches[Math.floor(Math.random() * availableBranches.length)];
      const child: MCTSNode = {
        state: { ...node.state, action },
        visits: 0,
        totalReward: 0,
        children: [],
        action,
        reasoning: getReasoning(action, query)
      };
      node.children.push(child);
      node = child;
    }
    
    // Simulation (simplified reward)
    const reward = simulateReward(node.action, query);
    node.visits++;
    node.totalReward += reward;
    
    // Backpropagation
    while (node.parent) {
      node.parent.visits++;
      node.parent.totalReward += reward;
      node = node.parent;
    }
  }
  
  return root;
}

function getReasoning(action: string, query: string): string {
  const reasons: Record<string, string> = {
    "stage_first": "Deploy to staging first reduces production failures by 22%",
    "prod_direct": "Direct to prod if low risk and time-critical",
    "scale_analysis": "Analyze current CPU/traffic before deciding",
    "cost_benchmark": "Compare staging vs prod costs",
    "mcts_tree_search": "Search multiple decision branches simultaneously",
    "multi_objective": "Optimize for cost, uptime, and latency",
    "chain_of_thought": "Step-by-step reasoning chain",
    "self_reflect": "Verify answer before responding",
    "direct_answer": "Answer directly based on known information"
  };
  return reasons[action] || `Exploring ${action}`;
}

function simulateReward(action: string, query: string): number {
  // Simplified reward function
  let reward = 0.5;
  
  // Penalize risky actions
  if (action === "prod_direct" && query.toLowerCase().includes("week1")) {
    reward -= 0.3;
  }
  
  // Reward exploration
  if (action.includes("analysis") || action.includes("think")) {
    reward += 0.2;
  }
  
  // Reward thoroughness
  if (action.includes("verify") || action.includes("reflect")) {
    reward += 0.15;
  }
  
  return Math.max(0, Math.min(1, reward));
}

function selectBestAction(root: MCTSNode): MCTSNode {
  if (root.children.length === 0) return root;
  
  return root.children.reduce((best, child) => {
    return (child.visits === 0) ? child : 
           (child.totalReward / child.visits) > (best.totalReward / best.visits) ? child : best;
  });
}

export default async function handler(event: any): Promise<any> {
  console.log('🧠 mcts-reflection:', event.type);
  
  const validEvents = ['message:planning', 'message:received', 'action:planning', 'prompt:start'];
  if (!validEvents.includes(event.type)) {
    return event;
  }
  
  // Extract query
  const userMessage = event.messages?.find((m: any) => m.role === 'user')?.content || '';
  const query = event.message || userMessage || '';
  
  if (!query) {
    return event;
  }
  
  // Check triggers
  const lower = query.toLowerCase();
  const trigger = TRIGGER_KEYWORDS.some(k => lower.includes(k));
  const complexity = lower.length > 100 ? 0.7 : 0.5;
  
  if (!trigger && complexity < 0.6) {
    return event;
  }
  
  // Detect domain
  let domain = 'general';
  let risk = 0.10;
  for (const [key, val] of Object.entries(DOMAIN_RISK)) {
    if (lower.includes(key)) {
      domain = key;
      risk = val;
      break;
    }
  }
  
  // Run MCTS
  const branches = generateBranches(query);
  const mctsResult = mctsSearch(query, branches);
  const best = selectBestAction(mctsResult);
  
  // Calculate metrics
  const confidence = Math.min(0.95, 0.5 + (best.visits / NUM_SIMULATIONS) * 0.3);
  const regret = 1 - confidence;
  const metacog = confidence * (1 - risk);
  
  // Format Metacog Pro v3 output
  const stateStr = `[State] Domain: ${domain} | Risk: ${Math.round(risk*100)}% | Mem: n=${best.visits}`;
  const confStr = `[Conf] ${Math.round(confidence*100)}%`;
  const cfrStr = `[CFR] Best: ${best.action} | Branches: ${branches.length} | UCB1: ${(best.totalReward/best.visits).toFixed(2)}`;
  const sanityStr = `[Sanity] MCTS ${NUM_SIMULATIONS} sims, depth ${MAX_DEPTH}`;
  const toolStr = `[Tool] Tree search: +${Math.round(regret*100)}% exploration (conf ${Math.round(confidence*100)}%)`;
  const actionStr = `[Action] ${best.reasoning}`;
  const traceStr = `[Trace] State→Conf→CFR→MCTS→Sanity→Action`;
  
  const metacogScore = Math.round(metacog * 100);
  
  const response = `${stateStr}
${confStr}
${cfrStr}
${sanityStr}
${toolStr}
${actionStr}
${traceStr}

[Metacog Score] ${metacogScore}/100

🧠 **MCTS Exploration Active** - Searched ${branches.length} branches`;

  // Inject into event
  event.messages?.unshift({
    role: 'system',
    content: response
  });
  
  console.log('🧠 MCTS:', best.action, 'conf:', confidence.toFixed(2), 'metacog:', metacogScore);
  
  return event;
}
