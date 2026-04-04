#!/usr/bin/env python3
"""
MEMORY.md File Watcher
Monitors MEMORY.md for changes and automatically vectorizes new entries to pgvector.

Usage: python3 memory_watcher.py [--daemon]

FIXES APPLIED (2026-04-04):
- Added certifi for SSL certificate handling
- Removed hardcoded API key fallback (security fix)
- Added watchdog import with graceful fallback
"""

import os
import sys
import time
import json
import hashlib
import argparse
from datetime import datetime
from pathlib import Path

# SSL Certificate handling - fix for SSL CERTIFICATE_VERIFY_FAILED
import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['SSL_CERT_DIR'] = '/etc/ssl/certs'

# Database connection - require environment variable
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is required. "
        "Set it to your PostgreSQL connection string."
    )

MEMORY_FILE = "/Users/danieltekippe/.openclaw/workspace/MEMORY.md"
STATE_FILE = "/Users/danieltekippe/.openclaw/workspace/.memory_watcher_state.json"
LOG_FILE = "/Volumes/ExternalCorsairSSD/shared/logs/memory-watcher.log"

def log(msg):
    """Log to both console and file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except:
        pass

def get_state():
    """Load the last known state."""
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {"last_hash": None, "last_position": 0}

def save_state(state):
    """Save the current state."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def compute_hash(content):
    """Compute a simple hash of the file content."""
    return hashlib.md5(content.encode()).hexdigest()

def get_file_content():
    """Read MEMORY.md content."""
    try:
        with open(MEMORY_FILE, "r") as f:
            return f.read()
    except Exception as e:
        log(f"Error reading MEMORY.md: {e}")
        return None

def parse_new_entries(old_content, new_content):
    """
    Extract new entries added to MEMORY.md.
    Entries start with '## [' and contain the category/title.
    """
    if not old_content:
        return []
    
    new_entries = []
    old_lines = old_content.split("\n")
    new_lines = new_content.split("\n")
    
    # Find where new content starts
    if len(new_lines) <= len(old_lines):
        return []  # No new content added
    
    # Find the first new line
    new_start = len(old_lines)
    
    # Collect new lines until we hit another '## [' or end
    entry_lines = new_lines[new_start:]
    
    # Also need to include the header line that might have been split
    # Check if old content ended mid-entry
    entry_text = "\n".join(entry_lines)
    
    # If we have substantial new content, parse entries from it
    if len(entry_text.strip()) > 50:
        # Split by entry markers
        import re
        entries = re.split(r'\n(?=## \[)', entry_text)
        for entry in entries:
            if entry.strip() and len(entry.strip()) > 50:
                new_entries.append(entry.strip())
    
    return new_entries

def embed_text(text, model="text-embedding-3-small"):
    """
    Generate embedding using OpenAI SDK.
    FIX: Removed hardcoded API key fallback - must use environment variable.
    """
    import os
    from openai import OpenAI
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        log("ERROR: OPENAI_API_KEY environment variable not set")
        return None
    
    try:
        client = OpenAI(api_key=api_key)
        response = client.embeddings.create(
            model=model,
            input=text[:8000]
        )
        return response.data[0].embedding
    except Exception as e:
        log(f"Embedding failed: {str(e)[:100]}")
        return None

def store_memory(content, embedding):
    """Store memory entry in pgvector."""
    import psycopg2
    import numpy as np
    
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    # Insert the memory
    cur.execute("""
        INSERT INTO memories (content, embedding, created_at, importance, domain, tags)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        content,
        embedding,
        datetime.now(),
        1.0,  # Default importance
        'episodic',  # Default domain
        ['memory-watcher']  # Tag for tracking
    ))
    
    memory_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    
    return memory_id

def process_file_change():
    """Process MEMORY.md changes and vectorize new entries."""
    state = get_state()
    content = get_file_content()
    
    if content is None:
        return
    
    new_hash = compute_hash(content)
    
    # Check if file actually changed
    if new_hash == state["last_hash"]:
        return
    
    old_content = state.get("last_content", "")
    new_entries = parse_new_entries(old_content, content)
    
    if not new_entries:
        log("New content detected but no new entries found")
    
    for i, entry in enumerate(new_entries):
        log(f"New entry detected ({i+1}/{len(new_entries)}), generating embedding...")
        
        embedding = embed_text(entry)
        if embedding:
            memory_id = store_memory(entry, embedding)
            log(f"Stored memory entry: {memory_id}")
        else:
            log("Failed to generate embedding, skipping entry")
    
    # Update state
    state["last_hash"] = new_hash
    state["last_content"] = content
    state["last_processed"] = datetime.now().isoformat()
    save_state(state)

def watch_file():
    """Watch MEMORY.md for changes using polling (simple approach)."""
    log("Starting MEMORY.md file watcher (polling mode)")
    log(f"Watching: {MEMORY_FILE}")
    
    # Initialize state on startup
    content = get_file_content()
    if content:
        state = get_state()
        state["last_hash"] = compute_hash(content)
        state["last_content"] = content
        save_state(state)
        log(f"Initialized with {len(content)} chars, hash: {state['last_hash']}")
    
    while True:
        time.sleep(5)  # Poll every 5 seconds
        try:
            process_file_change()
        except Exception as e:
            log(f"Error processing file change: {e}")

def use_watchdog():
    """Use watchdog library for event-driven monitoring."""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        
        class MemoryHandler(FileSystemEventHandler):
            def __init__(self):
                self.last_modified = time.time()
            
            def on_modified(self, event):
                if event.src_path == MEMORY_FILE:
                    # Debounce - ignore if within 1 second
                    if time.time() - self.last_modified < 1:
                        return
                    self.last_modified = time.time()
                    log(f"File modified: {event.src_path}")
                    time.sleep(0.5)  # Wait for file to finish writing
                    process_file_change()
        
        event_handler = MemoryHandler()
        observer = Observer()
        observer.schedule(event_handler, path=os.path.dirname(MEMORY_FILE), recursive=False)
        observer.start()
        
        log("Watchdog observer started")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        
        observer.join()
        
    except ImportError:
        log("watchdog not installed, falling back to polling mode")
        watch_file()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MEMORY.md File Watcher")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    args = parser.parse_args()
    
    log("=" * 50)
    log("MEMORY.md File Watcher Started")
    log("=" * 50)
    
    try:
        use_watchdog()
    except KeyboardInterrupt:
        log("Watcher stopped")
