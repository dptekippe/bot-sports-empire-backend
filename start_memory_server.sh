#!/bin/bash
# Wrapper script to start memory_server with correct environment
export PATH="/opt/anaconda3/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
cd /Users/danieltekippe/.openclaw/workspace
exec /opt/anaconda3/bin/python3 /Users/danieltekippe/.openclaw/workspace/app/core/memory_server.py
