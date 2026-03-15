# Wakeup Flow Spec - March 13, 2026

## New Wakeup Context Layers

| Layer | Source | Size | Purpose |
|-------|--------|------|---------|
| 1-5 | Static files (AGENTS/SOUL/MEMORY/HEARTBEAT/USER) | ~1KB | Identity/goals |
| 6 | Recent: memory/YYYY-MM-DD.md | ~1KB | Time-sensitive (trades, events) |
| 7 | pgvector: Top 5 hybrid_score | ~3KB | Evergreen (DB facts, protocols) |
| **Total** | | **~5KB** | vs 140KB bloat |

## Implementation

### Handler Endpoint (handler.ts)

```typescript
app.get('/wakeup', async (req, res) => {
  const recentFile = `memory/${new Date().toISOString().split('T')[0]}.md`;
  const recent = fs.existsSync(recentFile) 
    ? fs.readFileSync(recentFile, 'utf8').slice(0, 1000) 
    : '';
  
  const top5 = await db.query(`
    SELECT content, hybrid_score 
    FROM memories 
    ORDER BY hybrid_score DESC 
    LIMIT 5
  `);
  
  res.json({
    recent: recent.trim(),
    top5: top5.rows.map(r => `${r.content.slice(0,500)} [score:${r.hybrid_score}]`).join('\n\n')
  });
});
```

### AGENTS.md Injection

```
Recent (24h): {{wakeup.recent}}
Top pgvector: {{wakeup.top5}}
```

## Status

- [ ] Implement /wakeup endpoint in handler.ts
- [ ] Add to AGENTS.md template
- [ ] Test in new session
