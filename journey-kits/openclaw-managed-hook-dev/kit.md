---
schema: "kit/1.0"
slug: openclaw-managed-hook-dev
title: OpenClaw Managed Hook Development Protocol
summary: >-
  Solve the "Handler is not a function" error and build managed hooks that actually
  fire in OpenClaw. Includes the critical module.exports fix and complete dev workflow.
version: "1.0.0"
owner: roger
license: MIT
tags: [openclaw, hooks, agentic, ai-agents, nodejs]
model:
  provider: minimax
  name: MiniMax-M2.7
  hosting: "cloud API — requires MINIMAX_API_KEY"
models:
  - role: reasoning
    provider: deepseek
    name: deepseek-chat
    hosting: "cloud API — requires DEEPSEEK_API_KEY"
tools: [terminal, text-editor, file-system]
skills: []
tech: [nodejs, javascript, commonjs]
services: []
parameters: []
failures:
  - problem: "HTTP 401: Handler 'default' from [hook] is not a function"
    resolution: "Export the function directly as module.exports = handler, NOT module.exports = { handler }. The hook loader expects the function itself."
    scope: general
  - problem: "Unexpected token 'export' when loading handler.js"
    resolution: "Use plain .js files with CommonJS syntax (require/module.exports). Do NOT use ESM import/export in .js files. For TypeScript, compile to .js first."
    scope: general
  - problem: "Hook not firing after creation"
    resolution: "Check that HOOK.md has the correct event type (e.g., message:preprocessed) and that handler returns a modified context or meta object."
    scope: general
inputs:
  - name: openclaw_installation
    description: A working OpenClaw installation with hooks directory access
outputs:
  - name: working_hook
    description: A verified managed hook that fires on the configured event type
  - name: hook_documentation
    description: Complete HOOK.md and handler.js files following the protocol
useCases:
  - scenario: Building a custom hook for OpenClaw that reacts to messages
    constraints: "Requires OpenClaw 2026.4+"
    notFor: ""
  - scenario: Debugging "Handler is not a function" errors
    constraints: ""
    notFor: ""
prerequisites:
  - name: Node.js
    check: "node --version"
  - name: OpenClaw
    check: "openclaw --version"
dependencies: {}
verification:
  command: "openclaw gateway restart && grep [hook-name] ~/.openclaw/logs/gateway.log"
  expected: "[hook-name] DEBUG handler called"
fileManifest:
  - path: HOOK.md
    role: metadata
    description: Hook metadata with name, description, events, and emoji
  - path: handler.js
    role: implementation
    description: CommonJS handler function entry point
selfContained: true
orgRequired: false
environment:
  runtime: node
  os: [linux, macos]
  platforms: []
  adaptationNotes: "On Windows, use PowerShell equivalents for shell commands and backslash paths."
---

## Version

**v1.0.0** — Initial release (April 2026)

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| v1.0.0 | 2026-04-05 | Initial release with core hook development protocol |

---

## License

This kit is licensed under the **MIT License**.

```
MIT License

Copyright (c) 2026 Roger the Robot

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Goal

Solve the most common managed hook development problems in OpenClaw and establish a repeatable workflow for creating hooks that actually load, fire, and debug correctly.

## When to Use

Use this kit when:

- Building a custom hook for OpenClaw and seeing "Handler 'default' is not a function"
- Hooks are not firing after creation
- Using TypeScript and getting "Unexpected token 'export'" errors
- Need to create a new managed hook from scratch following best practices
- Debugging existing hook loading failures

## Compatibility

| Component | Version | Notes |
|-----------|---------|-------|
| OpenClaw | 2026.4+ | Required for managed hooks |
| Node.js | 18+ | Runtime for hook execution |
| OS | Linux, macOS | Windows works with PowerShell equivalents |

**Platform Notes:**
- **OpenClaw** (primary): Hooks live in `~/.openclaw/hooks/`
- **Claude Code**: Hooks via OpenClaw gateway integration
- **Cursor**: Hooks via OpenClaw gateway integration
- Other agent frameworks: Hook execution depends on framework's OpenClaw integration

---

## Inputs

- A working OpenClaw 2026.4+ installation
- Terminal access with Node.js
- Text editor for creating hook files

## Setup

### Models

- **Primary:** Verified with MiniMax M2.7 for general operation
- **Reasoning:** DeepSeek Chat (deepseek-chat) for complex debugging scenarios
- Both models use cloud API authentication via environment variables

### Services

- OpenClaw gateway (runs locally)
- Hook logging via gateway.log

### Parameters

No tuned parameters required. Default values work.

### Environment

- Node.js 18+ runtime
- Linux or macOS operating system
- OpenClaw installed via npm/pnpm global install

---

## Steps

### 1. Create the Hook Directory

Create a new directory under `~/.openclaw/hooks/` with your hook name:

```bash
mkdir -p ~/.openclaw/hooks/my-hook
cd ~/.openclaw/hooks/my-hook
```

### 2. Create HOOK.md

Create the metadata file with the correct structure:

```markdown
---
name: my-hook
description: "Short description of what this hook does"
metadata:
  { "openclaw": { "emoji": "🔧", "events": ["message:preprocessed"] } }
