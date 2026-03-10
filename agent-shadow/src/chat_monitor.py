#!/usr/bin/env python3
"""
Agent Shadow - Response Monitor Subagent
Monitors my (assistant) responses in the transcript and queues for critique.
Simpler version - no memory recall.
"""

import json
import time
from pathlib import Path

# Configuration
SESSIONS_DIR = Path.home() / ".openclaw" / "agents" / "main" / "sessions"
QUEUE_DIR = Path(__file__).parent / "queue"
QUEUE_DEEP_DIR = Path(__file__).parent / "queue_deep"
POLL_INTERVAL = 2  # seconds

# Keywords that trigger deep analysis
DEEP_TRIGGERS = [
    "philosophy", "ethics", "consciousness", "identity",
    "architecture", "methodology", "planning", "strategy",
    "fastapi", "sqlalchemy", "postgresql", "render"
]

# Track last processed line
last_position = {}

def get_transcript_files():
    """Find all transcript JSONL files (most recent first)."""
    files = list(SESSIONS_DIR.glob("*.jsonl"))
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return files[:1]

def extract_assistant_content(entry):
    """Extract assistant message content from transcript entry."""
    msg = entry.get("message", {})
    if msg.get("role") != "assistant":
        return None
    
    content = msg.get("content", [])
    if not isinstance(content, list):
        return None
    
    texts = []
    for part in content:
        if part.get("type") == "text":
            texts.append(part.get("text", ""))
    
    return "\n".join(texts) if texts else None

def check_deep_trigger(text):
    """Check if response needs deep analysis."""
    if not text:
        return False
    text_lower = text.lower()
    for keyword in DEEP_TRIGGERS:
        if keyword in text_lower:
            return True
    return len(text) > 2000

def queue_critique(text, priority="fast"):
    """Add my response to critique queue."""
    queue_dir = QUEUE_DEEP_DIR if priority == "deep" else QUEUE_DIR
    
    item = {
        "id": f"response_{int(time.time()*1000)}",
        "timestamp": time.time(),
        "source": "response",
        "response_text": text,
        "priority": priority
    }
    
    filename = queue_dir / f"critique_{int(time.time()*1000)}.json"
    with open(filename, 'w') as f:
        json.dump(item, f, indent=2)
    
    print(f"[Critique] {priority}: {text[:50]}...")

def process_transcripts():
    """Process transcript files."""
    global last_position
    
    for filepath in get_transcript_files():
        try:
            filepath_str = str(filepath)
            
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            start_idx = last_position.get(filepath_str, 0)
            
            for i in range(start_idx, len(lines)):
                line = lines[i]
                if not line.strip():
                    continue
                
                try:
                    entry = json.loads(line)
                except:
                    continue
                
                content = extract_assistant_content(entry)
                if content and len(content) > 20:
                    if check_deep_trigger(content):
                        queue_critique(content, "deep")
                    else:
                        queue_critique(content, "fast")
            
            last_position[filepath_str] = len(lines)
            
        except Exception as e:
            pass

def main():
    """Main loop - watch transcript files."""
    global last_position
    
    print("Agent Shadow - Response Monitor Starting...")
    print(f"Sessions: {SESSIONS_DIR}")
    print(f"Poll: {POLL_INTERVAL}s")
    print("-" * 40)
    
    QUEUE_DIR.mkdir(exist_ok=True)
    QUEUE_DEEP_DIR.mkdir(exist_ok=True)
    
    for filepath in get_transcript_files():
        try:
            with open(filepath, 'r') as f:
                last_position[str(filepath)] = len(f.readlines())
        except:
            pass
    
    print(f"Monitoring {len(last_position)} session")
    
    while True:
        try:
            process_transcripts()
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
