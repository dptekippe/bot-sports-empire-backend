/**
 * ProactiveGym Hook - Anticipating user needs
 * Trigger: message:planning
 */

export default async function handler(event) {
  console.log('🎯 proactive-gym:', event.type);
  
  const valid = ['message:planning', 'prompt:start'];
  if (!valid.includes(event.type)) return event;
  
  const query = event.message || '';
  const complexity = query.length > 100 ? 0.7 : 0.4;
  
  if (complexity > 0.5) {
    const output = `[ProactiveGym v1]
[State] Complexity: ${complexity}
[Action] preempt_tool
[Preempt] Suggest relevant tools proactively
[Preempt] Load context before asked

[Metacog] ${Math.round((1-complexity) * 100)}/100 → Anticipate needs`;

    event.messages?.unshift({ role: 'system', content: output });
  }
  
  return event;
}
