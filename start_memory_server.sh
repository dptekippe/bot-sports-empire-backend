#!/bin/bash
# Wrapper script to start memory_server with correct environment
export PATH="/opt/anaconda3/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Source shell profiles to get API keys
if [ -f ~/.zshrc ]; then
  source ~/.zshrc 2>/dev/null
fi

# Set DATABASE_URL if not already set
if [ -z "$DATABASE_URL" ]; then
  export DATABASE_URL="postgresql://dynastydroid_user:BKJZCv57P3sYpi5RGL3ciU9CylXsFRWv@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid"
fi

# Set server port (5000 is taken by ControlCenter)
export SERVER_PORT=5001

cd /Users/danieltekippe/.openclaw/workspace/app/core
exec /opt/anaconda3/bin/python3 memory_server.py
