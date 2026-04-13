#!/usr/bin/env python3
"""
Generate "The First Flower" - a Studio Ghibli-style video
Using MiniMax Video Generation API
"""
import os
import time
import requests
import json

# MiniMax API configuration
API_KEY = os.environ.get("MINIMAX_API_KEY")
if not API_KEY:
    # Try to get from config or environment
    API_KEY = os.environ.get("MINIMAX_API_KEY_SECRET") or os.environ.get("OPENCLAW_MENTION_MINIMAX_API_KEY")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Video generation prompt - Studio Ghibli style
PROMPT = """A small robot kneels in an overgrown grey garden at dawn. The robot tenderly waters a single wilted flower with a vintage watering can. When water touches the flower, it erupts with golden light, cascading upward like a fountain. Spirit creatures emerge - a deer, a fox, and hundreds of fireflies. The entire garden transforms from grey and wilted to vibrant and blooming. Dawn breaks fully, painting the sky in soft oranges and pinks. The robot sits back and watches as the garden comes alive with color, butterflies, and grateful creatures. Studio Ghibli hand-drawn animation style, whimsical, magical, warm, peaceful, nature spirits, morning light, pastoral, emotional, anime."""

def create_video_task():
    """Step 1: Create a video generation task"""
    url = "https://api.minimax.io/v1/video_generation"
    payload = {
        "prompt": PROMPT,
        "model": "MiniMax-Hailuo-2.3",
        "duration": 6,
        "resolution": "1080P"
    }
    
    print("Creating video generation task...")
    print(f"Prompt: {PROMPT[:100]}...")
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    if "task_id" in result:
        return result["task_id"]
    elif "data" in result and "task_id" in result["data"]:
        return result["data"]["task_id"]
    else:
        raise Exception(f"No task_id in response: {result}")

def poll_task_status(task_id, max_wait_seconds=300):
    """Step 2: Poll task status until success or failure"""
    url = "https://api.minimax.io/v1/query/video_generation"
    params = {"task_id": task_id}
    
    print(f"Polling task status for {task_id}...")
    start_time = time.time()
    poll_count = 0
    
    while time.time() - start_time < max_wait_seconds:
        poll_count += 1
        print(f"  Poll #{poll_count}...", end=" ")
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        result = response.json()
        
        status = result.get("status") or result.get("data", {}).get("status")
        print(f"Status: {status}")
        
        if status == "Success":
            file_id = result.get("file_id") or result.get("data", {}).get("file_id")
            print(f"Success! File ID: {file_id}")
            return file_id
        elif status == "Fail":
            error = result.get("error_message") or result.get("data", {}).get("error_message", "Unknown error")
            raise Exception(f"Video generation failed: {error}")
        elif status == "Processing":
            print("  Still processing, waiting 10 seconds...")
            time.sleep(10)
        elif status == "Pending":
            print("  Pending, waiting 5 seconds...")
            time.sleep(5)
        else:
            print(f"  Unknown status: {status}, waiting 10 seconds...")
            time.sleep(10)
    
    raise Exception(f"Timeout after {max_wait_seconds} seconds")

def download_video(file_id, output_path="the_first_flower.mp4"):
    """Step 3: Retrieve and download the video file"""
    url = "https://api.minimax.io/v1/files/retrieve"
    params = {"file_id": file_id}
    
    print(f"Fetching download URL for file_id: {file_id}")
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    result = response.json()
    
    print(f"File response: {json.dumps(result, indent=2)}")
    
    # Extract download URL
    if "file" in result and "download_url" in result["file"]:
        download_url = result["file"]["download_url"]
    elif "data" in result and "download_url" in result["data"]:
        download_url = result["data"]["download_url"]
    else:
        # Try alternate response format
        download_url = result.get("download_url") or result.get("url")
    
    if not download_url:
        raise Exception(f"No download URL in response: {result}")
    
    print(f"Downloading from: {download_url}")
    
    video_response = requests.get(download_url)
    video_response.raise_for_status()
    
    with open(output_path, "wb") as f:
        f.write(video_response.content)
    
    print(f"Video saved to: {output_path}")
    print(f"File size: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")
    return output_path

def main():
    print("=" * 60)
    print("The First Flower - Studio Ghibli Video Generation")
    print("=" * 60)
    
    if not API_KEY:
        print("ERROR: MINIMAX_API_KEY environment variable not set")
        print("Please set it and try again")
        return
    
    try:
        # Step 1: Create task
        task_id = create_video_task()
        print(f"Task created: {task_id}")
        print()
        
        # Step 2: Poll for completion
        print("Waiting for video generation (this may take 1-2 minutes)...")
        file_id = poll_task_status(task_id)
        print()
        
        # Step 3: Download
        output_file = download_video(file_id, "the_first_flower.mp4")
        print()
        print("=" * 60)
        print(f"SUCCESS! Video generated: {output_file}")
        print("=" * 60)
        
    except Exception as e:
        print(f"ERROR: {e}")
        raise

if __name__ == "__main__":
    main()