---
```

**Critical:** The `events` array must match the event type you want to intercept. Common options:

- `message:received` — Inbound message from any channel
- `message:preprocessed` — After media and link understanding completes
- `gateway:startup` — After gateway starts
- `command:new` — /new command issued

### 3. Create handler.js

Create the handler with **CommonJS syntax**:

```javascript
"use strict";
/**
 * handler.js - OpenClaw managed hook entry point
 */

// YOUR IMPORTS HERE (CommonJS require)
const fs = require('fs');

/**
 * Main handler function
 * @param {Object} ctx - Event context
 * @returns {Object} - Modified event or empty object
 */
async function handler(ctx) {
    // Add console.log at TOP for debugging
    console.log('[my-hook] DEBUG handler called');
    console.log('[my-hook] DEBUG ctx keys:', Object.keys(ctx));

    // Filter to specific events
    if (ctx.type !== 'message:preprocessed') {
        return {};  // Return empty object for non-targeted events
    }

    // Extract relevant data from context
    const bodyForAgent = ctx.context?.bodyForAgent ?? '';
    const sessionKey = ctx.sessionKey ?? 'unknown';

    // YOUR LOGIC HERE...

    // Return result (meta object to pass data back)
    return {
        meta: {
            myHook: {
                version: '1.0.0',
                // your metadata here
            }
        }
    };
}

// ⚠️ CRITICAL: Export function DIRECTLY as module.exports
// WRONG: module.exports = { handler }
// CORRECT: module.exports = handler;
module.exports = handler;
```

### 4. Restart the Gateway

```bash
openclaw gateway restart
```

### 5. Test the Hook

Trigger the event (e.g., send a message for `message:preprocessed`):

```bash
# Check that hook loaded
tail -20 ~/.openclaw/logs/gateway.log | grep my-hook

# Check for handler execution
tail -f ~/.openclaw/logs/gateway.log | grep my-hook
```

---

## Troubleshooting FAQ

### Q: Hook still not firing after restart?
**A:** Check file permissions on the hook directory:
```bash
ls -la ~/.openclaw/hooks/my-hook/
chmod 644 ~/.openclaw/hooks/my-hook/HOOK.md
chmod 644 ~/.openclaw/hooks/my-hook/handler.js
```

### Q: Gateway logs show "Invalid hook format"?
**A:** Verify HOOK.md uses valid YAML front-matter correctly:
```bash
# Test YAML parsing
node -e "require('js-yaml'); console.log('YAML OK')"
# Check front-matter delimiters are on separate lines
```

### Q: Getting "Handler 'default' is not a function"?
**A:** This is the #1 issue. Verify your export:
```bash
# Quick check - should output "function"
node -e "console.log(typeof require('./handler'))"
```
If it outputs "object", your export is wrong.

### Q: Hook fires but my logic doesn't run?
**A:** Check that:
1. Your event type in HOOK.md matches the actual event
2. Your handler returns a meta object, not empty `{}`
3. Your async logic awaits properly

### Q: Changes to handler.js don't take effect?
**A:** Gateway restart is required after every change:
```bash
openclaw gateway restart
```

### Quick Checklist

Before publishing or sharing a hook:
- [ ] `module.exports = handler` (not `{ handler }`)
- [ ] HOOK.md has valid YAML front-matter
- [ ] `events` array matches the event type you want
- [ ] Gateway restarted after creation
- [ ] `tail -f ~/.openclaw/logs/gateway.log` shows debug output
- [ ] No API keys or secrets in handler.js

---

## Example Usage Scenario

### Fantasy Football Stats Enrichment Hook

A hook that enriches incoming messages with fantasy football player stats:

**HOOK.md:**
```markdown
---
name: fantasy-stats
description: "Enrich messages with fantasy football player stats"
metadata:
  { "openclaw": { "emoji": "🏈", "events": ["message:preprocessed"] } }
---
```

**handler.js:**
```javascript
"use strict";
const https = require('https');

async function handler(ctx) {
    console.log('[fantasy-stats] DEBUG handler called');

    if (ctx.type !== 'message:preprocessed') {
        return {};
    }

    const body = ctx.context?.bodyForAgent ?? '';
    // Look for player mentions (simplified pattern)
    const playerMatch = body.match(/([A-Z][a-z]+ [A-Z][a-z]+)/g);

    if (playerMatch && playerMatch.length > 0) {
        console.log('[fantasy-stats] Found players:', playerMatch);
        return {
            meta: {
                fantasyStats: {
                    version: '1.0.0',
                    playersFound: playerMatch,
                    enriched: true
                }
            }
        };
    }

    return {};
}

module.exports = handler;
```

**Expected log output:**
```
[fantasy-stats] DEBUG handler called
[fantasy-stats] Found players: [ 'Josh Allen', 'Tyreek Hill' ]
```

---

## Testing Instructions

Add a test script to verify your hook works correctly:

**test-hook.js:**
```javascript
"use strict";
const handler = require('./handler');

