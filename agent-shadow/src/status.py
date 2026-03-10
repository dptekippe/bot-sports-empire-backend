#!/usr/bin/env python3
"""
Agent Shadow - CLI Status
Quick status check from command line.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent

def main():
    print("🌓 Agent Shadow - Status")
    print("=" * 40)
    
    # Check queues
    queue_dir = BASE_DIR / "src" / "queue"
    deep_queue_dir = BASE_DIR / "src" / "queue_deep"
    output_dir = BASE_DIR / "src" / "output"
    
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Fast queue
    if queue_dir.exists():
        fast_pending = len(list(queue_dir.glob("critique_*.json")))
        print(f"Fast Queue:     {fast_pending} pending")
    else:
        print("Fast Queue:     not found")
    
    # Deep queue
    if deep_queue_dir.exists():
        deep_pending = len(list(deep_queue_dir.glob("critique_*.json")))
        print(f"Deep Queue:     {deep_pending} pending")
    else:
        print("Deep Queue:     not found")
    
    # Completed
    if output_dir.exists():
        completed = len(list(output_dir.glob("*_critique.json")))
        deep_completed = len(list(output_dir.glob("*_deep_critique.json")))
        print(f"Completed:      {completed + deep_completed}")
    
    print()
    
    # Config
    config_file = BASE_DIR / "config" / "settings.json"
    if config_file.exists():
        with open(config_file) as f:
            config = json.load(f)
        print("Configuration:")
        print(f"  Auto-inject:  {config.get('auto_inject', False)}")
        print(f"  Fast model:   {config.get('models', {}).get('fast', 'qwen3.5:4b')}")
        print(f"  Deep model:  {config.get('models', {}).get('deep', 'qwen3.5:9b')}")
    
    print()
    print(f"Dashboard: http://localhost:18787")

if __name__ == "__main__":
    main()
