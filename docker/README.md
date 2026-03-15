# Roger Stack Docker Deployment

## What's Included

- **16 OpenClaw Hooks** - All active hooks:
  - mcts-reflection, render-deploy-gym, self-improve
  - echochamber, futureself, depth-render, meta-gym
  - question-gym, proactive-gym, biascheck-gym, doubttrigger-gym
  - memory-pre-action, and more

- **MetaGym** - Meta-orchestration system
- **PostgreSQL** - Database for memories/insights

## Quick Start

```bash
# 1. Copy env example
cp docker/.env.example docker/.env

# 2. Edit .env with your values
nano docker/.env

# 3. Deploy locally
cd docker
docker-compose up -d

# 4. Or deploy to Render
render-blueprint deploy docker/render.yaml
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| DATABASE_URL | PostgreSQL connection string |
| OPENCLAW_API_KEY | OpenClaw API key |
| MINIMAX_API_KEY | MiniMax API key (for Roger) |

## Render.com Blueprint

```bash
# Deploy to Render using blueprint
render-blueprint deploy docker/render.yaml
```

This will create:
- `roger-stack` - Docker service
- `roger-db` - PostgreSQL database
