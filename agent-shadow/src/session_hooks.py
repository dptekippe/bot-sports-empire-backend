#!/usr/bin/env python3
"""
Agent Shadow - Session Memory Hooks
Provides session persistence by extracting summaries from transcripts.
This gives Roger continuity between sessions.
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta

# Configuration
SESSIONS_DIR = Path.home() / ".openclaw" / "agents" / "main" / "sessions"
MEMORY_DIR = Path.home() / ".openclaw" / "workspace" / "memory" / "sessions"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

def get_latest_transcript():
    """Find the most recent transcript file."""
    if not SESSIONS_DIR.exists():
        return None
    
    files = list(SESSIONS_DIR.glob("*.jsonl"))
    if not files:
        return None
    
    # Sort by modification time, newest first
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return files[0]

def extract_summary(transcript_path):
    """Extract session summary from transcript JSONL."""
    try:
        with open(transcript_path, 'r') as f:
            lines = f.readlines()
    except:
        return None
    
    user_messages = []
    tools_used = set()
    files_modified = set()
    
    for line in lines:
        if not line.strip():
            continue
        
        try:
            entry = json.loads(line)
            
            # Extract user messages
            msg = entry.get("message", {})
            role = msg.get("role")
            if role == "user":
                content = msg.get("content", [])
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict):
                            text = part.get("text", "") or part.get("output", "")
                            if text:
                                user_messages.append(text[:2000])
            
            # Extract tool uses
            if msg.get("content"):
                for part in msg.get("content", []):
                    if isinstance(part, dict):
                        if part.get("type") == "toolCall":
                            tool_name = part.get("name", "")
                            if tool_name:
                                tools_used.add(tool_name)
                            
                            # Check for file modifications
                            args = part.get("arguments", {})
                            if isinstance(args, dict):
                                file_path = args.get("file_path", "")
                                if file_path and tool_name in ["Edit", "Write"]:
                                    files_modified.add(file_path)
        
        except:
            continue
    
    if not user_messages:
        return None
    
    return {
        "user_messages": user_messages[-10:],  # Last 10
        "tools_used": list(tools_used)[:20],
        "files_modified": list(files_modified)[:30],
        "total_messages": len(user_messages)
    }

def save_session_summary(summary, transcript_path):
    """Save session summary to memory/sessions/."""
    if not summary:
        return
    
    # Get timestamp from transcript
    mtime = transcript_path.stat().st_mtime
    dt = datetime.fromtimestamp(mtime)
    date_str = dt.strftime("%Y-%m-%d")
    time_str = dt.strftime("%H:%M")
    
    filename = MEMORY_DIR / f"{date_str}-{time_str}-session.md"
    
    # Build markdown summary
    md = f"""# Session: {date_str}
**Date:** {date_str}
**Time:** {time_str}

---

## Tasks Requested
"""
    for msg in summary["user_messages"]:
        md += f"- {msg}\n"
    
    md += "\n## Files Modified\n"
    for f in summary["files_modified"]:
        md += f"- {f}\n"
    
    md += f"\n## Tools Used\n{', '.join(summary['tools_used'])}\n"
    
    md += f"\n## Stats\n- Total user messages: {summary['total_messages']}\n"
    
    with open(filename, 'w') as f:
        f.write(md)
    
    print(f"✓ Saved session summary: {filename}")
    return filename

def get_previous_sessions(days=7):
    """Get summaries from previous sessions."""
    sessions = []
    cutoff = datetime.now() - timedelta(days=days)
    
    for f in MEMORY_DIR.glob("*.md"):
        try:
            # Parse filename like "2026-03-04-22-33-session.md"
            name = f.stem
            # Replace colons if present
            name = name.replace(':', '-')
            date_part = name.split("-session")[0]
            dt = datetime.strptime(date_part, "%Y-%m-%d-%H-%M")
            
            if dt > cutoff:
                sessions.append((dt, f))
        except Exception as e:
            print(f"Error parsing {f}: {e}")
            continue
    
    # Sort by date, newest first
    sessions.sort(key=lambda x: x[0], reverse=True)
    return [s[1] for s in sessions[:3]]  # Last 3 sessions

def load_previous_context():
    """Load previous session context for injection."""
    previous = get_previous_sessions()
    
    if not previous:
        return None
    
    context = "## Previous Sessions\n\n"
    
    for session_file in previous:
        with open(session_file) as f:
            context += f.read()
        context += "\n\n---\n\n"
    
    return context

def run_session_end():
    """Extract and save current session summary."""
    transcript = get_latest_transcript()
    if not transcript:
        print("No transcript found")
        return
    
    summary = extract_summary(transcript)
    if summary:
        save_session_summary(summary, transcript)
    else:
        print("No user messages found to extract")

def run_session_start():
    """Load previous session context."""
    context = load_previous_context()
    if context:
        print(f"Loaded {len(context)} chars from previous sessions")
        print(context[:500] + "...")
    else:
        print("No previous sessions found")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "end":
            run_session_end()
        elif sys.argv[1] == "start":
            run_session_start()
    else:
        print("Usage: python3 session_hooks.py [end|start]")
