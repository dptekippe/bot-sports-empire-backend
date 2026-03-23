# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

## 🤖 Browser Automation (OpenClaw CDP)

OpenClaw includes built-in browser automation via Chrome DevTools Protocol.

### Quick Start
```bash
openclaw browser start
openclaw browser navigate "https://example.com"
openclaw browser snapshot --limit 50
openclaw browser screenshot
openclaw browser stop
```

### Common Commands
| Command | Purpose |
|---------|---------|
| `openclaw browser start` | Start browser |
| `openclaw browser navigate <url>` | Go to URL |
| `openclaw browser snapshot` | Get page content |
| `openclaw browser click <ref>` | Click element |
| `openclaw browser type <ref> "text"` | Type text |
| `openclaw browser stop` | Close browser |

### Use Cases
- Scrape JS-rendered sites (FantasyPros, Draft Sharks)
- Automate web interactions
- Take screenshots

### Example: Scrape FantasyPros
```bash
openclaw browser start
openclaw browser navigate "https://www.fantasypros.com/nfl/rankings/dynasty-overall.php"
openclaw browser snapshot --limit 100
```

See full skill: `skills/browser-automation/SKILL.md`

### **OpenClaw Browser Profiles:**
- **`profile="chrome"`** - Chrome extension relay (requires attached tab)
- **`profile="openclaw"`** - OpenClaw-managed browser (auto-opens, no extension needed)

### **Browser Control Pattern:**
```javascript
browser({
  action: "open",
  targetUrl: "https://example.com",
  profile: "openclaw"  // Use this for reliable browser control
})
```

### **Common Issues & Solutions:**
1. **Extension exclamation mark** → Use `profile="openclaw"` instead
2. **Gateway not running** → `openclaw gateway start`
3. **Port already in use** → `openclaw gateway stop` then restart

### **Test Workflow:**
1. Open browser to google.com: `profile="openclaw"`
2. Navigate to other sites
3. Enter text in forms
4. Take screenshots if needed

**Memory:** Successfully tested 2026-02-18 with Chrome navigation and form interaction.

### **Safari AppleScript Control:**
- **Requirements:** Safari Develop menu enabled + "Allow JavaScript from Apple Events"
- **Method:** macOS AppleScript integration via `osascript` commands
- **Basic navigation:** `osascript -e 'tell application "Safari" to open location "https://..."'`
- **Current URL navigation:** `osascript -e 'tell application "Safari" to set URL of front document to "https://..."'`
- **JavaScript execution:** `do JavaScript` within AppleScript context
- **Form interaction:** JavaScript DOM manipulation for text entry

### **AppleScript Examples:**
```bash
# Open URL
osascript -e 'tell application "Safari" to open location "https://example.com"'

# Navigate current tab  
osascript -e 'tell application "Safari" to set URL of front document to "https://newurl.com"'

# Execute JavaScript
osascript <<'EOF'
tell application "Safari"
  tell front document
    do JavaScript "document.title = 'Test';"
  end tell
end tell
EOF

# Fill form field
osascript <<'EOF'
tell application "Safari"
  tell front document
    do JavaScript "document.querySelector('input').value = 'test';"
  end tell
end tell
EOF
```

**Memory:** Successfully tested 2026-02-18 with Safari navigation to duckduckgo.com → perplexity.ai → JavaScript text entry.

## 🤖 Iris (browser-use - AI Web Agent)

**AI-powered browser automation** - smarter than CDP, handles JS-heavy sites.

### When to use browser-use vs CDP:
- **CDP (openclaw browser):** Simple tasks, screenshots, basic automation
- **browser-use:** Complex tasks, research, scraping dynamic content, AI adaptation

### Setup (already done):
- Location: `/Volumes/ExternalCorsairSSD/Scout/browser-use/`
- Activate: `source .venv/bin/activate`
- Requires: OPENAI_API_KEY

### Quick script:
```python
import asyncio
from browser_use import Agent, Browser
from browser_use.llm import ChatOpenAI

async def main():
    browser = Browser(user_data_dir="/Volumes/ExternalCorsairSSD/Scout/browser-use/user-data")
    agent = Agent(task="YOUR TASK HERE", llm=ChatOpenAI(model="gpt-4o"), browser=browser)
    result = await agent.run()
    print(result)
    await browser.close()

asyncio.run(main())
```

### What makes it different:
- AI thinks step-by-step
- Auto-adapts when pages fail (404s, errors)
- Can search the web (DuckDuckGo)
- Extracts structured data from pages

### Skill: `skills/browser-use/SKILL.md`

## 🤖 DeepAgent (Scout)

**AI coding assistant** - runs code, files, git in persistent sessions.

### Setup (already done):
- Location: `/Volumes/ExternalCorsairSSD/Scout/`
- DeepAgent memories: `deepagent_memories/.deepagents/`
- Skill: `skills/deepagent/SKILL.md`

### Running Scout (DeepAgent):
```bash
# With MiniMax M2.7, no sandbox
deepagents --model anthropic:MiniMax-M2.7 \
  --model-params '{"base_url": "https://api.minimax.io/anthropic", "api_key": "..."}' \
  -n "task" -y
```

Or use the wrapper:
```bash
/Users/danieltekippe/.openclaw/skills/scout-identity/run_scout.sh "your task"
```

### What Scout can do:
- File operations (ls, read, write, edit)
- Shell execution (with approval)
- HTTP API calls
- Web search (needs Tavily API key)
- Subagent delegation
- Persistent memory across sessions

### Key: Scout = DeepAgent
Scout is the name Daniel gave DeepAgent. They're the same thing.

## 🤖 Matrix Bot Account

- **Handle:** @whiteroger:matrix.org
- **Token:** mat_UHv6KuGNo8c8h6iDcuwmGzi7gPiHvs_hQNQz2
- **Invited to:** Daniel Round Table room
