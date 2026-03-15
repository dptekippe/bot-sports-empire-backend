/**
 * QuestionGym Hook - Probing weak points
 * Trigger: after_model_response
 */

export default async function handler(event) {
  console.log('❓ question-gym:', event.type);
  
  const valid = ['after_model_response', 'action:planning'];
  if (!valid.includes(event.type)) return event;
  
  const conf = event.metacog?.score || 0.7;
  
  if (conf < 0.8) {
    const output = `[QuestionGym v1]
[State] Conf: ${conf}
[Action] probe_weakness
[Probe] What assumptions am I making?
[Probe] What evidence supports this?
[Probe] What's an alternative view?

[Metacog] ${Math.round(conf * 100)}/100 → Ask clarifying questions`;

    event.messages?.unshift({ role: 'system', content: output });
  }
  
  return event;
}
