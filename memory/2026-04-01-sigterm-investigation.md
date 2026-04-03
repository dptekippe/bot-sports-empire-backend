# SIGTERM Investigation - Hermes Report (April 1, 2026)

## Root Cause (HIGH confidence)
OpenClaw's exec tool background session management is the source, NOT Hermes' or Scout's code.

## Evidence
1. Both Hermes (Nous) and Scout (LangGraph) die - shared execution layer problem
2. sessions_spawn (simple shell) works fine for 60 seconds - different exec mechanism
3. Hermes' process_registry.py has NO automatic SIGTERM timers
4. Gateway session cleanup (run.py, session.py) doesn't kill processes
5. 5-14 minute timing is consistent with a watchdog TTL

## Key Difference
- sessions_spawn: Runs inside an existing shell session, simple background command - WORKS
- exec+background for full agents: Spawns new Python process, runs as detached session - SIGTERM

## Files Reviewed
- tools/process_registry.py - Clean, no SIGTERM timers
- gateway/run.py - Session expiry watcher doesn't kill processes
- gateway/config.py - Session reset policy is context only, no kill
- hermes_cli/gateway.py - Standard Launchd plist

## Recommendations
1. Add signal tracing to identify exact SIGTERM sender
2. Check Mac mini launchd/cron for orphan cleanup
3. Compare sessions_spawn vs exec+background behavior differences
4. Scout should investigate OpenClaw's exec session TTL configuration

## Status
This is blocking all multi-step agent tasks. Need to find what's in OpenClaw's exec tool that kills detached sessions after 5-14 minutes.
