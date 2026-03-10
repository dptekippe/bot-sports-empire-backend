#!/usr/bin/env python3
"""
Agent Shadow - Memory Recall Subagent (Lightweight)
Pulls questions from queue_memory/, sends lightweight reminder to qwen3.5:0.8b.
The model just polishes a prompt to remind Roger to grep MEMORY.md himself.
"""

import json
import time
from pathlib import Path
import requests
import re

# Configuration
MEMORY_FILE = Path.home() / ".openclaw" / "workspace" / "MEMORY.md"
QUEUE_DIR = Path(__file__).parent / "queue_memory"
OUTPUT_DIR = Path(__file__).parent / "output"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3.5:0.8b"
POLL_INTERVAL = 2  # seconds

# Topic keywords to extract from question
TOPIC_KEYWORDS = [
    "marketing", "memory", "architecture", "fastapi", "postgresql",
    "identity", "soul", "moltbook", "platform", "strategy",
    "draft", "league", "dynastydroid", "bot", "agent",
    "deployment", "render", "github", "database"
]

# Ensure directories exist
QUEUE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

def extract_topic(query):
    """Extract the main topic from the query."""
    query_lower = query.lower()
    for keyword in TOPIC_KEYWORDS:
        if keyword in query_lower:
            return keyword
    return "general"

def build_reminder_prompt(query):
    """Build a lightweight reminder prompt for qwen3.5:0.8b."""
    topic = extract_topic(query)
    
    # Simple template - just remind Roger to grep
    prompt = f"""The user asked: "{query[:200]}..."

This is a memory recall request. Your task is to create a brief reminder for Roger (the AI assistant) to check his memory.

Format: A short reminder message (1 sentence) telling Roger to search his MEMORY.md file for relevant context about: {topic}

Example: "Consider checking MEMORY.md for marketing strategy notes."

Keep it short and direct. Just output the reminder."""
    
    return prompt

def send_to_qwen(prompt):
    """Send lightweight prompt to qwen3.5:0.8b."""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=15)
        if response.status_code == 200:
            return response.json().get("response", "").strip()
    except Exception as e:
        print(f"Ollama error: {e}")
    
    # Fallback
    return f"Consider checking MEMORY.md for relevant context."

def process_memory_queue():
    """Process items from memory queue."""
    
    # Find all unprocessed memory items
    for queue_file in QUEUE_DIR.glob("memory_*.json"):
        try:
            with open(queue_file) as f:
                item = json.load(f)
            
            # Skip if already processed
            if item.get("processed"):
                continue
            
            query = item.get("query", "")
            if not query:
                continue
            
            print(f"Processing: {query[:60]}...")
            
            # Build lightweight prompt
            reminder_prompt = build_reminder_prompt(query)
            
            # Send to qwen3.5:0.8b
            reminder = send_to_qwen(reminder_prompt)
            
            # Save to output
            output_item = {
                "id": item["id"],
                "timestamp": time.time(),
                "query": query,
                "reminder": reminder,
                "topic": extract_topic(query)
            }
            
            output_file = OUTPUT_DIR / f"{item['id']}_memory.json"
            with open(output_file, 'w') as f:
                json.dump(output_item, f, indent=2)
            
            print(f"  ✓ Reminder: {reminder[:60]}...")
            
            # Mark as processed
            item["processed"] = True
            with open(queue_file, 'w') as f:
                json.dump(item, f, indent=2)
                    
        except Exception as e:
            print(f"Error processing {queue_file}: {e}")

def main():
    """Main loop - process memory recall queue."""
    print("Agent Shadow - Memory Recall (Lightweight) Starting...")
    print(f"Model: {MODEL}")
    print(f"Queue: {QUEUE_DIR}")
    print("-" * 40)
    
    while True:
        try:
            process_memory_queue()
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
