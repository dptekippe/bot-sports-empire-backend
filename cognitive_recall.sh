#!/bin/bash
# cognitive_recall.sh - Wrapper for pre_action_recall
# Usage: ./cognitive_recall.sh "query text" [user_id]

QUERY="${1:-}"
USER_ID="${2:-00000000-0000-0000-0000-000000000001}"

if [ -z "$QUERY" ]; then
    echo "Usage: $0 <query> [user_id]"
    exit 1
fi

cd /Users/danieltekippe/.openclaw/workspace

# Run the Python recall and extract just the context part
OPENAI_API_KEY="$MINIMAX_API_KEY" MOCK_EMBEDDING=1 python3 -c "
import sys
import warnings
warnings.filterwarnings('ignore')
from cognitive_memory import pre_action_recall
query = sys.argv[1]
user_id = sys.argv[2] if len(sys.argv) > 2 else '00000000-0000-0000-0000-000000000001'
result = pre_action_recall(query, user_id)
print(result)
" "$QUERY" "$USER_ID" 2>/dev/null
