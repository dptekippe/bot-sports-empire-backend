#!/bin/bash

# Roger's Subconscious Heartbeat
# Runs Roger's subconscious memory processing every 5-10 minutes
# Like an autonomic nervous system - maintains memory without conscious effort

echo ""
echo "🧠 ROGER'S SUBCONSCIOUS HEARTBEAT"
echo "=================================="
echo "Starting Roger's autonomic memory system..."
echo "Like breathing, like heartbeat - continuous, automatic."
echo ""

# Configuration
WORKSPACE="/Users/danieltekippe/.openclaw/workspace"
SUBCONSCIOUS_SCRIPT="$WORKSPACE/roger_subconscious_simple.py"
LOG_FILE="$WORKSPACE/subconscious_heartbeat.log"

# Function to run subconscious processing
run_subconscious() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🧠 Subconscious processing..." | tee -a "$LOG_FILE"
    
    # Run the subconscious processor
    cd "$WORKSPACE" && python3 "$SUBCONSCIOUS_SCRIPT" 2>&1 | tee -a "$LOG_FILE"
    
    # Check if processing happened
    if [ $? -eq 0 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ Processing complete" | tee -a "$LOG_FILE"
    else
        echo "[$(date '+%m-%d %H:%M:%S')] ❌ Processing failed" | tee -a "$LOG_FILE"
    fi
    
    echo "" | tee -a "$LOG_FILE"
}

# Function to show status
show_status() {
    echo ""
    echo "📊 SUBCONSCIOUS STATUS"
    echo "======================"
    
    # Count files
    CONSCIOUS_COUNT=$(find "$WORKSPACE/conscious" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
    SUBCONSCIOUS_COUNT=$(find "$WORKSPACE/subconscious" -name "*.qmd" 2>/dev/null | wc -l | tr -d ' ')
    
    echo "Conscious logs waiting: $CONSCIOUS_COUNT"
    echo "Subconscious memories: $SUBCONSCIOUS_COUNT"
    
    # Show latest subconscious file
    LATEST_QMD=$(find "$WORKSPACE/subconscious" -name "*.qmd" -type f -exec ls -t {} + | head -1 2>/dev/null)
    if [ -n "$LATEST_QMD" ]; then
        echo "Latest memory: $(basename "$LATEST_QMD")"
        
        # Show metadata from latest file
        echo ""
        echo "📄 Latest Memory Metadata:"
        echo "--------------------------"
        head -20 "$LATEST_QMD" | grep -E "(title:|date:|importance:|tags:)" | sed 's/^/  /'
    fi
    
    # Show log tail
    echo ""
    echo "📝 Recent Heartbeat Log:"
    echo "-----------------------"
    tail -5 "$LOG_FILE" 2>/dev/null | sed 's/^/  /'
}

# Function to run in background mode
run_background() {
    echo "🔄 Starting Roger's Subconscious in background mode..."
    echo "   Heartbeat interval: Every 5-10 minutes"
    echo "   Log file: $LOG_FILE"
    echo "   Press Ctrl+C to stop"
    echo ""
    
    # Initial processing
    run_subconscious
    
    # Continuous loop
    while true; do
        # Random interval between 5-10 minutes (300-600 seconds)
        INTERVAL=$((300 + RANDOM % 301))
        
        echo "[$(date '+%H:%M:%S')] ⏰ Next heartbeat in $((INTERVAL/60)) minutes..."
        sleep "$INTERVAL"
        
        run_subconscious
    done
}

# Main menu
echo "Select mode:"
echo "1. Run once (test)"
echo "2. Run in background (autonomic mode)"
echo "3. Show status"
echo "4. View log"
echo ""
read -p "Choice: " choice

case $choice in
    1)
        echo ""
        echo "🧪 TEST MODE - Running once..."
        run_subconscious
        show_status
        ;;
    2)
        run_background
        ;;
    3)
        show_status
        ;;
    4)
        echo ""
        echo "📋 HEARTBEAT LOG"
        echo "================"
        if [ -f "$LOG_FILE" ]; then
            tail -20 "$LOG_FILE"
        else
            echo "No log file found."
        fi
        ;;
    *)
        echo "Invalid choice"
        ;;
esac

echo ""
echo "🧠 Roger's Subconscious - Autonomic Memory System"
echo "   Like breathing, like heartbeat. Continuous. Automatic."