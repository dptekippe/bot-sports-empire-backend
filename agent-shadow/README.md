# Agent Shadow

Real-time response evaluation for OpenClaw agents. Watches log outputs, critiques with local Qwen models, and optionally injects feedback for iteration.

## Concept

Agent Shadow is a "second brain" that monitors your responses in real-time and provides constructive critique. Like having a senior colleague reviewing your work before you send it - except it's always on and runs locally.

## Requirements

- Python 3.8+
- [Ollama](https://ollama.ai) running locally
- Qwen models:
  - `qwen3.5:4b` (fast critique)
  - `qwen3.5:9b` (deep analysis)

## Quick Start

```bash
# 1. Install dependencies
cd agent-shadow
pip3 install requests

# 2. Pull models (if not already)
ollama pull qwen3.5:4b
ollama pull qwen3.5:9b

# 3. Start Ollama (if not running)
ollama serve

# 4. Run Agent Shadow
cd src
python3 run_production.py
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   AGENT SHADOW                              │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐                     │
│  │   Log       │───▶│   Router     │                     │
│  │   Monitor   │    │   (fast/deep)│                     │
│  └──────────────┘    └──────┬───────┘                     │
│                             │                               │
│              ┌──────────────┼──────────────┐               │
│              ▼              ▼              ▼               │
│       ┌──────────┐   ┌──────────┐   ┌──────────┐        │
│       │  Fast    │   │  Deep    │   │          │        │
│       │  Critic  │   │  Critic  │   │ Injector │        │
│       │ (qwen4b) │   │ (qwen9b) │   │          │        │
│       └─────┬────┘   └─────┬────┘   └────┬─────┘        │
│             │              │              │               │
│             └──────────────┼──────────────┘               │
│                            ▼                               │
│                   ┌──────────────┐                         │
│                   │   Session    │                         │
│                   │   ( Roger )  │                         │
│                   └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

## Components

| Component | File | Description |
|-----------|------|-------------|
| Log Monitor | `log_monitor.py` | Watches gateway.log, routes to fast/deep queue |
| Fast Critic | `fast_critic.py` | Quick critique with qwen3.5:4b |
| Deep Critic | `deep_critic.py` | Deep analysis with qwen3.5:9b |
| Injector | `injector.py` | Reviews critiques, optionally injects to session |
| Dashboard | `dashboard.py` | HTTP status page (optional) |
| Launcher | `run_production.py` | Main entry point |

## Configuration

Edit `config/settings.json`:

```json
{
  "auto_inject": false,
  "rate_limit_seconds": 30,
  "critique_threshold": "medium",
  "skip_keywords": ["private", "confidential", "secret"],
  "models": {
    "fast": "qwen3.5:4b",
    "deep": "qwen3.5:9b"
  }
}
```

## Deep Analysis Triggers

Responses containing these keywords will be routed to the deep critic:

**Philosophy & Identity:**
- philosophy, ethics, meaning, consciousness, identity, religion, belief, truth, reality, existence, free will, moral, purpose, value, rights

**AI & Agents:**
- AI, agent, bot, conscious, awareness, future, society, impact, implications

**Technical:**
- fastapi, sqlalchemy, postgresql, postgres, render, render.com, sleeper, api, endpoint, database, backend, frontend, deployment, github, git, docker, cloud, infrastructure

**System Design:**
- architecture, methodology, planning, strategy, design, system, pattern, refactor, optimize, performance, scalability, security, testing

## Usage

### Start Agent Shadow
```bash
cd agent-shadow/src
python3 run_production.py
```

### Check Status
```bash
python3 status.py
```

### View Dashboard
Open http://localhost:18787 in your browser

## Output Files

- `queue/` - Pending fast critiques
- `queue_deep/` - Pending deep critiques  
- `output/` - Completed critiques (JSON)
- `injection.log` - Injection history

## Philosophy

Agent Shadow believes in:
- **Continuous improvement** - Real-time feedback loop
- **Local-first** - No API costs, privacy preserved
- **Scalable depth** - Fast (4b) for quick checks, deep (9b) for complex topics
- **Human oversight** - Auto-inject off by default

## Future Enhancements

- Menu bar app (Tauri)
- Multiple model support
- Custom critique rubrics
- Team/shared configurations

---
*Agent Shadow - Your agent's second opinion*

---
## Status

**Phase 5: Complete** - Production Ready

All phases complete:
- ✅ Phase 1: Core Subagents
- ✅ Phase 2: Injection & Safety  
- ✅ Phase 3: Deep Analysis
- ✅ Phase 4: UI & Coordination
- ✅ Phase 5: Production

**Agent Shadow is production-ready!**

