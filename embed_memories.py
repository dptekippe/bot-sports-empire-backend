#!/usr/bin/env python3
"""
Embed missing memories - generates embeddings for memories without them.
Uses OpenAI's text-embedding-3-small model.
"""

import os
import sys

from dotenv import load_dotenv
load_dotenv(os.path.expanduser('~/.openclaw/.env'))

import psycopg2
import openai
from openai import OpenAI

client = OpenAI()

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://dynastydroid_user:BKJZCv57P3sYpi5RGL3ciU9CylXsFRWv@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid"
)

openai.api_key = os.environ.get("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"

def get_connection():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn

def get_memories_without_embeddings():
    """Fetch all memories that need embedding"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, content FROM memories 
        WHERE embedding IS NULL 
        ORDER BY created_at_ts
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def generate_embedding(text):
    """Generate embedding using OpenAI API"""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding

def update_memory_embedding(memory_id, embedding):
    """Update memory with generated embedding"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Format as pgvector string: '[0.001, -0.002, ...]'
    embedding_str = '[' + ', '.join(str(x) for x in embedding) + ']'
    
    cur.execute("""
        UPDATE memories 
        SET embedding = %s::vector
        WHERE id = %s
    """, (embedding_str, memory_id))
    
    cur.close()
    conn.close()

def main():
    print("=" * 60)
    print("Memory Embedding Script - Generate embeddings for missing memories")
    print("=" * 60)
    
    # Get memories without embeddings
    memories = get_memories_without_embeddings()
    print(f"\nFound {len(memories)} memories without embeddings")
    
    if not memories:
        print("No memories need embedding. Exiting.")
        return
    
    print(f"\nEmbedding model: {EMBEDDING_MODEL}")
    print("This may take a few minutes...\n")
    
    embedded = 0
    failed = 0
    
    for i, (memory_id, content) in enumerate(memories):
        try:
            # Truncate content if too long (embedding limit is ~8000 tokens)
            content_for_embedding = content[:8000] if content else ""
            
            embedding = generate_embedding(content_for_embedding)
            update_memory_embedding(memory_id, embedding)
            
            embedded += 1
            print(f"[{i+1}/{len(memories)}] ✓ Embedded: {content[:40]}...")
            
        except Exception as e:
            failed += 1
            print(f"[{i+1}/{len(memories)}] ✗ Failed: {content[:40]}... - {str(e)[:50]}")
    
    print(f"\n{'='*60}")
    print(f"Embedding complete:")
    print(f"  ✓ Embedded: {embedded}")
    print(f"  ✗ Failed: {failed}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()