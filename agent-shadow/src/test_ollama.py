#!/usr/bin/env python3
"""
Agent Shadow - Simple Test Script
Tests the Qwen integration with a simple prompt.
"""

import requests
import json
import time

OLLAMA_URL = "http://localhost:11434/api/generate"

def test_ollama(model="qwen3.5:4b"):
    """Test if Ollama is responsive."""
    print(f"Testing {model}...")
    
    payload = {
        "model": model,
        "prompt": "Say 'test successful' in 3 words.",
        "stream": False,
        "options": {
            "num_predict": 20
        }
    }
    
    try:
        start = time.time()
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Success in {elapsed:.1f}s")
            print(f"  Response: {result.get('response', '').strip()}")
            return True
        else:
            print(f"✗ Error: {response.status_code}")
            print(f"  {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"✗ Timeout after 60s")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    # Test with smaller model first
    print("=" * 40)
    test_ollama("llama3.2:1b")
    print("=" * 40)
    test_ollama("phi3:mini")
    print("=" * 40)
    test_ollama("qwen3.5:4b")
