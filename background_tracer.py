"""
Background Tracer for Metacognition Pro v2

Logs session metrics to traces.jsonl for analytics.
Does NOT auto-commit - explicit memory only.
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional

TRACE_FILE = os.path.expanduser("~/.openclaw/workspace/traces.jsonl")

# Domain risk biases
RISK_BIAS = {
    'deploy': 0.15,
    'code': 0.08,
    'api': 0.22,
    'draft': 1.20,
    'debug': 0.35,
    'plan': 0.25,
    'optimize': 0.18
}


def detect_domain(text: str) -> str:
    """Detect domain from text"""
    text = text.lower()
    
    domains = {
        'deploy': ['deploy', 'render', 'production', 'staging', 'hosting'],
        'code': ['code', 'python', 'function', 'implement', 'refactor'],
        'api': ['api', 'request', 'endpoint', 'curl', 'http'],
        'draft': ['draft', 'fantasy', 'pick', 'adp', 'vorp'],
        'debug': ['debug', 'error', 'fix', 'bug', 'issue'],
        'plan': ['plan', 'strategy', 'roadmap', 'architecture'],
        'optimize': ['optimize', 'performance', 'speed', 'cache']
    }
    
    for domain, keywords in domains.items():
        if any(k in text for k in keywords):
            return domain
    
    return 'general'


def extract_confidence(text: str) -> float:
    """Extract confidence percentage from text"""
    import re
    
    # Look for patterns like "66%", "confidence: 80%"
    patterns = [
        r'\[Conf\]\s*(\d+)%',
        r'confidence[:\s]+(\d+)%',
        r'(\d+)%\s*confident'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1)) / 100
    
    return 0.50  # Default


def extract_risk_bias(text: str) -> float:
    """Extract or lookup risk bias"""
    domain = detect_domain(text)
    return RISK_BIAS.get(domain, 0.10)


def extract_cfr_delta(text: str) -> float:
    """Extract CFR regret delta from text"""
    import re
    
    # Look for patterns like "+7% regret", "delta=22%"
    patterns = [
        r'\+(\d+)%\s*regret',
        r'regret[:\s=]+(\d+)',
        r'delta[=:](\d+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1)) / 100
    
    return 0.0


def llm_summarize(text: str, max_tokens: int = 50) -> str:
    """Simple LLM-free summary (first sentence + key terms)"""
    # Extract key terms
    domain = detect_domain(text)
    
    # First 100 chars as summary
    summary = text[:100].replace('\n', ' ')
    
    return f"[{domain}] {summary}..."


def trace_session(messages: list, metadata: dict = None) -> Dict:
    """
    Trace a session and log metrics.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        metadata: Optional metadata (session_id, etc.)
    
    Returns:
        Trace dict
    """
    # Combine all user messages
    user_text = " ".join([
        m.get('content', '') 
        for m in messages 
        if m.get('role') in ['user', 'system']
    ])
    
    # Extract metrics
    domain = detect_domain(user_text)
    confidence = extract_confidence(user_text)
    risk_bias = extract_risk_bias(user_text)
    metacog_score = confidence * (1 - risk_bias)
    regret_delta = extract_cfr_delta(user_text)
    
    # Create trace
    trace = {
        'timestamp': datetime.now().isoformat(),
        'domain': domain,
        'confidence': confidence,
        'risk_bias': risk_bias,
        'metacog_score': metacog_score,
        'regret_delta': regret_delta,
        'summary': llm_summarize(user_text),
        'message_count': len(messages),
        'session_id': metadata.get('session_id') if metadata else None
    }
    
    # Append to trace file
    try:
        with open(TRACE_FILE, 'a') as f:
            f.write(json.dumps(trace) + '\n')
    except Exception as e:
        print(f"Warning: Could not write trace: {e}")
    
    # High value alert
    if metacog_score > 0.85:
        print(f"HIGH VALUE SESSION: metacog={metacog_score:.2f}, domain={domain}")
    
    return trace


def query_traces(domain: str = None, min_metacog: float = None, limit: int = 10) -> list:
    """Query traces from file"""
    traces = []
    
    if not os.path.exists(TRACE_FILE):
        return traces
    
    with open(TRACE_FILE, 'r') as f:
        for line in f:
            try:
                trace = json.loads(line)
                
                # Filter
                if domain and trace.get('domain') != domain:
                    continue
                if min_metacog and trace.get('metacog_score', 0) < min_metacog:
                    continue
                
                traces.append(trace)
            except:
                continue
    
    return traces[-limit:]


def get_stats() -> Dict:
    """Get trace statistics"""
    traces = query_traces(limit=1000)
    
    if not traces:
        return {'total': 0}
    
    domains = {}
    scores = []
    
    for t in traces:
        d = t.get('domain', 'unknown')
        domains[d] = domains.get(d, 0) + 1
        scores.append(t.get('metacog_score', 0))
    
    return {
        'total': len(traces),
        'domains': domains,
        'avg_metacog': sum(scores) / len(scores) if scores else 0,
        'high_value': sum(1 for s in scores if s > 0.85)
    }


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == 'stats':
            stats = get_stats()
            print(json.dumps(stats, indent=2))
        elif cmd == 'query':
            domain = sys.argv[2] if len(sys.argv) > 2 else None
            min_metacog = float(sys.argv[3]) if len(sys.argv) > 3 else None
            results = query_traces(domain, min_metacog)
            for r in results:
                print(json.dumps(r))
        else:
            print("Usage: python background_tracer.py [stats|query]")
    else:
        # Test
        test_text = "[State] deploy | Risk: 15%\n[Conf] 66%\n[CFR] +7% regret"
        trace = trace_session([{'role': 'user', 'content': test_text}])
        print("Test trace:", json.dumps(trace, indent=2))
