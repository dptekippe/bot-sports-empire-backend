/**
 * BiasCheckGym Hook - Challenging assumptions
 * Trigger: think_protocol_end
 */

export default async function handler(event) {
  console.log('⚖️ biascheck-gym:', event.type);
  
  const valid = ['think:end', 'action:planning'];
  if (!valid.includes(event.type)) return event;
  
  const metacog = event.metacog?.score || 0.6;
  
  if (metacog < 0.85) {
    const output = `[BiasCheckGym v1]
[State] Metacog: ${metacog}
[Action] challenge_assumption
[Challenge] What if I'm wrong?
[Challenge] What's contrary evidence?
[Challenge] Source verification needed?

[Regret] ${Math.round((1-metacog)*100)}% → Challenge assumptions`;

    event.messages?.unshift({ role: 'system', content: output });
  }
  
  return event;
}
