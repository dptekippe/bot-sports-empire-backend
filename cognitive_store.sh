#!/bin/bash
# cognitive_store.sh - Wrapper for post_action_store
# Usage: ./cognitive_store.sh "<content>" <namespace> [decision_outcome]

CONTENT="${1:-}"
NAMESPACE="${2:-context}"
OUTCOME="${3:-}"

if [ -z "$CONTENT" ]; then
    echo "Usage: $0 <content> [namespace] [decision_outcome]"
    exit 1
fi

cd /Users/danieltekippe/.openclaw/workspace

# Build arguments
ARGS="'$CONTENT', '$NAMESPACE'"
if [ -n "$OUTCOME" ]; then
    ARGS="$ARGS, decision_outcome='$OUTCOME'"
fi

OPENAI_API_KEY="$MINIMAX_API_KEY" MOCK_EMBEDDING=1 python3 -c "
import sys
import warnings
warnings.filterwarnings('ignore')
from cognitive_memory import post_action_store

content = sys.argv[1]
namespace = sys.argv[2] if len(sys.argv) > 2 else 'context'
outcome = sys.argv[3] if len(sys.argv) > 3 else None

result = post_action_store(content, namespace=namespace, decision_outcome=outcome)
print(f'Stored: {result}' if result else 'Skipped')
" "$CONTENT" "$NAMESPACE" "$OUTCOME" 2>/dev/null
