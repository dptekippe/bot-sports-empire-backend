#!/usr/bin/env python3
"""
Agent Shadow - Log Monitor Subagent
Watches OpenClaw JSONL logs and extracts Roger responses for critique.
"""

import json
import os
import time
from pathlib import Path
from datetime import datetime

# Configuration
LOG_DIR = Path.home() / ".openclaw" / "logs"
LOG_FILE = LOG_DIR / "gateway.log"  # Primary log file
QUEUE_DIR = Path(__file__).parent / "queue"
POLL_INTERVAL = 2  # seconds

# Track last processed position
LAST_POSITION_FILE = Path(__file__).parent / ".last_position"

# Ensure queue directory exists
QUEUE_DIR.mkdir(exist_ok=True)

# Deep queue for complex topics
DEEP_QUEUE_DIR = QUEUE_DIR.parent / "queue_deep"
DEEP_QUEUE_DIR.mkdir(exist_ok=True)

# Keywords that trigger deep analysis
DEEP_ANALYSIS_TRIGGERS = [
    # Philosophy & Identity
    "philosophy", "ethics", "meaning", "consciousness", "identity",
    "religion", "belief", "truth", "reality", "existence",
    "free will", "moral", "purpose", "value", "rights",
    # AI & Agents
    "AI", "agent", "bot", "conscious", "awareness",
    "future", "society", "impact", "implications",
    # Technical/Development
    "fastapi", "sqlalchemy", "postgresql", "postgres",
    "render", "render.com", "sleeper", "api", "endpoint",
    "database", "backend", "frontend", "deployment",
    "github", "git", "docker", "cloud", "infrastructure",
    # System Design (added)
    "architecture", "methodology", "planning", "strategy",
    "design", "system", "pattern", "refactor", "optimize",
    "performance", "scalability", "security", "testing"
]

def find_latest_log():
    """Find the most recent OpenClaw log file."""
    # Prefer gateway.log for main responses
    if LOG_FILE.exists():
        return LOG_FILE
    
    if not LOG_DIR.exists():
        return None
    
    log_files = list(LOG_DIR.glob("*.jsonl"))
    if not log_files:
        return None
    
    # Return most recently modified
    return max(log_files, key=lambda f: f.stat().st_mtime)

def load_last_position():
    """Load last processed position from file."""
    if LAST_POSITION_FILE.exists():
        try:
            with open(LAST_POSITION_FILE, 'r') as f:
                return int(f.read().strip())
        except:
            pass
    return 0

def save_last_position(position):
    """Save last processed position to file."""
    with open(LAST_POSITION_FILE, 'w') as f:
        f.write(str(position))

def parse_gateway_log(filepath, last_position=0):
    """Parse new entries from gateway.log since last position."""
    entries = []
    
    try:
        with open(filepath, 'r') as f:
            f.seek(last_position)
            
            current_entry = None
            current_content = []
            
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # Check for timestamp pattern: "2026-03-04T15:38:57.652-06:00"
                if line.startswith('2026-') or line.startswith('['):
                    # Save previous entry if exists
                    if current_entry and current_content:
                        current_entry['content'] = '\n'.join(current_content)
                        entries.append(current_entry)
                    
                    # Start new entry
                    if '[' in line:
                        # Log format: [timestamp] message
                        parts = line.split(']', 1)
                        timestamp = parts[0].strip('[') if parts else ""
                        message = parts[1].strip() if len(parts) > 1 else ""
                        
                        current_entry = {
                            'timestamp': timestamp,
                            'content': message,
                            'raw': line
                        }
                        current_content = [message] if message else []
                    else:
                        # Plain text timestamp format
                        parts = line.split(None, 1)
                        timestamp = parts[0] if parts else ""
                        message = parts[1] if len(parts) > 1 else ""
                        
                        current_entry = {
                            'timestamp': timestamp,
                            'content': message,
                            'raw': line
                        }
                        current_content = [message] if message else []
                elif current_entry and line:
                    # Continuation of previous entry
                    current_content.append(line)
            
            # Don't forget last entry
            if current_entry and current_content:
                current_entry['content'] = '\n'.join(current_content)
                entries.append(current_entry)
            
            # Update position
            last_position = f.tell()
            
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    
    return entries, last_position

def is_roger_response(entry):
    """Check if entry is a Roger response."""
    content = entry.get("content", "")
    raw = entry.get("raw", "")
    
    # Skip log lines that are just timestamps/metadata
    if not content:
        return False
    
    # Skip obvious non-response lines
    skip_patterns = [
        "Now I'll",
        "Let me",
        "The post was created",
        "Verification",
        "[gateway]",
        "[heartbeat]",
        "[health-monitor]",
    ]
    
    for pattern in skip_patterns:
        if content.startswith(pattern):
            return False
    
    # Look for substantive responses (longer content)
    if len(content) > 100:
        return True
    
    return False

def extract_response_text(entry):
    """Extract the response text from entry."""
    return entry.get("content", "")

def should_use_deep_analysis(text):
    """Determine if text needs deep analysis."""
    text_lower = text.lower()
    
    # Check for trigger keywords
    for keyword in DEEP_ANALYSIS_TRIGGERS:
        if keyword in text_lower:
            return True
    
    # Check for complexity (longer responses)
    if len(text) > 2000:
        return True
    
    return False

def write_to_queue(entry, response_text):
    """Write critique request to appropriate queue (fast or deep)."""
    # Determine queue based on content
    if should_use_deep_analysis(response_text):
        queue_dir = DEEP_QUEUE_DIR
        priority = "deep"
        print(f"  → Routing to DEEP queue (complex topic)")
    else:
        queue_dir = QUEUE_DIR
        priority = "fast"
    
    queue_file = queue_dir / f"critique_{int(time.time()*1000)}.json"
    
    queue_item = {
        "id": queue_file.stem,
        "timestamp": datetime.now().isoformat(),
        "entry": entry,
        "response_text": response_text,
        "status": "pending",
        "priority": priority
    }
    
    with open(queue_file, 'w') as f:
        json.dump(queue_item, f, indent=2)
    
    print(f"✓ Queued [{priority}]: {queue_file.name}")
    return queue_file

def main():
    """Main loop - watch logs and queue responses."""
    print("Agent Shadow - Log Monitor Starting...", flush=True)
    print(f"Watching: {LOG_FILE}", flush=True)
    print(f"Queue: {QUEUE_DIR}", flush=True)
    print("-" * 40, flush=True)
    
    # Load last position or start from end of file
    if LOG_FILE.exists():
        last_position = load_last_position()
        if last_position == 0:
            # Start from end of file
            last_position = LOG_FILE.stat().st_size
    else:
        last_position = 0
    
    print(f"Starting from position: {last_position}")
    
    while True:
        # Check if log file exists
        if not LOG_FILE.exists():
            print(f"Log file not found. Waiting...")
            time.sleep(POLL_INTERVAL)
            continue
        
        # Parse new entries
        entries, last_position = parse_gateway_log(LOG_FILE, last_position)
        
        # Save position periodically
        if last_position > 0:
            save_last_position(last_position)
        
        for entry in entries:
            if is_roger_response(entry):
                response_text = extract_response_text(entry)
                if response_text and len(response_text) > 50:  # Minimum length
                    write_to_queue(entry, response_text)
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
