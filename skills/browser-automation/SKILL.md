# Skill: browser-automation
# Description: Control browser via OpenClaw CDP (Chrome DevTools Protocol)

## When to use
- Scrape JavaScript-rendered sites (FantasyPros, Draft Sharks, etc.)
- Need to wait for dynamic content to load
- Interactive pages that need login/clicking

## Commands

### Start browser
```bash
openclaw browser start
```

### Navigate to URL
```bash
openclaw browser navigate "https://example.com"
```

### Get page snapshot (accessibility tree)
```bash
openclaw browser snapshot --limit 50
```

### Click element
```bash
openclaw browser click <ref_number>
```

### Type text
```bash
openclaw browser type <ref_number> "text"
```

### Wait for element
```bash
openclaw browser wait --text "Loading..."
```

### Get console errors
```bash
openclaw browser console --level error
```

### Screenshot
```bash
openclaw browser screenshot
```

### Close browser
```bash
openclaw browser stop
```

## Example: Scrape FantasyPros
```bash
# Start
openclaw browser start

# Navigate
openclaw browser navigate "https://www.fantasypros.com/nfl/rankings/dynasty-overall.php"

# Wait for load, get snapshot
openclaw browser snapshot --limit 100

# Extract data from snapshot (JSON output)
```

## Tips
- Use `--limit` to control snapshot size
- Elements referenced by numbers (ref) in snapshot
- Check console for errors: `openclaw browser console --level error`
- Can use `evaluate` to run JavaScript: `openclaw browser evaluate --fn "() => document.title"`
