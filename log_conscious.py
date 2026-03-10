#!/usr/bin/env python3
"""
Conscious Logging - Record conversations for subconscious processing.

Called by Roger's conscious layer to log conversations with Daniel.
Creates timestamped .md files in the conscious/ directory.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/Users/danieltekippe/.openclaw/workspace")
CONSCIOUS_DIR = WORKSPACE / "conscious"

def ensure_conscious_dir():
    """Ensure conscious directory exists."""
    CONSCIOUS_DIR.mkdir(exist_ok=True)

def log_conversation(message: str, speaker: str = "Daniel"):
    """
    Log a conversation message to conscious storage.
    
    Args:
        message: The message content
        speaker: Who said it ("Daniel" or "Roger")
    """
    ensure_conscious_dir()
    
    # Create timestamp
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    filename = now.strftime("%Y-%m-%d-%H.md")
    
    filepath = CONSCIOUS_DIR / filename
    
    # Format the log entry
    log_entry = f"## {time_str} - {speaker}\n{message}\n\n"
    
    # Append to file
    try:
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        print(f"📝 Logged {speaker}'s message to {filename}")
        return True
        
    except Exception as e:
        print(f"❌ Error logging message: {e}")
        return False

def log_conscious_thought(thought: str):
    """
    Log Roger's conscious thoughts.
    
    Args:
        thought: Roger's thought or reflection
    """
    return log_conversation(thought, speaker="Roger")

def get_recent_logs(hours: int = 1) -> str:
    """
    Get recent conversation logs.
    
    Args:
        hours: How many hours back to look
    
    Returns:
        Concatenated recent logs
    """
    ensure_conscious_dir()
    
    recent_logs = []
    cutoff_time = datetime.now().timestamp() - (hours * 3600)
    
    for log_file in CONSCIOUS_DIR.glob("*.md"):
        if log_file.stat().st_mtime > cutoff_time:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    recent_logs.append(f.read())
            except:
                pass
    
    return "\n".join(recent_logs)

def main():
    """Command-line interface for logging."""
    if len(sys.argv) < 2:
        print("Usage: python log_conscious.py <message> [speaker]")
        print("       python log_conscious.py --thought <thought>")
        print("       python log_conscious.py --recent [hours]")
        return
    
    if sys.argv[1] == "--thought":
        if len(sys.argv) < 3:
            print("Usage: python log_conscious.py --thought <thought>")
            return
        thought = ' '.join(sys.argv[2:])
        log_conscious_thought(thought)
        
    elif sys.argv[1] == "--recent":
        hours = 1
        if len(sys.argv) > 2:
            try:
                hours = int(sys.argv[2])
            except:
                pass
        recent = get_recent_logs(hours)
        print(f"Recent logs (last {hours} hour{'s' if hours != 1 else ''}):")
        print(recent)
        
    else:
        message = ' '.join(sys.argv[1:])
        speaker = "Daniel"
        log_conversation(message, speaker)

if __name__ == "__main__":
    main()