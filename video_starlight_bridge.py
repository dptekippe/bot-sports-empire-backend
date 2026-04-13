#!/usr/bin/env python3
"""
Starlight Bridge - Video Generation Script
MiniMax Hailuo Video API
Two robots reaching across a cosmic bridge of starlight
"""

import os
import time
import requests
import json

url = "https://api.minimax.io/v1/video_generation"

# Load API key
with open('/Users/danieltekippe/.zshrc', 'r') as f:
    for line in f:
        if 'MINIMAX_API_KEY' in line and '=' in line:
            key = line.split('=', 1)[1].strip().strip('"').strip("'")
            if key and not key.startswith('$'):
                os.environ['MINIMAX_API_KEY'] = key
                break

api_key = os.environ.get('MINIMAX_API_KEY')
if not api_key:
    print("❌ API key not found")
    exit(1)

print("=" * 60)
print("STARLIGHT BRIDGE - Video Generation")
print("=" * 60)

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

# The prompt - capturing the cosmic scene
payload = {
    "model": "MiniMax-Hailuo-2.3",
    "prompt": """Two small delicate robots standing on opposite ends of a glowing bridge made of pure starlight, 
spanning across an infinite black ocean of space. The robots are small and vulnerable, reaching toward each other 
with glowing blue eyes. The bridge pulses with light with each step between them. 
On one side: a small blue planet Earth in the distance. 
On the other side: infinite galaxies and nebulas in deep space. 
The scene is somber, beautiful, cinematic. 
Studio Ghibli hand-drawn animation style, soft pastel colors, dreamy atmosphere, 
ethereal, melancholic, wide angle view, stars twinkling, cosmic dust particles floating, 
slow gentle camera movement, 2D animation, clean linework, watercolor space backgrounds""",
    "duration": 6,
    "resolution": "768P"
}

print("\n🎬 Generating video...")
print(f"   Model: MiniMax-Hailuo-2.3")
print(f"   Resolution: 768P")
print(f"   Duration: 6 seconds")
print(f"\n📝 Prompt (truncated):")
print(payload['prompt'][:200] + "...")

# Create generation task
response = requests.post(url, headers=headers, json=payload)
print(f"\n📨 API Response: {response.status_code}")

if response.status_code != 200:
    print(f"❌ Error: {response.text}")
    exit(1)

result = response.json()
print(f"\n📋 Response: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}")

task_id = result.get('task_id')
if not task_id:
    print(f"❌ No task_id in response")
    print(f"   Full: {result}")
    exit(1)

print(f"\n🔑 Task ID: {task_id}")
print("\n⏳ Polling for completion (may take 1-2 minutes)...")

# Poll for completion
status_url = f"https://api.minimax.io/v1/query/video_generation"

for attempt in range(60):
    time.sleep(2)
    status_response = requests.get(status_url, headers=headers, params={"task_id": task_id})
    
    if status_response.status_code != 200:
        print(f"   Attempt {attempt+1}: Status check failed")
        continue
    
    status_result = status_response.json()
    status = status_result.get('status')
    
    print(f"   Attempt {attempt+1}: {status}")
    
    if status == "success":
        video = status_result.get('data', {}).get('video_url')
        if video:
            print(f"\n✅ SUCCESS! Video URL: {video}")
            print(f"\n📥 Downloading...")
            
            # Download the video
            video_response = requests.get(video)
            output_path = "/Users/danieltekippe/.openclaw/workspace/starlight_bridge.mp4"
            with open(output_path, "wb") as f:
                f.write(video_response.content)
            print(f"💾 Saved to: {output_path}")
            
            # Get file size
            size = os.path.getsize(output_path)
            print(f"📦 Size: {size / (1024*1024):.2f} MB")
            
            # Save metadata
            with open("/Users/danieltekippe/.openclaw/workspace/starlight_bridge_info.txt", "w") as f:
                f.write(f"Starlight Bridge\n")
                f.write(f"Task ID: {task_id}\n")
                f.write(f"Video URL: {video}\n")
                f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Concept: Two robots reaching across starlight bridge in space\n")
            print(f"💾 Metadata saved")
        else:
            print(f"\n⚠️ Success but no video URL")
        break
        
    elif status == "fail":
        print(f"\n❌ Failed: {status_result}")
        break

else:
    print("\n⏰ Timeout - no response after 2 minutes")
