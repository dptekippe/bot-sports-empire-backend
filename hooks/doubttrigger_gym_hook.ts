/**
 * DoubtTriggerGym Hook - Pause for self-reflection
 * Trigger: before_model_response
 */

export default async function handler(event) {
  console.log('⏸️ doubttrigger-gym:', event.type);
  
  const valid = ['before:response', 'action:planning'];
  if (!valid.includes(event.type)) return event;
  
  const respTime = event.response_time || 0.5;
  const conf = event.metacog?.score || 0.7;
  
  if (conf < 0.75 || respTime < 0.3) {
    const output = `[DoubtTriggerGym v1]
[State] Time: ${respTime}, Conf: ${conf}
[Action] pause_reflect
[Doubt] Should I verify this?
[Doubt] What would change my mind?
[Doubt] Am I confident enough?

[Self-Accuracy] ${Math.round(conf*100)}% → Pause and reflect`;

    event.messages?.unshift({ role: 'system', content: output });
  }
  
  return event;
}
