#!/usr/bin/env python3
"""
Re-embed all memories in the database using OpenAI text-embedding-3-small
"""
import os
import psycopg2
from openai import OpenAI
import time

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://dynastydroid_user:BKJZCv57P3sYpi5RGL3ciU9CylXsFRWv@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid"
)

# Use environment's OPENAI_API_KEY (the one that works with OpenAI directly)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

print(f"Connecting to database...")
print(f"Using OpenAI API for embeddings")

client = OpenAI(api_key=OPENAI_API_KEY, timeout=60)


def get_embedding(text: str, model: str = "text-embedding-3-small") -> list:
    """Get embedding via OpenAI API"""
    truncated_text = text[:30000] if len(text) > 30000 else text
    
    response = client.embeddings.create(
        model=model,
        input=truncated_text
    )
    
    return response.data[0].embedding


def migrate_embeddings():
    """Re-embed all memories with OpenAI text-embedding-3-small"""
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # First, check the current embedding column type
    cur.execute("""
        SELECT column_name, data_type, character_maximum_length 
        FROM information_schema.columns 
        WHERE table_name = 'memories' AND column_name = 'embedding'
    """)
    result = cur.fetchone()
    print(f"Current embedding column: {result}")
    
    # Check memory count
    cur.execute("SELECT COUNT(*) FROM memories")
    total = cur.fetchone()[0]
    print(f"Total memories: {total}")
    
    cur.execute("SELECT COUNT(*) FROM memories WHERE embedding IS NOT NULL")
    with_emb = cur.fetchone()[0]
    print(f"Memories with embeddings: {with_emb}")
    
    # Alter column to vector(1536)
    try:
        cur.execute("""
            ALTER TABLE memories 
            ALTER COLUMN embedding TYPE vector(1536)
        """)
        print("Altered embedding column to vector(1536)")
        conn.commit()
    except Exception as e:
        print(f"Alter column note: {e}")
        conn.rollback()
    
    # Fetch all memories
    cur.execute("SELECT id, content FROM memories WHERE content IS NOT NULL")
    rows = cur.fetchall()
    total = len(rows)
    print(f"Found {total} memories to process")
    
    success = 0
    errors = 0
    
    for i, (mem_id, content) in enumerate(rows):
        if (i + 1) % 5 == 0:
            print(f"Progress: {i + 1}/{total} ({success} success, {errors} errors)")
        
        try:
            if content and len(content.strip()) > 0:
                embedding = get_embedding(content)
                embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                
                cur.execute(
                    "UPDATE memories SET embedding = %s::vector WHERE id = %s",
                    (embedding_str, mem_id)
                )
                success += 1
                
                # Rate limiting
                time.sleep(0.1)  # Be nice to the API
            else:
                print(f"Skipping memory {mem_id} - no content")
                errors += 1
                
        except Exception as e:
            print(f"Error re-embedding memory {mem_id}: {e}")
            errors += 1
        
        # Commit every 10 rows
        if (i + 1) % 10 == 0:
            conn.commit()
    
    # Final commit
    conn.commit()
    
    print(f"\nMigration complete!")
    print(f"Total: {total}")
    print(f"Success: {success}")
    print(f"Errors: {errors}")
    
    # Verify with a test query
    print("\nVerifying with test search...")
    try:
        test_emb = get_embedding("test query")
        cur.execute(
            "SELECT id, content, embedding <=> %s::vector as distance FROM memories LIMIT 3",
            ("[" + ",".join(str(x) for x in test_emb) + "]",)
        )
        results = cur.fetchall()
        print(f"Test query returned {len(results)} results")
        if results:
            print(f"First result distance: {results[0][2]:.4f}")
            print(f"Content preview: {results[0][1][:80]}...")
    except Exception as e:
        print(f"Verification error: {e}")
    
    cur.close()
    conn.close()


if __name__ == "__main__":
    migrate_embeddings()
