#!/usr/bin/env python3
"""
Agent Shadow - Deep Critic Subagent
Reads from queue and provides deep analysis using Qwen3.5:9b via Ollama.
Used for complex topics that need thorough analysis.
"""

import json
import time
from pathlib import Path
import requests

# Configuration
QUEUE_DIR = Path(__file__).parent / "queue"
OUTPUT_DIR = Path(__file__).parent / "output"
DEEP_QUEUE_DIR = Path(__file__).parent / "queue_deep"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3.5:9b"
POLL_INTERVAL = 5  # seconds

# Ensure directories exist
QUEUE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
DEEP_QUEUE_DIR.mkdir(exist_ok=True)

# Deep critique prompt template
DEEP_CRITIQUE_PROMPT = """You are a senior AI researcher providing an in-depth critique of an AI agent's response.

Analyze this response thoroughly, considering:
1. Logical soundness
2. Factual accuracy  
3. Edge cases and exceptions
4. Alternative perspectives
5. Potential unintended consequences
6. Philosophical implications

Response to evaluate:
---
{response_text}
---

Provide your critique as detailed JSON:
{{
    "strengths": ["what works well in this response"],
    "weaknesses": ["areas that need improvement"],
    "risks": ["potential issues or negative consequences"],
    "assumptions": ["unstated assumptions that could be wrong"],
    "alternatives": ["different approaches worth considering"],
    "questions_raised": ["interesting questions this raises"],
    "depth_score": 1-10,
    "summary": "2-3 sentence overall assessment"
}}

Only output valid JSON, no markdown formatting.
"""

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

def get_pending_deep_critique():
    """Get the oldest pending deep critique from queue."""
    queue_files = sorted(DEEP_QUEUE_DIR.glob("critique_*.json"))
    
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
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "")
        else:
            print(f"Ollama error: {response.status_code}")
            return None
    except requests.exceptions.Timeout:
        print("Ollama timeout (120s)")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def parse_critique(response_text):
    """Parse JSON critique from Ollama response."""
    try:
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        
        if start >= 0 and end > start:
            json_str = response_text[start:end]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    return None

def main():
    """Main loop - process deep critique queue."""
    print("Agent Shadow - Deep Critic Starting...")
    print(f"Queue: {DEEP_QUEUE_DIR}")
    print(f"Model: {MODEL}")
    print("-" * 40)
    
    while True:
        queue_file, item = get_pending_deep_critique()
        
        if queue_file is None:
            time.sleep(POLL_INTERVAL)
            continue
        
        print(f"Processing deep critique: {item['id']}")
        
        # Build prompt
        prompt = DEEP_CRITIQUE_PROMPT.format(response_text=item["response_text"])
        
        # Send to Ollama (9b model)
        print("  → Deep analysis with Qwen3.5:9b...")
        response = send_to_ollama(prompt)
        
        if response:
            critique = parse_critique(response)
            
            if critique:
                print(f"  ✓ Deep critique received (depth: {critique.get('depth_score', 'N/A')})")
                
                # Save to output
                item["status"] = "completed"
                item["deep_critique"] = critique
                
                output_file = OUTPUT_DIR / f"{item['id']}_deep_critique.json"
                with open(output_file, 'w') as f:
                    json.dump(item, f, indent=2)
                
                # Mark queue item as done
                with open(queue_file, 'w') as f:
                    json.dump(item, f)
                
                print(f"  ✓ Saved: {output_file.name}")
                
                # Print summary
                if critique.get("summary"):
                    print(f"    Summary: {critique['summary']}")
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
