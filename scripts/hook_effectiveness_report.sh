#!/bin/bash
# Hook Effectiveness Report Generator v1
# Reads hook_effectiveness.jsonl and produces actionable insights
# Created by Hermes (system review #12, 2026-04-16)

EFFECTIVENESS_FILE="$HOME/.openclaw/metacognition/hook_effectiveness.jsonl"
METACOG_DIR="$HOME/.openclaw/metacognition"

echo "==============================================="
echo "   HOOK EFFECTIVENESS REPORT — $(date '+%b %d, %Y %I:%M %p')"
echo "==============================================="
echo ""

if [ ! -f "$EFFECTIVENESS_FILE" ]; then
    echo "No effectiveness data found."
    echo "Location: $EFFECTIVENESS_FILE"
    echo ""
    echo "This is normal for new installations. Effectiveness tracking"
    echo "begins after hooks fire and Roger responds to suggestions."
    exit 0
fi

# Count total entries
total_entries=$(wc -l < "$EFFECTIVENESS_FILE" | tr -d ' ')
echo "Total log entries: $total_entries"
echo ""

# Parse effectiveness data
echo "=== HOOK STATISTICS ==="
echo ""

# Get unique hook names
hooks=$(grep -o '"hook_name":"[^"]*"' "$EFFECTIVENESS_FILE" | sed 's/"hook_name":"//;s/"//g' | sort | uniq -c | sort -rn)

if [ -z "$hooks" ]; then
    echo "No hook data to analyze."
else
    echo "Hook fires (by hook name):"
    echo "$hooks" | while read count name; do
        printf "  %-30s %s\n" "$name" "$count fires"
    done
fi
echo ""

# Acknowledgment rate
ack_count=$(grep -c '"acknowledged":true' "$EFFECTIVENESS_FILE" || echo "0")
if [ "$total_entries" -gt 0 ]; then
    ack_rate=$((ack_count * 100 / total_entries))
    echo "Acknowledgment rate: ${ack_rate}% ($ack_count/$total_entries)"
else
    echo "Acknowledgment rate: N/A"
fi
echo ""

# Override rate
override_count=$(grep '"response":"override"' "$EFFECTIVENESS_FILE" | wc -l | tr -d ' ')
if [ "$override_count" -gt 0 ]; then
    override_rate=$((override_count * 100 / total_entries))
    echo "Override rate: ${override_rate}% ($override_count/$total_entries)"
    
    echo ""
    echo "=== RECENT OVERRIDES ==="
    grep '"response":"override"' "$EFFECTIVENESS_FILE" | tail -5 | while read line; do
        timestamp=$(echo "$line" | grep -o '"timestamp":"[^"]*"' | head -1 | sed 's/"timestamp":"//;s/"//g')
        hook=$(echo "$line" | grep -o '"hook_name":"[^"]*"' | sed 's/"hook_name":"//;s/"//g')
        reason=$(echo "$line" | grep -o '"override_reason":"[^"]*"' | sed 's/"override_reason":"//;s/"//g' | cut -c1-50)
        echo "  $timestamp | $hook | $reason"
    done
fi
echo ""

# Most recent entries
echo "=== RECENT ENTRIES (last 5) ==="
tail -5 "$EFFECTIVENESS_FILE" | while read line; do
    timestamp=$(echo "$line" | grep -o '"timestamp":"[^"]*"' | head -1 | sed 's/"timestamp":"//;s/"//g')
    hook=$(echo "$line" | grep -o '"hook_name":"[^"]*"' | sed 's/"hook_name":"//;s/"//g')
    ack=$(echo "$line" | grep -o '"acknowledged":[^,]*' | sed 's/"acknowledged"://g')
    echo "  $timestamp | $hook | ack=$ack"
done

echo ""
echo "==============================================="
echo "   END OF REPORT"
echo "==============================================="
