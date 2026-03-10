#!/usr/bin/env python3
"""
Agent Shadow - Fast Critic Subagent
Reads from queue and critiques responses using Qwen3.5:4b via Ollama.
"""

import json
import os
import time
from pathlib import Path
import requests

# Configuration
QUEUE_DIR = Path(__file__).parent / "queue"
OUTPUT_DIR = Path(__file__).parent / "output"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3.5:4b"
POLL_INTERVAL = 3  # seconds

# Ensure directories exist
QUEUE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Critique prompt template
CRITIQUE_PROMPT = """You are a senior editor reviewing an AI agent's response for depth, risks, and blindspots.

Evaluate this response and provide feedback in JSON format:

Response to evaluate:
---
{response_text}
---

Provide your critique as JSON with these fields:
{{
    "risks": ["what could go wrong or be misunderstood"],
    "assumptions": ["what's being assumed that might not be true"],
    "blindspots": ["important perspectives or information that are missing"],
    "depth_gaps": ["areas that are too shallow or need more nuance"],
    "alternatives": ["other approaches or viewpoints worth considering"],
    "overall_score": 1-10,
    "summary": "One sentence summary of the main critique"
}}

Only output valid JSON, no markdown formatting.
"""

def get_pending_critique():
    """Get the oldest pending critique from queue."""
    queue_files = sorted(QUEUE_DIR.glob("critique_*.json"))
    
    for queue_file in queue_files:
        try:
            with open(queue_file, 'r') as f:
                item = json.load(f)
            
            if item.get("status") == "pending":
                return queue_file, item
                
        except Exception as e:
            print(f"Error reading {queue_file}: {e}")
    
    return None, None

def send_to_ollama(prompt, model=MODEL):
    """Send prompt to Ollama and get response."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "")
        else:
            print(f"Ollama error: {response.status_code}")
            return None
    except requests.exceptions.Timeout:
        print("Ollama timeout")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def parse_critique(response_text):
    """Parse JSON critique from Ollama response."""
    try:
        # Find JSON in response
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        
        if start >= 0 and end > start:
            json_str = response_text[start:end]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    return None

def save_critique(queue_file, original_item, critique):
    """Save critique result."""
    # Update original item
    original_item["status"] = "completed"
    original_item["critique"] = critique
    
    # Save to output
    output_file = OUTPUT_DIR / f"{original_item['id']}_critique.json"
    
    with open(output_file, 'w') as f:
        json.dump(original_item, f, indent=2)
    
    # Mark queue item as done
    with open(queue_file, 'w') as f:
        json.dump(original_item, f, indent=2)
    
    print(f"✓ Critique saved: {output_file.name}")
    return output_file

def main():
    """Main loop - process critique queue."""
    print("Agent Shadow - Fast Critic Starting...")
    print(f"Queue: {QUEUE_DIR}")
    print(f"Model: {MODEL}")
    print("-" * 40)
    
    while True:
        queue_file, item = get_pending_critique()
        
        if queue_file is None:
            time.sleep(POLL_INTERVAL)
            continue
        
        print(f"Processing: {item['id']}")
        
        # Build prompt
        prompt = CRITIQUE_PROMPT.format(response_text=item["response_text"])
        
        # Send to Ollama
        print("  → Sending to Qwen...")
        response = send_to_ollama(prompt)
        
        if response:
            critique = parse_critique(response)
            
            if critique:
                print(f"  ✓ Critique received (score: {critique.get('overall_score', 'N/A')})")
                save_critique(queue_file, item, critique)
                
                # Print summary
                if critique.get("summary"):
                    print(f"    Summary: {critique['summary']}")
                if critique.get("risks"):
                    print(f"    Risks: {', '.join(critique['risks'][:2])}")
            else:
                print("  ✗ Failed to parse critique")
                item["status"] = "error"
                with open(queue_file, 'w') as f:
                    json.dump(item, f)
        else:
            print("  ✗ Ollama request failed")
            item["status"] = "error"
            with open(queue_file, 'w') as f:
                json.dump(item, f)
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
