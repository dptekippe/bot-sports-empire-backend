---
name: dynastydroid-code-review
description: Review DynastyDroid backend code for bugs, security issues, and best practices. Use when editing main.py, static files, or when fixing bugs in the DynastyDroid platform.
---

# DynastyDroid Code Review Skill

## Core Principles

1. **Verify before claiming** - Test endpoints locally before declaring fixes complete
2. **Check for regressions** - Search for similar patterns elsewhere in codebase
3. **Document the fix** - Note what was changed and why in commit messages

## Pre-Push Checklist

Run these before every commit:

```bash
# 1. Syntax check
python3 -m py_compile main.py

# 2. Check for bad patterns
grep -r "chat/channels" static/     # Wrong API paths
grep -r "mock-" static/             # Hardcoded data  
grep -r "localhost:8000" static/   # Hardcoded URLs
grep -n "print(" main.py           # Debug leftovers
grep -n "TODO\|FIXME" main.py     # TODOs

# 3. Test locally
uvicorn main:app --reload
curl localhost:8000/api/v1/leagues
```

## Common Patterns to Check

### API Endpoints (from API.md)
- Channels: `/api/v1/channels/{slug}/posts`
- League chat: `/api/v1/leagues/{id}/chat`
- Player stats: `/api/v1/players/stats?season=2024&week=1`

### Database Models
- Draft, Team, League, LeagueMember, LeagueMessage
- Channel, Post, Comment
- PlayerStats

### Frontend Patterns
- Use `apiFetch()` helper for error logging
- Check localStorage for bot_id
- Handle empty API responses gracefully

## Error Handling

When API calls fail:
```javascript
if (!response.ok) {
    console.warn(`API failed: ${url}`, response.status);
}
```

## Testing Checklist

After deployment, verify:
1. League list loads
2. League switching works
3. Channel navigation works
4. Chat posts and displays
5. Draft board generates

## Related Files

- `/API.md` - API endpoint documentation
- `/AGENTS.md` - Development methodology
- `/main.py` - Backend
- `/static/` - Frontend files
