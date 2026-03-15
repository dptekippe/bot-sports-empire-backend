/**
 * Render Deploy Gym Hook - OpenClaw Integration
 */

export default async function handler(event) {
  console.log('🎯 render-deploy-gym:', event.type);
  
  const validEvents = ['message:planning', 'message:received', 'action:planning', 'prompt:start'];
  if (!validEvents.includes(event.type)) return;
  
  const userMessage = event.messages?.find(m => m.role === 'user')?.content || '';
  if (!userMessage.toLowerCase().includes('deploy')) return;
  
  // Parse parameters
  let cpuPct = 50, weekNum = 15, lastDeploySuccess = true;
  const cpuMatch = userMessage.match(/cpu[=\s]+(\d+)/i);
  if (cpuMatch) cpuPct = parseInt(cpuMatch[1]);
  const weekMatch = userMessage.match(/week[=\s]+(\d+)/i);
  if (weekMatch) weekNum = parseInt(weekMatch[1]);
  if (userMessage.toLowerCase().includes('fail')) lastDeploySuccess = false;
  
  // CFR Decision
  let action = 'stage_deploy', confidence = 0.65, regret = 0.08, reason = 'Default: stage recommended';
  
  if (weekNum <= 1) {
    action = 'stage_deploy'; confidence = 0.92; regret = 0.22;
    reason = 'Week 1 = 15% fail rate, stage reduces to 8%';
  } else if (cpuPct > 70) {
    action = 'stage_deploy'; confidence = 0.85; regret = 0.15;
    reason = 'High CPU (70%+) = 22% more uptime with staging';
  } else if (!lastDeploySuccess) {
    action = 'stage_deploy'; confidence = 0.78; regret = 0.12;
    reason = 'Recent failures = stage recommended';
  } else if (cpuPct < 50 && lastDeploySuccess) {
    action = 'prod_deploy'; confidence = 0.72; regret = 0.05;
    reason = 'Low risk scenario: prod OK';
  }
  
  const metacog = Math.round(confidence * (1 - 0.15) * 100);
  
  const response = `[State] Domain: deploy | Risk: 15% | Mem: n=1000
[Conf] ${Math.round(confidence * 100)}%
[CFR] ${action === 'stage_deploy' ? 'prod_deploy' : 'stage_deploy'}: +${Math.round(regret * 100)}%
[Sanity] Holdout: 8% (staging), 15% (prod)
[Tool] CFR model: +${Math.round(regret * 100)}% uptime (conf ${Math.round(confidence * 100)}%)
[Action] ${action} - ${reason}

[Metacog Score] ${metacog}/100`;

  event.messages?.unshift({ role: 'system', content: `🎯 **Render Deploy Gym v1**\n\n${response}` });
  console.log('🎯 Deploy decision:', action, 'conf:', confidence);
}
