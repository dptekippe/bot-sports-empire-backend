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

## 🌐 **Browser Control**

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

## 🤖 Matrix Bot Account

- **Handle:** @whiteroger:matrix.org
- **Token:** mat_UHv6KuGNo8c8h6iDcuwmGzi7gPiHvs_hQNQz2
- **Invited to:** Daniel Round Table room
