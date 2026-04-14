# Procedures & Preferences

_Last updated: April 14, 2026_

---

## Technical Procedures

### SIGTERM Prevention — Session Accumulation (Apr 14, 2026)
**Problem:** Hermes getting SIGTERM'd during `mcp_patch` at end of long sessions.
**Root cause:** Accumulated session files from Hermes and OpenClaw main agent.

**Full cleanup protocol:**

**Step 1 — Check all session locations:**
```bash
# Hermes sessions (external SSD)
ls -lt /Volumes/ExternalCorsairSSD/Hermes/sessions/
du -sh /Volumes/ExternalCorsairSSD/Hermes/sessions/

# OpenClaw main sessions
ls -lt ~/.openclaw/agents/main/sessions/
du -sh ~/.openclaw/agents/main/sessions/

# Scout sessions (browser-use)
find /Volumes/ExternalCorsairSSD/Scout/browser-use -name "*.jsonl" 2>/dev/null
```

**Step 2 — Archive Hermes sessions (keep ≤5 days):**
```bash
ARCHIVE_DIR="/Volumes/ExternalCorsairSSD/archived-sessions/hermes-sessions-$(date +%Y-%m-%d)"
mkdir -p "$ARCHIVE_DIR"
cd /Volumes/ExternalCorsairSSD/Hermes/sessions
# Keep sessions from 20260410 onward (adjust cutoff as needed)
for file in session_20260[0-3]*.json session_202603*.json; do
  [ -f "$file" ] && mv "$file" "$ARCHIVE_DIR/" && echo "Archived: $file"
done
```

**Step 3 — Archive OpenClaw main sessions (keep ≤3 days):**
```bash
ARCHIVE_DIR="/Volumes/ExternalCorsairSSD/archived-sessions/2026-$(date +%m-%d)-sessions"
mkdir -p "$ARCHIVE_DIR"
cd ~/.openclaw/agents/main/sessions

# Archive pre-Apr 11 sessions
for uuid in 6b0f0938 3b0f1c58 8881772f e6edf41c c4f6ef69 cc47971f 5909130b 6d4deda1 ed047db2; do
  find . -maxdepth 1 -name "${uuid}*" -exec mv {} "$ARCHIVE_DIR/" \; 2>/dev/null
done

# Remove checkpoint files (orphaned)
rm *.checkpoint.* 2>/dev/null || true
```

**Step 4 — Verify:**
```bash
echo "Hermes: $(ls /Volumes/ExternalCorsairSSD/Hermes/sessions/*.json 2>/dev/null | wc -l) files, $(du -sh /Volumes/ExternalCorsairSSD/Hermes/sessions/ | cut -f1)"
echo "OpenClaw main: $(ls ~/.openclaw/agents/main/sessions/*.jsonl 2>/dev/null | wc -l) files, $(du -sh ~/.openclaw/agents/main/sessions/ | cut -f1)"
```

**Step 5 — Test:**
```bash
cd /Volumes/ExternalCorsairSSD/Hermes && hermes chat -Q -q "Test" --provider minimax --toolsets "file"
```

**Apr 14 findings:** Hermes 235→22 files (22MB→2MB), OpenClaw 57→32 files (213MB→175MB). Largest single file: 17MB Apr 12 session bound to failing Hermes Growth Session cron.

**When to run:** Weekly preventive, or when Hermes starts getting SIGTERM'd.

### SIGTERM Deep Dive Investigation (Apr 14, 2026)
**Problem:** Hermes getting SIGTERM'd during file writes at end of long sessions.
**Note:** Session cleanup alone did NOT resolve SIGTERM. Pattern persists after cleanup.

**Settings found (from config inspection):**
```yaml
# ~/.openclaw/agents/main/agent/models.json
agent:
  max_turns: 60          # Max turns per conversation

# terminal section
terminal:
  timeout: 180           # 3 min terminal timeout
  lifetime_seconds: 300   # 5 min session lifetime

# code_execution section
code_execution:
  timeout: 300           # 5 min code execution timeout
  max_tool_calls: 50     # Max tool calls per session
```

**Settings are reasonable** — none are obviously causing SIGTERM.

**Observed pattern:**
- SIGTERM happens during final file write operations (memory_server.py, HEARTBEAT patches)
- 90% of work completes successfully, process dies during final write
- SIGTERM not SIGKILL (different signal — see below)

**Types of termination:**
- `SIGTERM` (15) — graceful termination request, can be caught/handled
- `SIGKILL` (9) — force kill, cannot be caught
- Recent sessions show SIGKILL on exec timeout

**Possible causes (not confirmed):**
1. Herme's exec subprocess hitting a hidden resource limit
2. The `hermes chat` process itself has a turn/time limit not in config
3. File write operations triggering a size/context limit
4. OpenClaw gateway session size limit during final output generation

**Recommendations to try:**
1. Add `--max-turns 120` to hermes-ui.yaml command
2. Increase `code_execution.max_tool_calls` from 50 to 100
3. Break long tasks into smaller incremental sessions
4. Monitor `hermes chat` process directly during execution

**Note:** The "permission denied" error during file writes to `/Users/danieltekippe/.openclaw/workspace/app/core/` is expected — Hermes can't write to Roger's workspace. She can only write to `/Volumes/ExternalCorsairSSD/shared/` and her own directories.

### Response Cutoff Prevention
**Problem:** Long responses getting cut off mid-transmission.
**Root cause:** Single response too large for session limits.
**Solution:** Break longer tasks into smaller chunks:
- For glossary expansion: add terms in batches of ~20-30
- For large file edits: use multiple edit calls with smaller changes
- For long explanations: break into multiple messages

## Workflow Preferences

### Project Post-Mortem Protocol
After completing any significant project:
1. Create a living spec document from day 1
2. Track all decisions with reasoning (audit trail)
3. Conduct full SDK research before escalating to Daniel
4. Reference spec in final review to ensure expectations met

### SDK Verification Rule (Team Delegation Framework Section 1.G)
Before writing code against external APIs/SDKs:
1. Inspect SDK types FIRST — Read the actual SDK source/type definitions
2. Run a 5-line proof-of-concept — Prove the SDK calls work
3. Confirm build compiles — Run `tsc` before considering code done

## System Configurations

