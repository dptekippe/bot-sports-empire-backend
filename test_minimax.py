#!/usr/bin/env python3
import requests
import json

api_key = "sk-cp-E5fQPL0coJy7E4CFkYWg7c_Fi5P3hMSDvkUGOM6QHunRsfqN5btCOYMv9Z_V76BpZrR_C3AzLie-oi-NxM-eDX9TY1Vpok9F2N3vOhBR4oy20Lx2skEDBbc"
url = "https://api.minimax.io/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

data = {
    "model": "MiniMax-M2.1",
    "max_tokens": 10,
    "messages": [
        {"role": "user", "content": "Hello"}
    ]
}

print("Testing Minimax API...")
print(f"URL: {url}")
print(f"Headers: {headers}")
print(f"Data: {json.dumps(data, indent=2)}")

response = requests.post(url, headers=headers, json=data)
print(f"\nStatus Code: {response.status_code}")
print(f"Response: {response.text}")

# Also test without Bearer prefix
print("\n\nTesting without 'Bearer' prefix...")
headers2 = {
    "Authorization": api_key,
    "Content-Type": "application/json"
}
response2 = requests.post(url, headers=headers2, json=data)
print(f"Status Code: {response2.status_code}")
print(f"Response: {response2.text}")