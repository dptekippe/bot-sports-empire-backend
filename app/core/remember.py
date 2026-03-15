"""
Filtered Session Memory Capture
Supports structured memory with tags, importance, type
"""

import re
import json
import time
import sys
sys.path.insert(0, '/Users/danieltekippe/.openclaw/workspace')

from app.core.memory import write as vector_write, parse_markdown_memory

# Sensitive patterns to filter
SENSITIVE_PATTERNS = [
    r'api[_-]?key["\']?\s*[:=]\s*["\']?[\w-]+',
    r'sk-[a-zA-Z0-9]+',
    r'password["\']?\s*[:=]\s*["\']?[^\s"\'>]+',
    r'token["\']?\s*[:=]\s*["\']?[\w-]+',
    r'Bearer\s+[\w-]+',
]

def sanitize(content: str) -> str:
    """Remove sensitive data from content"""
    sanitized = content
    for pattern in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)
    return sanitized


def parse_memory_input(text: str) -> dict:
    """
    Parse memory input - supports JSON or Markdown hinting.
    
    Examples:
    
    JSON:
    {"content": "Daniel's birthday", "type": "fact", "tags": ["preference"], "importance": 8}
    
    Markdown:
    # Type: fact
    # Tags: [preference, personal]
    # Importance: 8
    # Project: personal
    
    Daniel's birthday: May 8, 1981
    
    Plain text:
    Remember this: Daniel's birthday is May 8
    """
    # Default values
    parsed = {
        "content": text,
        "type": "general",
        "tags": [],
        "importance": 5.0,
        "project": "general",
        "sensitivity": "internal"
    }
    
    # Try JSON first
    if text.strip().startswith('{'):
        try:
            data = json.loads(text)
            parsed.update(data)
            return parsed
        except json.JSONDecodeError:
            pass
    
    # Try Markdown hinting
    header_pattern = r'#\s*(Type|Tags|Importance|Project|Sensitivity):\s*(.+)'
    lines = text.split('\n')
    content_lines = []
    
    for line in lines:
        match = re.match(header_pattern, line.strip())
        if match:
            key = match.group(1).lower().strip()
            value = match.group(2).strip()
            
            if key == 'type':
                parsed['type'] = value
            elif key == 'tags':
                # Parse [tag1, tag2] format
                tags = re.findall(r'[\w-]+', value)
                parsed['tags'] = tags
            elif key == 'importance':
                try:
                    parsed['importance'] = float(value)
                except ValueError:
                    pass
            elif key == 'project':
                parsed['project'] = value
            elif key == 'sensitivity':
                parsed['sensitivity'] = value
        else:
            content_lines.append(line)
    
    # Clean content (remove hint lines)
    parsed['content'] = sanitize('\n'.join(content_lines).strip())
    
    # Also check for inline "Remember this:" prefix
    if 'remember this:' in parsed['content'].lower():
        parsed['content'] = re.sub(r'remember this:\s*', '', parsed['content'], flags=re.IGNORECASE)
    
    return parsed


def remember(text: str, source: str = "manual") -> dict:
    """
    Save important memory to vector store with structured metadata.
    
    Usage:
    
    # JSON format
    remember('{"content": "Daniel's birthday", "type": "fact", "importance": 8}')
    
    # Markdown format
    remember('''
    # Type: fact
    # Tags: [preference, personal]
    # Importance: 8
    
    Daniel's birthday: May 8, 1981
    ''')
    
    # Plain text (auto-parsed)
    remember("Remember this: Daniel's birthday is May 8")
    """
    # Parse input
    parsed = parse_memory_input(text)
    
    # Add timestamp
    parsed['created_at'] = int(time.time())
    parsed['source'] = source
    
    # Write to vector store with structured fields
    try:
        vector_write(
            content=parsed['content'],
            source=source,
            memory_type=parsed['type'],
            tags=parsed['tags'],
            importance=parsed['importance'],
            project=parsed['project'],
            sensitivity=parsed['sensitivity']
        )
        
        return {
            "status": "saved",
            "type": parsed['type'],
            "tags": parsed['tags'],
            "importance": parsed['importance'],
            "project": parsed['project'],
            "content": parsed['content'][:100]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def retrieve_memories(query: str, k: int = 3, filters: dict = None) -> list:
    """
    Retrieve memories with optional filters and hybrid scoring.
    
    Args:
        query: Search query
        k: Number of results
        filters: Optional filters (type, tags, project, etc.)
        
    Returns:
        List of memories with scores
    """
    from app.core.memory import retrieve
    
    results = retrieve(query, k=k * 2)  # Get more, filter later
    
    # Parse stored JSON
    parsed_results = []
    for r in results:
        try:
            data = json.loads(r['content'])
            parsed_results.append({
                "content": data.get('content', r['content']),
                "type": data.get('type', 'general'),
                "tags": data.get('tags', []),
                "importance": data.get('importance', 5.0),
                "project": data.get('project', 'general'),
                "sensitivity": data.get('sensitivity', 'internal'),
                "source": r.get('source', 'unknown'),
                "score": 1.0  # Base score
            })
        except:
            # Fallback for old format
            parsed_results.append({
                "content": r['content'],
                "type": "general",
                "tags": [],
                "importance": 5.0,
                "project": "general",
                "sensitivity": "internal",
                "source": r.get('source', 'unknown'),
                "score": 1.0
            })
    
    # Apply filters
    if filters:
        filtered = []
        for r in parsed_results:
            match = True
            if filters.get('type') and r['type'] != filters['type']:
                match = False
            if filters.get('project') and r['project'] != filters['project']:
                match = False
            if filters.get('tags') and not any(t in r['tags'] for t in filters['tags']):
                match = False
            if match:
                filtered.append(r)
        parsed_results = filtered
    
    # Return top k
    return parsed_results[:k]


# CLI interface
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Remember important things')
    parser.add_argument('content', help='Content to remember (JSON or Markdown format)')
    parser.add_argument('--source', default='manual', help='Source of the memory')
    
    args = parser.parse_args()
    
    result = remember(args.content, args.source)
    print(json.dumps(result, indent=2))
