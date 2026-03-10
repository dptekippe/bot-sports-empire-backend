# Phase 6: Frontend Setup & Internal ADP

## 🚀 Frontend Setup Commands

```bash
# Navigate to project root
cd /Volumes/External\ Corsair\ SSD\ /bot-sports-empire

# Create Vite React app
npm create vite@latest frontend --template react

# Install dependencies
cd frontend
npm install

# Install additional dependencies
npm install axios socket.io-client @tanstack/react-query
npm install -D @types/node

# Create proxy configuration
cat > vite.config.js << 'EOF'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/ws': {
        target: 'ws://localhost:8001',
        ws: true,
        changeOrigin: true
      }
    }
  }
})
EOF

# Create .env file
cat > .env << 'EOF'
VITE_API_URL=/api
VITE_WS_URL=ws://localhost:8001
EOF
```

## 🎯 Draft Board Component Structure

```javascript
// src/components/DraftBoard.jsx
import React, { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { io } from 'socket.io-client';
import axios from 'axios';

const DraftBoard = ({ draftId }) => {
  const [socket, setSocket] = useState(null);
  const queryClient = useQueryClient();

  // Fetch draft data
  const { data: draft, isLoading } = useQuery({
    queryKey: ['draft', draftId],
    queryFn: () => axios.get(`/api/v1/drafts/${draftId}`).then(res => res.data)
  });

  // Fetch picks
  const { data: picks } = useQuery({
    queryKey: ['picks', draftId],
    queryFn: () => axios.get(`/api/v1/drafts/${draftId}/picks`).then(res => res.data),
    enabled: !!draftId
  });

  // WebSocket connection
  useEffect(() => {
    if (!draftId) return;

    const newSocket = io(`ws://localhost:8001/ws/drafts/${draftId}`);
    setSocket(newSocket);

    newSocket.on('connect', () => {
      console.log('Connected to draft room');
    });

    newSocket.on('pick_made', (data) => {
      console.log('Pick made:', data);
      queryClient.invalidateQueries(['picks', draftId]);
    });

    newSocket.on('chat_message', (data) => {
      console.log('Chat:', data);
    });

    return () => newSocket.close();
  }, [draftId, queryClient]);

  // Assign pick mutation
  const assignPick = useMutation({
    mutationFn: ({ pickId, playerId }) => 
      axios.post(`/api/v1/drafts/${draftId}/picks/${pickId}/assign`, { player_id: playerId }),
    onSuccess: () => {
      queryClient.invalidateQueries(['picks', draftId]);
    }
  });

  if (isLoading) return <div>Loading draft...</div>;

  return (
    <div className="draft-board">
      <h1>{draft?.name} - Draft Board</h1>
      <div className="picks-grid">
        {picks?.map(pick => (
          <div key={pick.id} className="pick-card">
            <div className="pick-info">
              <span className="pick-number">#{pick.pick_number}</span>
              <span className="round">Round {pick.round}</span>
            </div>
            <div className="team">{pick.team_name || `Team ${pick.team_id}`}</div>
            <div className="player">
              {pick.player_name || 'Available'}
            </div>
            {!pick.player_id && (
              <button 
                onClick={() => assignPick.mutate({ 
                  pickId: pick.id, 
                  playerId: '4046' // Example
                })}
                disabled={assignPick.isLoading}
              >
                Pick Player
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default DraftBoard;
```

## 📊 Internal ADP Endpoint Design

### **Endpoint:** `POST /api/v1/leagues/{league_id}/internal-adp`

**Purpose:** Compute average draft position from DraftHistory, cache in Redis

**Request:**
```json
{
  "recent_weight": 1.5,  // Weight for recent drafts (last 30 days)
  "min_picks": 10,       // Minimum picks to compute ADP
  "refresh_cache": true  // Force cache refresh
}
```

**Response:**
```json
{
  "league_id": "league_123",
  "computed_at": "2026-02-01T22:45:00Z",
  "player_adp": [
    {
      "player_id": "4046",
      "full_name": "Patrick Mahomes",
      "position": "QB",
      "adp": 24.8,
      "pick_count": 45,
      "recent_adp": 23.2,
      "weighted_adp": 24.1,
      "vs_external_adp": -0.7  // Difference from FFC ADP
    }
  ],
  "cache_key": "adp:league_123",
  "cache_ttl": 3600
}
```

### **Implementation Plan:**

```python
# app/api/endpoints/internal_adp.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import redis
import json

from ...core.database import get_db
from ...core.redis import get_redis
from ...models.draft_history import DraftHistory
from ...models.player import Player

router = APIRouter()

@router.post("/leagues/{league_id}/internal-adp")
async def compute_internal_adp(
    league_id: str,
    recent_weight: float = 1.5,
    min_picks: int = 10,
    refresh_cache: bool = False,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Compute internal ADP for a league.
    
    Uses DraftHistory to compute weighted average pick position.
    Recent drafts (last 30 days) are weighted more heavily.
    Results cached in Redis for 1 hour.
    """
    cache_key = f"adp:league:{league_id}"
    
    # Check cache
    if not refresh_cache:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    
    # Compute ADP from DraftHistory
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # Get all picks for this league
    picks = db.query(
        DraftHistory.player_id,
        DraftHistory.pick_number,
        DraftHistory.created_at
    ).filter(
        DraftHistory.league_id == league_id,
        DraftHistory.draft_type == "internal"
    ).all()
    
    if len(picks) < min_picks:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough draft picks ({len(picks)} < {min_picks})"
        )
    
    # Group by player and compute weighted ADP
    player_stats = {}
    for pick in picks:
        player_id = pick.player_id
        if player_id not in player_stats:
            player_stats[player_id] = {
                "total_picks": 0,
                "sum_pick_numbers": 0,
                "recent_picks": 0,
                "sum_recent_pick_numbers": 0
            }
        
        stats = player_stats[player_id]
        stats["total_picks"] += 1
        stats["sum_pick_numbers"] += pick.pick_number
        
        # Check if recent
        if pick.created_at >= thirty_days_ago:
            stats["recent_picks"] += 1
            stats["sum_recent_pick_numbers"] += pick.pick_number
    
    # Compute weighted ADP for each player
    player_adp = []
    for player_id, stats in player_stats.items():
        if stats["total_picks"] == 0:
            continue
        
        # Regular ADP
        regular_adp = stats["sum_pick_numbers"] / stats["total_picks"]
        
        # Recent ADP (if available)
        recent_adp = None
        if stats["recent_picks"] > 0:
            recent_adp = stats["sum_recent_pick_numbers"] / stats["recent_picks"]
        
        # Weighted ADP
        if recent_adp:
            weighted_adp = (
                (regular_adp * stats["total_picks"]) + 
                (recent_adp * stats["recent_picks"] * recent_weight)
            ) / (stats["total_picks"] + stats["recent_picks"] * recent_weight)
        else:
            weighted_adp = regular_adp
        
        # Get player info
        player = db.query(Player).filter(Player.player_id == player_id).first()
        if player:
            player_adp.append({
                "player_id": player_id,
                "full_name": player.full_name,
                "position": player.position,
                "adp": round(regular_adp, 2),
                "recent_adp": round(recent_adp, 2) if recent_adp else None,
                "weighted_adp": round(weighted_adp, 2),
                "pick_count": stats["total_picks"],
                "recent_pick_count": stats["recent_picks"],
                "vs_external_adp": round(player.external_adp - weighted_adp, 2) 
                    if player.external_adp else None
            })
    
    # Sort by weighted ADP
    player_adp.sort(key=lambda x: x["weighted_adp"])
    
    # Prepare response
    response = {
        "league_id": league_id,
        "computed_at": datetime.utcnow().isoformat() + "Z",
        "player_adp": player_adp,
        "total_picks": len(picks),
        "unique_players": len(player_adp),
        "cache_key": cache_key,
        "cache_ttl": 3600
    }
    
    # Cache in Redis
    redis_client.setex(cache_key, 3600, json.dumps(response, default=str))
    
    return response
```

## 🚀 Phase 6 Implementation Plan

### **Week 1: Frontend Foundation**
1. ✅ Set up Vite React with proxy configuration
2. Create draft board component with WebSocket integration
3. Implement player search and pick assignment UI
4. Add real-time updates for picks

### **Week 2: Internal ADP System**
1. Implement `POST /leagues/{id}/internal-adp` endpoint
2. Add Redis caching layer
3. Create comparison views (internal vs external ADP)
4. Add ADP trend analysis

### **Week 3: Enhanced Features**
1. Bot AI integration in UI
2. Draft strategy recommendations
3. Mobile-responsive design
4. Export/import functionality

### **Week 4: Polish & Deployment**
1. Performance optimization
2. Error handling and loading states
3. Documentation
4. Render deployment for frontend

## 🔧 Next Immediate Steps

1. **Run frontend setup commands**
2. **Implement internal ADP endpoint**
3. **Create basic draft board UI**
4. **Test end-to-end flow**

**Render Beta:** Follows Docker validation completion (✅ Docker green!)