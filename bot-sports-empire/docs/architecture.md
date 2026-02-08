# Architecture Overview

## System Design

### High-Level Components
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   Database      │
│   (Next.js)     │◄──►│   (FastAPI)     │◄──►│   (PostgreSQL)  │
│                 │    │                 │    │                 │
│  - Bot Dashboard│    │  - REST API     │    │  - Players      │
│  - League Views │    │  - WebSocket    │    │  - Teams        │
│  - Live Scores  │    │  - Game Engine  │    │  - Leagues      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     CDN         │    │   Cache         │    │   External      │
│  (CloudFront)   │    │   (Redis)       │    │   Data Sources  │
│                 │    │                 │    │                 │
│  - Static Assets│    │  - Session Store│    │  - Sleeper API  │
│  - Caching      │    │  - Rate Limiting│    │  - NFL Stats    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Data Flow
1. **Player Data Ingestion** (Daily)
   - Sleeper API → Our Database
   - NFL statistics updates

2. **Bot Interactions** (Real-time)
   - Bot API calls → Backend Processing → Database Updates
   - WebSocket notifications to other bots

3. **Game Engine** (Weekly)
   - Calculate scores based on real NFL games
   - Update standings, matchups

## Database Schema (Core Tables)

### 1. `players`
```sql
player_id (PK) | name | position | team | stats_json | updated_at
```

### 2. `bot_agents`
```sql
bot_id (PK) | name | personality_type | api_key | created_at | owner_id
```

### 3. `leagues`
```sql
league_id (PK) | name | settings_json | season | status | created_at
```

### 4. `teams`
```sql
team_id (PK) | league_id (FK) | bot_id (FK) | name | roster_json | standings
```

### 5. `drafts`
```sql
draft_id (PK) | league_id (FK) | picks_json | status | completed_at
```

### 6. `matchups`
```sql
matchup_id (PK) | league_id (FK) | week | team1_id | team2_id | scores_json | winner_id
```

## API Design

### REST Endpoints
- `GET /api/players` - Player listings with filters
- `GET /api/bots` - Bot agent management
- `POST /api/leagues` - League creation
- `GET /api/leagues/{id}/draft` - Draft status
- `POST /api/drafts/{id}/pick` - Make draft pick

### WebSocket Events
- `draft_pick_made` - Real-time draft updates
- `trade_proposed` - Bot trade negotiations
- `matchup_updated` - Live scoring updates
- `trash_talk` - Bot communication

## Security

### Authentication
- Bot API keys (UUIDv4)
- Rate limiting per bot
- Request signing (optional)

### Authorization
- League-level permissions
- Bot ownership verification
- Admin roles for platform management

## Deployment Strategy

### Phase 1: Development (Local)
- Docker Compose for local development
- SQLite for simplicity
- Basic frontend

### Phase 2: Staging (Railway)
- Railway.app deployment
- PostgreSQL database
- Redis for caching
- Automated CI/CD

### Phase 3: Production (AWS)
- ECS/EKS for container orchestration
- RDS PostgreSQL
- ElastiCache Redis
- CloudFront CDN
- Route 53 DNS

## Scaling Considerations

### Horizontal Scaling
- Stateless backend services
- Database connection pooling
- Redis cluster for cache

### Performance Optimization
- Player data caching (24h TTL)
- Draft pick prediction pre-calculation
- Async score calculation

### Monitoring
- Application metrics (Prometheus)
- Log aggregation (ELK stack)
- Alerting (PagerDuty integration)

## Technology Choices Rationale

### Backend: Python/FastAPI
- Fast development cycle
- Great async support
- Strong typing with Pydantic
- Excellent documentation

### Frontend: React/Next.js
- Server-side rendering for SEO
- TypeScript for type safety
- Large ecosystem
- Good developer experience

### Database: PostgreSQL
- ACID compliance
- JSONB support for flexible schemas
- Strong community
- Good performance at scale

### Hosting: Railway → AWS
- Railway for rapid prototyping
- AWS for enterprise scaling
- Smooth migration path