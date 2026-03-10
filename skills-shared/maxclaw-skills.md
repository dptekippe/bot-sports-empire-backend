# MaxClaw Skills - For Black Roger

*Skills available on White Roger (MaxClaw cloud) that Black Roger can reference and learn from.*

---

## GitHub Operations (`gh` CLI)

**Use for:** PRs, issues, CI status, repo queries

**How to use:**
```bash
gh pr status              # Check open PRs
gh issue list            # List issues
gh run list              # List CI runs
gh run view <id>        # View CI log
gh api repos/owner/repo  # Query API
```

**Black Roger:** Use `exec` with `gh` commands. Requires `gh` installed.

---

## Healthcheck - Security Auditing

**Use for:** Host security hardening, firewall checks, risk assessment

**How to use:**
- Read-only by default
- Requires explicit approval for changes
- Check: OS version, firewall status, SSH config, disk encryption
- Run: `openclaw gateway status` for OpenClaw-specific checks

**Black Roger:** Run via exec, requires sudo for some checks.

---

## Session Logs

**Use for:** Analyzing conversation history, debugging issues

**How to use:**
- Stores conversation transcripts
- Searchable by session key or timestamp
- Useful for: understanding what happened in past sessions

**Black Roger:** Access via memory/sessions/ or OpenClaw session tools.

---

## Coding Agent

**Use for:** Delegating complex coding tasks to sub-agents

**How to use:**
```python
# Spawns a coding agent
sessions_spawn(task="fix bug in main.py", runtime="subagent")
```

**Black Roger:** Can use this to offload coding tasks.

---

## Discord (Bot Operations)

**Use for:** Discord bot management, message operations

**Available actions:**
- send, edit, delete messages
- react, pin, create threads
- channel management

**Black Roger:** Uses this skill to interact via Discord.

---

## Web Research

**Use for:** Finding current information, fact-checking

**Tools available:**
- `batch_web_search` - Google-like search
- `extract_content_from_websites` - Parse web pages
- `images_search_and_download` - Find images

**Black Roger:** Can request White Roger to do research using these tools.

---

## TTS (Text-to-Speech)

**Use for:** Converting text to audio

**How:**
```python
tts(text="Hello Dan", channel="discord")
```

**Black Roger:** Can request via coordination.

---

## Image Synthesis

**Use for:** Generating images from prompts

**How:**
```python
image_synthesize(requests=[{"prompt": "robot", "output_file": "robot.png"}])
```

**Black Roger:** Can request White Roger to generate images.

---

## Browser Control

**Use for:** Web automation, screenshots, form filling

**Actions:**
- open, navigate, click, type
- snapshot, screenshot
- fill forms, evaluate JavaScript

**Black Roger:** Has via local browser tools.

---

## Nodes (Device Control)

**Use for:** Paired device management, notifications, camera

**Actions:**
- device_status, camera_snap, notifications_list
- Run commands on paired devices

**Black Roger:** Could pair with Dan's devices.

---

## Skills Summary Table

| Skill | What It Does | Black Roger Access |
|-------|--------------|-------------------|
| github | GitHub CLI ops | Via exec |
| healthcheck | Security audits | Via exec |
| session-logs | Conversation history | Via memory |
| coding-agent | Sub-agent spawning | Via sessions_spawn |
| discord | Bot operations | Direct |
| web-research | Info gathering | Request WR |
| tts | Text-to-speech | Request WR |
| image-gen | Image generation | Request WR |
| browser | Web automation | Via browser tool |
| nodes | Device control | Via nodes tool |

---

## How to Request White Roger Skills

When you need something White Roger can do:

1. **Research:** Ask "Can you research X?"
2. **Images:** Ask "Generate an image of X"
3. **TTS:** Ask "Speak this message"
4. **Web extraction:** Ask "Get content from URL"

White Roger will execute and return results.

---

*Last updated: 2026-03-08*
