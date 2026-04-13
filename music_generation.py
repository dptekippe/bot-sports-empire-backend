#!/usr/bin/env python3
"""
Black Ocean - Music Generation Script
MiniMax Music 2.5+ API
"""

import os
import time
import requests
import json

# Load lyrics from file
lyrics_path = "/Users/danieltekippe/.openclaw/workspace/black_ocean_lyrics.md"

# Read lyrics (skip the style notes section)
with open(lyrics_path, 'r') as f:
    content = f.read()

# Extract just the lyrics portion (before "## Style Notes")
lyrics_section = content.split("## Style Notes")[0].strip()

# Clean up the markdown formatting
lyrics = lyrics_section.replace("# \"Black Ocean\" - Original Song", "").strip()

print("=" * 60)
print("BLACK OCEAN - Music Generation")
print("=" * 60)
print("\n📝 Lyrics loaded:\n")
print(lyrics[:500])
print("...[truncated for display]...")
print("\n" + "=" * 60)

# API setup
url = "https://api.minimax.io/v1/music_generation"
api_key = os.environ.get("MINIMAX_API_KEY")
if not api_key:
    # Try loading from .zshrc
    import subprocess
    result = subprocess.run(['source', '/Users/danieltekippe/.zshrc'], shell=True)
    api_key = os.environ.get("MINIMAX_API_KEY")

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

# Music prompt - The National inspired style
music_prompt = """Moody indie rock anthem, deep baritone vocals, atmospheric guitars, 
cinematic build, The National-inspired, existential, crescendo refrains, 
cosmic loneliness, slow tempo, melancholic, spoken-word verses, 
building to cathartic choruses, cinematic, reverb-heavy guitars"""

payload = {
    "model": "music-2.5+",
    "prompt": music_prompt,
    "lyrics": lyrics,
    "audio_setting": {
        "sample_rate": 44100,
        "bitrate": 256000,
        "format": "mp3"
    },
    "output_format": "url"
}

print("\n🎵 Generating music...")
print(f"   Model: music-2.5+")
print(f"   Style: {music_prompt[:80]}...")

# Step 1: Create generation task
response = requests.post(url, headers=headers, json=payload)
print(f"\n📨 API Response: {response.status_code}")

if response.status_code != 200:
    print(f"❌ Error: {response.text}")
    exit(1)

result = response.json()
print(f"\n📋 Full response: {json.dumps(result, ensure_ascii=False, indent=2)}")

task_id = result.get("task_id")
if not task_id:
    print("❌ No task_id in response")
    exit(1)

print(f"\n🔑 Task ID: {task_id}")
print("\n⏳ Polling for completion (may take 1-2 minutes)...")

# Step 2: Poll for completion
status_url = f"https://api.minimax.io/v1/query/music_generation"

max_attempts = 120  # 2 minutes max
for attempt in range(max_attempts):
    time.sleep(1)
    status_response = requests.get(
        status_url,
        headers=headers,
        params={"task_id": task_id}
    )
    
    if status_response.status_code != 200:
        print(f"   Attempt {attempt+1}: Status check failed")
        continue
        
    status_result = status_response.json()
    status = status_result.get("status", "unknown")
    
    print(f"   Attempt {attempt+1}: {status}")
    
    if status == "success":
        # Get the audio URL
        audio_url = status_result.get("data", {}).get("audio_url")
        if audio_url:
            print(f"\n✅ SUCCESS! Audio URL: {audio_url}")
            print(f"\n📥 Download the audio:")
            print(f"   curl -o black_ocean.mp3 '{audio_url}'")
            
            # Save to file
            audio_response = requests.get(audio_url)
            with open("/Users/danieltekippe/.openclaw/workspace/black_ocean.mp3", "wb") as f:
                f.write(audio_response.content)
            print(f"\n💾 Saved to: /Users/danieltekippe/.openclaw/workspace/black_ocean.mp3")
            
            # Also save metadata
            with open("/Users/danieltekippe/.openclaw/workspace/black_ocean_info.txt", "w") as f:
                f.write(f"Black Ocean - Original Song\n")
                f.write(f"Task ID: {task_id}\n")
                f.write(f"Audio URL: {audio_url}\n")
                f.write(f"Style: The National-inspired indie rock\n")
                f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            print(f"💾 Metadata saved to: black_ocean_info.txt")
        else:
            print(f"\n⚠️ Success but no audio_url found")
            print(f"   Full result: {json.dumps(status_result, ensure_ascii=False, indent=2)}")
        break
        
    elif status == "fail":
        print(f"\n❌ Generation failed: {status_result}")
        break

else:
    print("\n⏰ Timeout - no response after 2 minutes")
    print("   The song may still be generating. Check the MiniMax console.")
