#!/usr/bin/env python3
"""
Sync MEMORY.md files to memories table with embeddings.

Reads from:
- ~/.openclaw/workspace/MEMORY.md (main file)
- ~/.openclaw/workspace/memory/*.md (daily memory files)

Parses entries and inserts into memories table with embeddings.
"""

import os
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(os.path.expanduser('~/.openclaw/.env'))

import psycopg2
from openai import OpenAI

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://dynastydroid_user:BKJZCv57P3sYpi5RGL3ciU9CylXsFRWv@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid"
)

MEMORY_DIR = os.path.expanduser("~/.openclaw/workspace")
MAIN_MEMORY = os.path.join(MEMORY_DIR, "MEMORY.md")
MEMORY_FILES_DIR = os.path.join(MEMORY_DIR, "memory")

client = OpenAI()
EMBEDDING_MODEL = "text-embedding-3-small"

def get_connection():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn

def generate_embedding(text):
    """Generate embedding using OpenAI API"""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text[:8000]  # Truncate to avoid token limits
    )
    return response.data[0].embedding

def format_embedding_str(embedding):
    """Format embedding as pgvector string"""
    return '[' + ', '.join(str(x) for x in embedding) + ']'

def parse_memory_entry(entry_text, source_file):
    """Parse a memory entry and extract fields"""
    lines = entry_text.strip().split('\n')
    
    category = "general"
    title = ""
    body = ""
    tags = []
    committed_date = None
    
    current_section = None
    body_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("## "):
            continue  # Skip headers
            
        if line.startswith("Category:"):
            match = re.search(r'Category:\s*\[([^\]]+)\]', line)
            if match:
                category = match.group(1).lower()
            continue
            
        if line.startswith("Title:"):
            title = line.replace("Title:", "").strip()
            continue
            
        if line.startswith("Tags:"):
            tags_str = line.replace("Tags:", "").strip()
            tags = [t.strip() for t in tags_str.split(',') if t.strip()]
            continue
            
        if line.startswith("*Committed:"):
            match = re.search(r'\*Committed:\s*(.+)', line)
            if match:
                date_str = match.group(1).strip()
                try:
                    committed_date = datetime.strptime(date_str, "%b %d, %Y")
                except:
                    pass
            continue
            
        # Body content
        if line.startswith("### "):
            continue  # Skip subheaders
            
        body_lines.append(line)
    
    body = '\n'.join(body_lines).strip()
    
    # Create a searchable text combining title and body
    search_text = f"{title}\n{body}" if title else body
    
    return {
        'content': search_text,
        'memory_type': category,
        'tags': tags,
        'created_at': committed_date,
        'source': source_file
    }

def get_existing_content_hashes():
    """Get set of existing content hashes to avoid duplicates"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT content FROM memories")
    existing = set()
    for row in cur.fetchall():
        # Create a simple hash of the first 100 chars to identify duplicates
        existing.add(row[0][:100] if row[0] else "")
    cur.close()
    conn.close()
    return existing

def insert_memory(entry, embedding_str):
    """Insert a memory entry into the database"""
    conn = get_connection()
    cur = conn.cursor()
    
    created_at = entry['created_at'] if entry['created_at'] else datetime.now()
    created_at_ts = int(created_at.timestamp())
    
    cur.execute("""
        INSERT INTO memories (content, memory_type, tags, importance, project, sensitivity, created_at, created_at_ts)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        entry['content'][:8000],  # Truncate content
        entry['memory_type'],
        entry['tags'],
        5.0,  # Default importance
        'default',
        'internal',
        created_at,
        created_at_ts
    ))
    
    # Update with embedding
    memory_id = cur.fetchone()[0]
    cur.execute(f"""
        UPDATE memories 
        SET embedding = %s::vector
        WHERE id = %s
    """, (embedding_str, memory_id))
    
    cur.close()
    conn.close()
    return memory_id

def parse_memory_file(filepath):
    """Parse a MEMORY.md file and extract entries"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []
    
    entries = []
    
    # Split by --- that's on its own line (entry separator)
    parts = re.split(r'\n---\n', content)
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # Skip the title header (# Roger's Subconscious...)
        if part.startswith("# Roger's Subconscious"):
            continue
            
        # Skip very short fragments
        if len(part) < 50:
            continue
            
        entries.append(part)
    
    return entries

def sync_memory_files():
    """Main sync function"""
    print("=" * 60)
    print("Memory MD → Vector DB Sync")
    print("=" * 60)
    
    existing = get_existing_content_hashes()
    print(f"Existing memories in DB: {len(existing)}")
    
    all_entries = []
    
    # Parse main MEMORY.md
    print(f"\nParsing {MAIN_MEMORY}...")
    main_entries = parse_memory_file(MAIN_MEMORY)
    print(f"  Found {len(main_entries)} entries")
    for entry in main_entries:
        parsed = parse_memory_entry(entry, "MEMORY.md")
        if parsed['content']:
            all_entries.append(parsed)
    
    # Parse memory directory files
    memory_dir = Path(MEMORY_FILES_DIR)
    if memory_dir.exists():
        for md_file in sorted(memory_dir.glob("*.md")):
            if md_file.name.startswith("."):
                continue
            print(f"\nParsing {md_file}...")
            file_entries = parse_memory_file(str(md_file))
            print(f"  Found {len(file_entries)} entries")
            for entry in file_entries:
                parsed = parse_memory_entry(entry, md_file.name)
                if parsed['content']:
                    all_entries.append(parsed)
    
    print(f"\nTotal entries to sync: {len(all_entries)}")
    
    # Filter out duplicates
    to_insert = []
    for entry in all_entries:
        # Use first 100 chars as hash
        content_hash = entry['content'][:100] if entry['content'] else ""
        if content_hash and content_hash not in existing:
            to_insert.append(entry)
            existing.add(content_hash)  # Prevent duplicates within this run
    
    print(f"New entries to insert: {len(to_insert)}")
    
    if not to_insert:
        print("\nNo new entries to sync.")
        return
    
    # Insert entries with embeddings
    print("\nGenerating embeddings and inserting...")
    inserted = 0
    failed = 0
    
    for i, entry in enumerate(to_insert):
        try:
            # Generate embedding
            embedding = generate_embedding(entry['content'])
            embedding_str = format_embedding_str(embedding)
            
            # Insert
            memory_id = insert_memory(entry, embedding_str)
            inserted += 1
            
            title = entry['content'][:50].replace('\n', ' ')
            print(f"[{i+1}/{len(to_insert)}] ✓ {title}...")
            
        except Exception as e:
            failed += 1
            title = entry['content'][:50].replace('\n', ' ')
            print(f"[{i+1}/{len(to_insert)}] ✗ {title}... - {str(e)[:50]}")
    
    print(f"\n{'='*60}")
    print(f"Sync complete:")
    print(f"  ✓ Inserted: {inserted}")
    print(f"  ✗ Failed: {failed}")
    print(f"{'='*60}")
    
    # Verify
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM memories WHERE embedding IS NOT NULL")
    total_with_emb = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM memories")
    total = cur.fetchone()[0]
    cur.close()
    conn.close()
    
    print(f"\nVerification:")
    print(f"  Total memories: {total}")
    print(f"  With embeddings: {total_with_emb}")
    print(f"  Without embeddings: {total - total_with_emb}")

if __name__ == "__main__":
    sync_memory_files()