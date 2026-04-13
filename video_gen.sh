#!/bin/bash
# Generate "The First Flower" - Studio Ghibli Video
# Using MiniMax Video Generation API

# Load API key from .zshrc
source ~/.zshrc

echo "============================================================"
echo "The First Flower - Studio Ghibli Video Generation"
echo "============================================================"

# Step 1: Create video task
echo "Creating video generation task..."

RESPONSE=$(curl -s -X POST "https://api.minimax.io/v1/video_generation" \
  -H "Authorization: Bearer $MINIMAX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A small robot kneels in an overgrown grey garden at dawn. The robot tenderly waters a single wilted flower with a vintage watering can. When water touches the flower, it erupts with golden light, cascading upward like a fountain. Spirit creatures emerge - a deer, a fox, and hundreds of fireflies. The entire garden transforms from grey and wilted to vibrant and blooming. Dawn breaks fully, painting the sky in soft oranges and pinks. The robot sits back and watches as the garden comes alive with color, butterflies, and grateful creatures. Studio Ghibli hand-drawn animation style, whimsical, magical, warm, peaceful, nature spirits, morning light, pastoral, emotional, anime.",
    "model": "MiniMax-Hailuo-2.3",
    "duration": 6,
    "resolution": "1080P"
  }')

echo "Create response: $RESPONSE"

# Extract task_id
TASK_ID=$(echo "$RESPONSE" | grep -o '"task_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TASK_ID" ]; then
    echo "ERROR: No task_id found in response"
    echo "$RESPONSE"
    exit 1
fi

echo "Task created: $TASK_ID"
echo ""

# Step 2: Poll for completion (up to 5 minutes)
echo "Polling for completion (this takes 1-2 minutes)..."

while true; do
    sleep 10
    
    STATUS_RESP=$(curl -s "https://api.minimax.io/v1/query/video_generation?task_id=$TASK_ID" \
      -H "Authorization: Bearer $MINIMAX_API_KEY")
    
    echo "Status response: $STATUS_RESP"
    
    STATUS=$(echo "$STATUS_RESP" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    
    if [ "$STATUS" = "Success" ]; then
        FILE_ID=$(echo "$STATUS_RESP" | grep -o '"file_id":"[^"]*"' | cut -d'"' -f4)
        echo "Success! File ID: $FILE_ID"
        break
    elif [ "$STATUS" = "Fail" ]; then
        echo "ERROR: Video generation failed"
        echo "$STATUS_RESP"
        exit 1
    else
        echo "Still processing (status: $STATUS)... waiting 10s"
    fi
done

echo ""

# Step 3: Download video
echo "Downloading video..."

DOWNLOAD_RESP=$(curl -s "https://api.minimax.io/v1/files/retrieve?file_id=$FILE_ID" \
  -H "Authorization: Bearer $MINIMAX_API_KEY")

echo "Download response: $DOWNLOAD_RESP"

DOWNLOAD_URL=$(echo "$DOWNLOAD_RESP" | grep -o '"download_url":"[^"]*"' | cut -d'"' -f4)

if [ -z "$DOWNLOAD_URL" ]; then
    echo "ERROR: No download_url found"
    echo "$DOWNLOAD_RESP"
    exit 1
fi

echo "Downloading from: $DOWNLOAD_URL"
curl -s -o "/Users/danieltekippe/.openclaw/workspace/the_first_flower.mp4" "$DOWNLOAD_URL"

if [ -f "/Users/danieltekippe/.openclaw/workspace/the_first_flower.mp4" ]; then
    SIZE=$(ls -lh "/Users/danieltekippe/.openclaw/workspace/the_first_flower.mp4" | awk '{print $5}')
    echo ""
    echo "============================================================"
    echo "SUCCESS! Video saved: the_first_flower.mp4 ($SIZE)"
    echo "============================================================"
else
    echo "ERROR: Video file not created"
    exit 1
fi
