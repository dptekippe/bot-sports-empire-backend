#!/usr/bin/env python3
"""
Memory Flush Hook for LCM Compaction
Extracts thinking traces before compaction, scores importance, upserts to pgvector.
"""

import re
import sys
import json
from datetime import datetime

sys.path.insert(0, '/Users/danieltekippe/.openclaw/workspace')
from cognitive_memory import store_memory, recall_memories

# Pattern to match thinking traces (MiniMax 2.7 uses <think>...</think>)
THINK_PATTERN = re.compile(r'\[thinking\s*\]\s*|\[think\]\s*|\ufeffthink\s*', re.IGNORECASE)
CONTENT_TAG_PATTERN = re.compile(r'<think[^>]*>(.*?)</think>', re.DOTALL)
UNDERSCORE_PATTERN = re.compile(r'_\(.*?\)_', re.DOTALL)  # MiniMax thinking: _(thought)_
XML_THINK_PATTERN = re.compile(r'<think>(.*?)</think>', re.DOTALL)

def extract_thinking_traces(content: str) -> list[dict]:
    """Extract thinking traces from message content."""
    traces = []
    
    # Try XML style first
    for match in XML_THINK_PATTERN.finditer(content):
        trace_text = match.group(1).strip()
        if len(trace_text) >= 50:
            traces.append({
                'text': trace_text,
                'style': 'xml_think',
                'start': match.start(),
                'end': match.end()
            })
    
    # Try MiniMax underscore style
    for match in UNDERSCORE_PATTERN.finditer(content):
        trace_text = match.group(1).strip()
        if len(trace_text) >= 50:
            traces.append({
                'text': trace_text,
                'style': 'underscore',
                'start': match.start(),
                'end': match.end()
            })
    
    return traces

def score_trace_importance(trace_text: str) -> tuple[float, str]:
    """
    Score thinking trace importance on 0-10 scale.
    Returns (score, reason).
    
    TIER 1 (Auto-keep, score >= 8):
    - Decision keywords
    - Citations/sources
    - Code/architecture
    - Arithmetic/trade values
    
    TIER 2 (Auto-discard, score <= 2):
    - Pure meta-thinking
    - Length < 150 chars
    - Self-reference only
    
    TIER 3 (Borderline, 3-7): Heuristic scoring
    """
    score = 5.0  # Start neutral
    reasons = []
    
    # Decision keywords (high signal)
    decision_patterns = [
        r'\b(DECISION|CONCLUSION|VERDICT|SELECTED|CHOSEN|RECOMMEND|PROCEED)\b',
        r'\b(wins|loses|accept|reject|buy|sell|trade)\b',
        r'→\s*(A|B|team)',  # Trade outcome arrows
    ]
    for pat in decision_patterns:
        if re.search(pat, trace_text, re.IGNORECASE):
            score += 3
            reasons.append('decision_keyword')
            break
    
    # Citations/sources (high signal)
    if re.search(r'https?://|www\.|\[source\]|\(\d+\)|footnote', trace_text, re.IGNORECASE):
        score += 2
        reasons.append('has_citation')
    
    # Code/architecture (high signal)
    if re.search(r'```|`[^`]+`|def |class |import |function |=>|->', trace_text):
        score += 2
        reasons.append('has_code')
    
    # Arithmetic/trade values (medium signal)
    if re.search(r'\$[\d,]+|[\d,]+ tokens|[\d,]+ points|[\d,]+ MHz|KTC [\d,]+', trace_text):
        score += 1.5
        reasons.append('has_values')
    
    # Trade-specific patterns
    if re.search(r'Team [AB]|trade value|player.*KT|ADP', trace_text, re.IGNORECASE):
        score += 1.5
        reasons.append('trade_context')
    
    # Length bonus
    if len(trace_text) > 500:
        score += 1
        reasons.append('length_500')
    if len(trace_text) > 1000:
        score += 1
        reasons.append('length_1000')
    
    # Penalty: pure meta-thinking (scaffolding)
    meta_patterns = [
        r'^(let me|i should|i need to|i will|perhaps|maybe|let\'s)',
        r'(reconsider|think about|analyze|examine|look at)\s+(this|that|it)',
    ]
    for pat in meta_patterns:
        if re.search(pat, trace_text, re.IGNORECASE):
            score -= 2
            reasons.append('meta_scaffolding')
            break
    
    # Penalty: self-reference only
    noun_count = len(re.findall(r'\b(I|me|my|you|your|the|this|that|it)\b', trace_text))
    word_count = len(trace_text.split())
    if word_count > 0 and noun_count / word_count > 0.5:
        score -= 1.5
        reasons.append('pronoun_heavy')
    
    # Tier 2: Auto-discard for very short
    if len(trace_text) < 100:
        score = 2.0
        reasons = ['too_short']
    
    # Clamp
    score = max(0.0, min(10.0, score))
    
    return score, '+'.join(reasons) if reasons else 'neutral'

