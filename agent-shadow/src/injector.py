#!/usr/bin/env python3
"""
Agent Shadow - Injection Subagent
Reads completed critiques and memory recall items, injects them back into OpenClaw session.
"""

import json
import time
from pathlib import Path
import subprocess
import sys

# Configuration
OUTPUT_DIR = Path(__file__).parent / "output"
MEMORY_QUEUE_DIR = Path(__file__).parent / "queue_memory"
INJECTION_LOG = Path(__file__).parent / "injection.log"
POLL_INTERVAL = 5  # seconds
RATE_LIMIT_SECONDS = 30  # Don't inject too frequently

# Last injection time
last_injection = 0

def get_injection_mode():
    """Check if auto-injection is enabled."""
    config_file = Path(__file__).parent.parent / "config" / "settings.json"
    if config_file.exists():
        try:
            with open(config_file) as f:
                config = json.load(f)
            return config.get("auto_inject", False)
        except:
            pass
    return False

def should_skip_injection(text):
    """Check if we should skip injection for this content."""
    skip_keywords = [
        "private", "confidential", "secret",
        "password", "api_key", "token",
        "system", "debug", "internal"
    ]
    
    text_lower = text.lower()
    for keyword in skip_keywords:
        if keyword in text_lower:
            return True
    return False

def inject_via_sessions_send(message):
    """Inject message using sessions_send tool."""
    global last_injection
    
    # Rate limiting
    now = time.time()
    if now - last_injection < RATE_LIMIT_SECONDS:
        print(f"Rate limited. Wait {RATE_LIMIT_SECONDS - (now - last_injection):.0f}s")
        return False
    
    # In a real implementation, this would call sessions_send
    # For now, we'll simulate and log
    print(f"[INJECT] Would send to session: {message[:100]}...")
    
    # Log the injection
    with open(INJECTION_LOG, "a") as f:
        f.write(f"{time.time()}: {message}\n")
    
    last_injection = now
    return True

def process_completed_critiques():
    """Find and process completed critiques."""
    if not OUTPUT_DIR.exists():
        return []
    
    processed = []
    
    for critique_file in OUTPUT_DIR.glob("*_critique.json"):
        try:
            with open(critique_file) as f:
                item = json.load(f)
            
            # Check if already injected
            if item.get("injected"):
                continue
            
            # Check for critical issues that should always be injected
            critique = item.get("critique", {})
            score = critique.get("overall_score", 5)
            risks = critique.get("risks", [])
            
            # Inject if: low score OR high risk items
            if score <= 4 or len(risks) >= 2:
                processed.append(item)
                
        except Exception as e:
            print(f"Error reading {critique_file}: {e}")
    
    return processed

def process_memory_recall():
    """Find and process memory recall items from output directory."""
    if not OUTPUT_DIR.exists():
        return []
    
    processed = []
    
    # Check OUTPUT_DIR for memory recall results
    for memory_file in OUTPUT_DIR.glob("*_memory.json"):
        try:
            with open(memory_file) as f:
                item = json.load(f)
            
            # Check if already injected
            if item.get("injected"):
                continue
            
            processed.append(item)
                
        except Exception as e:
            print(f"Error reading {memory_file}: {e}")
    
    return processed

def main():
    """Main loop - check for critiques and memory recall to inject."""
    print("Agent Shadow - Injection Subagent Starting...")
    print(f"Output Dir: {OUTPUT_DIR}")
    print(f"Memory Queue: {MEMORY_QUEUE_DIR}")
    print(f"Auto-inject: {get_injection_mode()}")
    print("-" * 40)
    
    # Create dirs if needed
    OUTPUT_DIR.mkdir(exist_ok=True)
    MEMORY_QUEUE_DIR.mkdir(exist_ok=True)
    
    while True:
        # Check for completed critiques
        critiques = process_completed_critiques()
        memory_items = process_memory_recall()
        
        if critiques:
            print(f"Found {len(critiques)} critiques to review")
            
            for item in critiques:
                response_text = item.get("response_text", "")[:200]
                critique = item.get("critique", {})
                
                print(f"\n{item['id']}:")
                print(f"  Response: {response_text}...")
                print(f"  Score: {critique.get('overall_score', 'N/A')}")
                print(f"  Risks: {critique.get('risks', [])}")
                
                # Check for skip keywords
                if should_skip_injection(response_text):
                    print("  → Skipping (private content)")
                    item["injected"] = False
                    item["skip_reason"] = "private_content"
                    with open(OUTPUT_DIR / f"{item['id']}_critique.json", "w") as f:
                        json.dump(item, f, indent=2)
                    continue
                
                # Build injection message
                risks = critique.get("risks", [])
                if risks:
                    msg = f"[Agent Shadow Critique] Consider: {risks[0]}"
                    
                    if get_injection_mode():
                        inject_via_sessions_send(msg)
                        item["injected"] = True
                    else:
                        print(f"  → Would inject: {msg}")
                        item["injected"] = "pending"
                    
                    # Save updated status
                    with open(OUTPUT_DIR / f"{item['id']}_critique.json", "w") as f:
                        json.dump(item, f, indent=2)
        
        # Handle memory recall
        if memory_items:
            print(f"Found {len(memory_items)} memory recall items")
            
            for item in memory_items:
                reminder = item.get("reminder", "")
                topic = item.get("topic", "")
                
                if reminder:
                    print(f"\n{item['id']}:")
                    print(f"  Topic: {topic}")
                    print(f"  Reminder: {reminder}")
                    
                    # Build memory injection message
                    msg = f"[Memory Recall] {reminder}"
                    
                    if get_injection_mode():
                        inject_via_sessions_send(msg)
                        item["injected"] = True
                    else:
                        print(f"  → Would inject: {msg}")
                        item["injected"] = "pending"
                    
                    # Save updated status
                    output_file = OUTPUT_DIR / f"{item['id']}_memory.json"
                    with open(output_file, 'w') as f:
                        json.dump(item, f, indent=2)
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
