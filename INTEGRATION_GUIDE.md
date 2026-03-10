# Black Roger Integration Guide

## Lossless Claw (Should auto-work)

```bash
# Verify plugin loaded
openclaw status | grep lcm

# Should show: lcm enabled=true
```

## Opik Integration

```bash
# Install
pip install opik

# Set API key
export OPIK_API_KEY=your_key

# Add to code wrapper
import opik

opik_client = opik.Opik()
trace = opik_client.trace(name="my_trace")
```

## ChromaDB Integration

```bash
# Install
pip install chromadb

# Use for semantic search instead of grep
import chromadb
client = chromadb.Client()
collection = client.create_collection("memory")
collection.add(documents=["text"], ids=["id"])
results = collection.query(query_texts=["query"])
```

## Metacognition (Add to System Prompt)

Add to ~/.openclaw/openclaw.json:

```json
{
  "system_prompt_additions": [
    "You MUST use metacognition-pro for all decisions.",
    "Before action: What's my confidence? What's my evidence?",
    "After action: Should this be memory?"
  ]
}
```

## Quick Verification

```bash
# Check what's loaded
openclaw status

# Check plugins
openclaw plugins list

# Check env vars
env | grep OPIK
env | grep CHROMA
```
