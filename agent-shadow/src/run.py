#!/usr/bin/env python3
"""
Agent Shadow - Main Launcher
Starts all subagents for real-time response evaluation.
"""

import subprocess
import sys
import time
import os
from pathlib import Path

# Get the script directory (parent of src)
SCRIPT_DIR = Path(__file__).parent.parent

def start_subagent(script_name, label):
    """Start a subagent script."""
    script_path = SCRIPT_DIR / "src" / script_name
    
    print(f"Starting {label}...")
    
    process = subprocess.Popen(
        [sys.executable, str(script_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    return process

def main():
    print("=" * 50)
    print("Agent Shadow - Starting")
    print("=" * 50)
    
    # Check if Ollama is running
    import requests
    try:
        r = requests.get("http://localhost:11434/", timeout=5)
        print(f"✓ Ollama: {r.text}")
    except:
        print("✗ Ollama not responding")
        return
    
    # Start subagents
    processes = []
    
    # Start Log Monitor
    p1 = start_subagent("log_monitor.py", "Log Monitor")
    processes.append(("Log Monitor", p1))
    
    time.sleep(2)
    
    # Start Fast Critic  
    p2 = start_subagent("fast_critic.py", "Fast Critic")
    processes.append(("Fast Critic", p2))
    
    time.sleep(2)
    
    # Start Injector
    p3 = start_subagent("injector.py", "Injector")
    processes.append(("Injector", p3))
    
    time.sleep(2)
    
    # Start Deep Critic (for complex topics)
    p4 = start_subagent("deep_critic.py", "Deep Critic")
    processes.append(("Deep Critic", p4))
    
    # Optionally start dashboard (uncomment to enable)
    # p5 = start_subagent("dashboard.py", "Dashboard")
    # processes.append(("Dashboard", p5))
    
    print("\n" + "=" * 50)
    print("Agent Shadow Running")
    print("=" * 50)
    print("\nMonitoring logs, critiquing, and injecting...")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        # Monitor processes
        while True:
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"\n{name} stopped")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nStopping Agent Shadow...")
        
    finally:
        for name, proc in processes:
            proc.terminate()
            print(f"Stopped {name}")

if __name__ == "__main__":
    main()
