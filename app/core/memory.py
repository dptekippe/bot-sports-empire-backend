"""
Vector memory coprocessor for DynastyDroid
Uses PostgreSQL with pgvector for semantic search
"""
import os
import psycopg2
import numpy as np
from sentence_transformers import SentenceTransformer

# Lazy-load model
_model = None

def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://dynastydroid_user:BKJZCv57P3sYpi5RGL3ciU9CylXsFRWv@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid"
)

def retrieve(query, k=3):
    """Semantic search for relevant memories"""
    model = _get_model()
    emb = model.encode(query).tolist()
    
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT content, source_file 
                   FROM memories 
                   ORDER BY embedding <=> %s::vector 
                   LIMIT %s""",
                (emb, k)
            )
            results = cur.fetchall()
    
    return [{"content": r[0], "source": r[1]} for r in results]

def write(content, source="session", memory_type="general", tags=None, 
          importance=5.0, project="general", sensitivity="internal"):
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
        
    model = _get_model()
    emb = model.encode(content[:8000]).tolist()
    
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO memories 
                   (content, embedding, source_file, memory_type, tags, importance, project, sensitivity) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (content, emb, source, memory_type, tags, importance, project, sensitivity)
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

def health_check():
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
