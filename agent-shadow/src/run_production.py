#!/usr/bin/env python3
"""
Agent Shadow - Production Launcher
Starts all subagents with proper error handling and logging.
"""

import subprocess
import sys
import time
import os
import signal
from pathlib import Path

# Get the script directory (parent of src)
SCRIPT_DIR = Path(__file__).parent.parent

def start_subagent(script_name, label):
    """Start a subagent script with error handling."""
    script_path = SCRIPT_DIR / "src" / script_name
    
    print(f"Starting {label}...")
    
    try:
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(SCRIPT_DIR / "src")
        )
        return process, None
    except Exception as e:
        return None, str(e)

def main():
    print("=" * 50)
    print("Agent Shadow - Starting")
    print("=" * 50)
    
    # Check if Ollama is running
    import requests
    try:
        r = requests.get("http://localhost:11434/", timeout=5)
        print(f"✓ Ollama: {r.text}")
    except Exception as e:
        print(f"✗ Ollama not responding: {e}")
        print("  Agent Shadow requires Ollama to be running.")
        return
    
    # Check log file exists
    log_file = Path.home() / ".openclaw" / "logs" / "gateway.log"
    if not log_file.exists():
        print(f"⚠ Warning: Log file not found: {log_file}")
        print("  Agent Shadow will wait for log file...")
    
    # Start subagents (Critique System Only)
    processes = []
    subagents = [
        ("chat_monitor.py", "Response Monitor"),  # Watches my responses
        ("log_monitor.py", "Log Monitor"),        # Watches system events
        ("fast_critic.py", "Fast Critic"),       # Quick critique with 4b
        ("deep_critic.py", "Deep Critic"),        # Deep analysis with 9b
        ("injector.py", "Injector"),             # Reviews & injects
    ]
    
    for script, label in subagents:
        proc, err = start_subagent(script, label)
        if err:
            print(f"✗ Failed to start {label}: {err}")
        else:
            processes.append((label, proc))
    
    if not processes:
        print("✗ No subagents started. Exiting.")
        return
    
    print("\n" + "=" * 50)
    print("Agent Shadow Running")
    print("=" * 50)
    print(f"Monitoring: {log_file}")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        # Monitor processes
        while True:
            all_dead = True
            for label, proc in processes:
                ret = proc.poll()
                if ret is not None:
                    print(f"⚠ {label} stopped (exit code: {ret})")
                else:
                    all_dead = False
            
            if all_dead and processes:
                print("✗ All subagents stopped. Exiting.")
                break
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\nStopping Agent Shadow...")
        
    finally:
        for label, proc in processes:
            if proc.poll() is None:
                proc.terminate()
                print(f"Stopped {label}")

if __name__ == "__main__":
    main()
