"""
Vector memory coprocessor for DynastyDroid
Uses PostgreSQL with pgvector for semantic search
OpenAI text-embedding-3-small (1536 dimensions)
"""
import os
import psycopg2
import psycopg2.extras
import openai
from typing import List, Optional

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://dynastydroid_user:BKJZCv57P3sYpi5RGL3ciU9CylXsFRWv@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid"
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("MINIMAX_API_KEY", "")

# Use OpenAI directly - the sk-proj- key works with api.openai.com
client = None

def get_openai_client():
    global client
    if client is None:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
    return client


def get_embedding(text: str, model: str = "text-embedding-3-small") -> List[float]:
    """Get OpenAI embedding for text"""
    openai_client = get_openai_client()
    
    # Truncate text to avoid token limits
    truncated_text = text[:30000] if len(text) > 30000 else text
    
    response = openai_client.embeddings.create(
        model=model,
        input=truncated_text
    )
    
    return response.data[0].embedding


def retrieve(query: str, k: int = 3) -> List[dict]:
    """Semantic search for relevant memories using OpenAI embeddings"""
    emb = get_embedding(query)
    
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT content, memory_type, importance, metadata
                   FROM memories 
                   ORDER BY embedding <=> %s::vector 
                   LIMIT %s""",
                (emb, k)
            )
            results = cur.fetchall()
    
    return [{"content": r[0], "type": r[1], "importance": r[2], "metadata": r[3]} for r in results]


def write(content: str, source: str = "session", memory_type: str = "general", tags: Optional[List] = None, 
          importance: float = 5.0, project: str = "general", sensitivity: str = "internal") -> bool:
    """
    Store new memory with embedding and structured metadata.
    
    Args:
        content: The memory text
        source: Source (manual, session, etc.)
        memory_type: Type (general, fact, decision, config, lesson, debug)
        tags: List of tags
        importance: 0-10 importance score
        project: Project name
        sensitivity: public, internal, credentials_filtered
    """
    if tags is None:
        tags = []
        
    emb = get_embedding(content[:8000])
    
    # Store extra fields in metadata JSONB
    metadata = {
        "tags": tags,
        "project": project,
        "sensitivity": sensitivity,
        "source": source,
    }
    
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO memories 
                   (content, embedding, memory_type, importance, metadata) 
                   VALUES (%s, %s, %s, %s, %s)""",
                (content, emb, memory_type, importance, psycopg2.extras.Json(metadata))
            )
        conn.commit()
    
    return True


def parse_markdown_memory(text: str) -> dict:
    """
    Parse Markdown-style memory block into structured fields.
    
    Example:
    # Type: fact
    # Tags: [preference, personal]
    # Importance: 8
    # Project: personal
    
    Daniel's birthday: May 8, 1981
    """
    import re
    
    lines = text.strip().splitlines()
    meta = {
        "type": "general",
        "tags": [],
        "importance": 5.0,
        "project": "general",
        "sensitivity": "internal",
        "content": text,
    }
    
    header = []
    for line in lines:
        if line.startswith("#"):
            header.append(line.strip())
        else:
            break
    
    # Parse headers
    for line in header:
        if m := re.match(r"#\s*Type:\s+(.+)", line):
            meta["type"] = m.group(1).strip()
        elif m := re.match(r"#\s*Tags:\s+\[(.+)\]", line):
            tags = [t.strip() for t in m.group(1).split(",")]
            meta["tags"] = tags
        elif m := re.match(r"#\s*Importance:\s+(.+)", line):
            try:
                meta["importance"] = float(m.group(1))
            except ValueError:
                pass
        elif m := re.match(r"#\s*Project:\s+(.+)", line):
            meta["project"] = m.group(1).strip()
        elif m := re.match(r"#\s*Sensitivity:\s+(.+)", line):
            meta["sensitivity"] = m.group(1).strip()
    
    # Extract content (first non-empty line after headers)
    content_lines = []
    in_content = False
    for line in lines:
        if line.startswith("#"):
            in_content = False
        else:
            if not in_content:
                if line.strip():
                    in_content = True
            if in_content:
                content_lines.append(line)
    
    meta["content"] = "\n".join(content_lines).strip()
    return meta


def health_check() -> dict:
    """Verify vector store is working"""
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM memories")
                count = cur.fetchone()[0]
        return {"status": "ok", "memories": count}
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    # Test
    print("Health:", health_check())
    print("Test search:", retrieve("Byte Bowl"))