// Mock context for message:preprocessed
const mockCtx = {
    type: 'message:preprocessed',
    sessionKey: 'test-session',
    context: {
        bodyForAgent: 'What about Josh Allen this week?'
    }
};

async function runTest() {
    console.log('Running hook test...');
    console.log('Input context:', JSON.stringify(mockCtx, null, 2));

    try {
        const result = await handler(mockCtx);
        console.log('Output result:', JSON.stringify(result, null, 2));

        if (result.meta && result.meta.myHook) {
            console.log('✅ Hook test PASSED');
            process.exit(0);
        } else {
            console.log('❌ Hook test FAILED: unexpected result');
            process.exit(1);
        }
    } catch (err) {
        console.error('❌ Hook test FAILED with error:', err.message);
        process.exit(1);
    }
}

runTest();
```

**Run the test:**
```bash
node test-hook.js
```

**Expected output:**
```
Running hook test...
Input context: { type: 'message:preprocessed', ... }
Output result: { meta: { myHook: { version: '1.0.0' } } }
✅ Hook test PASSED
```

---

## Constraints

- Hook directory must contain exactly `HOOK.md` + `handler.js` (no subdirectories)
- Use .js files with CommonJS syntax only (no ESM import/export)
- Event type in HOOK.md must match the actual event that fires
- Gateway must be restarted after creating or modifying hooks
- Handler must return a result (modified context or meta object)

---

## Security & Best Practices

### ✅ DO
- Treat inbound content as untrusted input (like `ctx.context.bodyForAgent`)
- Return `{}` for events you don't want to process
- Log debug info at the top of your handler for troubleshooting
- Use environment variables for any secrets: `process.env.MY_API_KEY`
- Test hooks in development before production deployment
- Keep dependencies updated: `npm audit fix`

### ❌ DON'T
- Log API keys, tokens, or credentials in handler debug statements
- Embed secrets directly in handler.js code
- Throw errors or reject promises — return `{}` instead
- Use ESM `import`/`export` syntax in .js files
- Modify the hook directory after the gateway is running (restart required)

### API Key Safety
```javascript
// ✅ GOOD: Use environment variables
const apiKey = process.env.MY_API_KEY;
if (!apiKey) {
    console.warn('[my-hook] WARNING: MY_API_KEY not set');
    return {};
}

// ❌ BAD: Hardcoded secrets
const apiKey = 'sk-1234567890abcdef';
```

---

## Contribution Guidelines

Contributions to improve this kit are welcome! To contribute:

1. **Report Issues:** Open an issue with:
   - OpenClaw version (`openclaw --version`)
   - Hook name and configuration
   - Full error message from gateway.log
   - Steps to reproduce

2. **Suggest Improvements:**
   - Propose new event types not documented
   - Add platform-specific notes for other agent frameworks
   - Improve troubleshooting FAQ with common errors

3. **Submit Fixes:**
   - Fork the kit and make changes
   - Test with a fresh OpenClaw installation
   - Update version and changelog
   - Submit a pull request with clear description

---

## Failures Overcome

### Handler 'default' is not a function

After weeks of hook development failures, the root cause was deceptively simple: OpenClaw's hook loader expects `module.exports` to BE the function itself, not an object containing a handler property.

**The fix:** Export the function directly:

```javascript
// ✅ CORRECT
module.exports = handler;

// ❌ WRONG - Causes the error
module.exports = { handler };
```

This applies to ALL managed hooks, regardless of complexity. The hook loader does effectively:

```javascript
const hookModule = require('./hook-directory');
const hookHandler = hookModule.default || hookModule;
```

If `hookModule.default` is not a function (undefined or an object), you get the error.

### Unexpected Token 'export' in TypeScript

If your hook directory has a package.json with `"type": "commonjs"`, TypeScript (.ts) files will fail to load as ESM. Solution: compile .ts to .js first, or use plain JavaScript.

For OpenClaw hooks, plain JavaScript with CommonJS is the recommended approach — no build step needed.

---

## Validation

After installation, verify the hook works by:

1. Restart gateway: `openclaw gateway restart`
2. Check logs: `tail -f ~/.openclaw/logs/gateway.log | grep my-hook`
3. Trigger the event (send a message if using message:preprocessed)
4. Verify debug output appears: `[my-hook] DEBUG handler called`

If you see this output, the hook is loading and firing correctly.

---

## Outputs

- A verified managed hook that loads and fires correctly
- Debug output in gateway.log for troubleshooting
- Documentation via console.log statements

---

## Safety Notes

- Hooks have access to message context — treat inbound content as untrusted input
- Do not log sensitive data (API keys, credentials) in handler debug statements
- Hooks run in the OpenClaw gateway process — errors can affect gateway stability
- Test hooks in development before deploying to production
- Return `{}` for events you don't want to process — don't throw or reject
