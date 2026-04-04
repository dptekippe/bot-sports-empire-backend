# Roger Tools

Simple, memorable tools for Daniel and Roger.

---

## memory_search - Dual Semantic + Vector Search

Search memories using hybrid pgvector search (semantic similarity + keyword match).

**Location:** `/Users/danieltekippe/.openclaw/workspace/tools/memory_search.py`

**Usage:**
```bash
python3 /Users/danieltekippe/.openclaw/workspace/tools/memory_search.py "code review"
```

**Short alias:**
```bash
./memory_search.sh "code review"
# or
./ms.sh "code review"
```

**Example queries:**
- `python3 memory_search.py "scout"` - Find Scout-related memories
- `python3 memory_search.py "trade value"` - Find trade evaluation memories
- `python3 memory_search.py "hooks"` - Find hook system memories

**Output includes:**
- Relevance score (hybrid of semantic + keyword)
- Domain (trade, architecture, agent-ops, etc.)
- Timestamp
- Content preview
- Tags

---

## Other Tools

More tools coming as needed.