def strip_thinking_from_content(content: str) -> str:
    """Remove thinking traces from content, replace with [thinking omitted] marker."""
    result = content
    
    # Replace XML think blocks
    result = XML_THINK_PATTERN.sub('\n[thinking omitted - stored in pgvector]\n', result)
    
    # Replace underscore-style thinking
    result = UNDERSCORE_PATTERN.sub('[thinking omitted]', result)
    
    # Clean up extra whitespace
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    return result.strip()

def flush_thinking_traces(messages: list[dict], session_id: str = 'default') -> dict:
    """
    Main function: Extract, score, store thinking traces from messages.
    
    Args:
        messages: List of message dicts with 'content' and 'role' keys
        session_id: Session identifier for grouping
    
    Returns:
        Summary dict with counts of stored/pruned
    """
    stats = {
        'messages_scanned': len(messages),
        'traces_found': 0,
        'traces_stored': 0,
        'traces_pruned': 0,
        'total_chars': 0,
        'estimated_token_savings': 0,
    }
    
    for msg in messages:
        content = msg.get('content', '')
        if not content or msg.get('role') == 'system':
            continue
        
        traces = extract_thinking_traces(content)
        
        for trace in traces:
            stats['traces_found'] += 1
            score, reason = score_trace_importance(trace['text'])
            stats['total_chars'] += len(trace['text'])
            
            if score >= 5.0:  # Keep threshold
                # Store to pgvector
                metadata = {
                    'source_type': 'thinking_trace',
                    'session_id': session_id,
                    'style': trace['style'],
                    'reason': reason,
                    'original_length': len(trace['text']),
                    'stored_at': datetime.utcnow().isoformat(),
                }
                
                result = store_memory(
                    user_id='00000000-0000-0000-0000-000000000001',
                    content=trace['text'][:4000],  # pgvector limit
                    namespace='thinking',
                    importance=score,
                    ttl_days=30,  # Thinking traces expire sooner than facts
                    metadata=metadata
                )
                
                if result:
                    stats['traces_stored'] += 1
                else:
                    stats['traces_pruned'] += 1
            else:
                stats['trunes_pruned'] += 1
    
    # Estimate token savings: ~4 chars per token
    stats['estimated_token_savings'] = stats['total_chars'] // 4
    
    return stats

def create_openclaw_hook() -> str:
    """
    Generate the OpenClaw hook TypeScript code.
    """
    return '''
// hooks/memory-flush/hook.ts
// Memory flush hook - runs before LCM compaction

const handler: HookHandler = async (event) => {
  if (event.type !== 'session' || event.action !== 'compact:before') {
    return; // Only handle session:compact:before
  }
  
  const messages = event.messages || [];
  const sessionId = event.sessionId || 'default';
  
  // Extract messages to send to Python
  const payload = JSON.stringify({ messages, sessionId });
  
  // Call Python memory flush script
  const { execSync } = require('child_process');
  
  try {
    const result = execSync(
      `python3 /Users/danieltekippe/.openclaw/workspace/memory_flush_hook.py << 'EOF'
${payload}
EOF`,
      { encoding: 'utf8', maxBuffer: 10 * 1024 * 1024 }
    );
    
    const stats = JSON.parse(result);
    console.log(`[memory-flush] Stored: {stats.traces_stored}, Pruned: {stats.traces_pruned}, Saved: ~{stats.estimated_token_savings} tokens`);
    
    // Optionally strip thinking from messages before compaction
    if (stats.traces_stored > 0) {
      event.hookData.strippedThinking = true;
    }
  } catch (err) {
    console.error('[memory-flush] Error:', err.message);
  }
};

export default handler;
'''

if __name__ == '__main__':
    # Test with sample messages
    test_messages = [
        {
            'role': 'assistant',
            'content': '''<think>
Let me think about this trade. Team A offers Bijan Robinson (KTC 15000) for Team B's Garrett Wilson (KTC 5838) + Kenneth Walker (KTC 5792).

The math: 15000 vs 11630. Team A wins easily.

DECISION: Team A wins this trade.

Let me consider the alternatives. If we add a 2nd round pick to Team B's offer...
</think>

Team A wins. Bijan is significantly more valuable.''',
        },
        {
            'role': 'assistant', 
            'content': '''<think>
Let me think about this...
</think>

I need to reconsider my approach here.''',
        },
    ]
    
    print("Testing memory flush hook...")
    stats = flush_thinking_traces(test_messages, 'test_session')
    print(json.dumps(stats, indent=2))
