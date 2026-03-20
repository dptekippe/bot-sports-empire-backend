#!/bin/bash
# cognitive_session_start.sh - Called at session start to recall relevant context
# This is invoked by a cron job or manually at session start

cd /Users/danieltekippe/.openclaw/workspace

echo "=== Roger's Memory Context ==="
echo ""

# Recall recent decisions
echo "Recent decisions:"
~/.openclaw/workspace/cognitive_recall.sh "recent dynasty trade decisions" 2>/dev/null | head -10

echo ""
echo "User preferences:"
~/.openclaw/workspace/cognitive_recall.sh "Daniel preferences identity" 2>/dev/null | head -5

echo ""
echo "Active projects:"
~/.openclaw/workspace/cognitive_recall.sh "DynastyDroid project status" 2>/dev/null | head -5

echo ""
echo "================================"
