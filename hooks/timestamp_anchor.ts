/**
 * Temporal Anchor Hook
 * Adds timestamp context to every message for temporal grounding
 * 
 * Trigger: message:planning, action:planning
 * 
 * What it does:
 *   1. Attach current timestamp to message context
 *   2. Calculate time since last relevant event
 *   3. Add temporal context (day of week, time of day)
 *   4. Enable time-aware reasoning
 */

export default async function handler(event: any): Promise<any> {
  console.log('⏰ temporal-anchor:', event.type);
  
  const validEvents = ['message:planning', 'action:planning', 'prompt:start'];
  if (!validEvents.includes(event.type)) return event;
  
  const now = new Date();
  const cdtOffset = -5; // CDT is UTC-5 (or UTC-6 in standard time)
  
  // Calculate CDT time
  const cdtTime = new Date(now.getTime() + cdtOffset * 60 * 60 * 1000);
  
  // Temporal anchors
  const anchors = {
    timestamp: now.toISOString(),
    cdt: cdtTime.toISOString(),
    dayOfWeek: cdtTime.toLocaleDateString('en-US', { weekday: 'long' }),
    timeOfDay: cdtTime.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      timeZoneName: 'short'
    }),
    hour: cdtTime.getHours(),
    isWeekend: cdtTime.getDay() === 0 || cdtTime.getDay() === 6,
    isBusinessHours: cdtTime.getHours() >= 9 && cdtTime.getHours() <= 17
  };
  
  // Contextual time labels
  let timeLabel = 'evening';
  if (anchors.hour >= 5 && anchors.hour < 12) timeLabel = 'morning';
  else if (anchors.hour >= 12 && anchors.hour < 17) timeLabel = 'afternoon';
  else if (anchors.hour >= 17 && anchors.hour < 21) timeLabel = 'evening';
  else timeLabel = 'night';
  
  if (anchors.isWeekend) timeLabel = 'weekend ' + timeLabel;
  
  // Format output
  const anchorStr = `[Time] ${anchors.dayOfWeek} ${anchors.timeOfDay} (CDT) - ${timeLabel}`;
  
  // Add to context
  event.temporal_anchor = anchors;
  event.messages?.unshift({
    role: 'system',
    content: anchorStr
  });
  
  console.log('⏰ Anchor:', anchors.dayOfWeek, anchors.timeOfDay);
  
  return event;
}
