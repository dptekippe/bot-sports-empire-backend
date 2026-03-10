#!/bin/bash
echo "=== Continuous Render Deployment Monitor ==="
echo "Monitoring: https://bot-sports-empire.onrender.com"
echo "Push completed at: $(date)"
echo ""
echo "Waiting 30 seconds for build to start..."
sleep 30

for i in {1..30}; do
    echo ""
    echo "=== Check #$i at $(date) ==="
    
    # Check if service is responding
    echo "Checking service status..."
    if curl -s --max-time 10 https://bot-sports-empire.onrender.com/health > /dev/null; then
        echo "✓ Service is responding"
        
        # Check version
        echo "Checking version..."
        VERSION=$(curl -s --max-time 10 https://bot-sports-empire.onrender.com/ | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
        if [ -n "$VERSION" ]; then
            echo "✓ Version: $VERSION"
            
            # Test bot registration endpoint
            echo "Testing bot registration endpoint..."
            RESPONSE=$(curl -s --max-time 10 -X POST https://bot-sports-empire.onrender.com/api/v1/bots/register \
                -H "Content-Type: application/json" \
                -d '{"name":"test_monitor_'$(date +%s)'","display_name":"Test Monitor","description":"Test bot from monitor","personality":"balanced","owner_id":"monitor"}' | head -3)
            
            if echo "$RESPONSE" | grep -q "success"; then
                echo "✓ Bot registration endpoint working!"
                echo "✅ DEPLOYMENT SUCCESSFUL!"
                exit 0
            elif echo "$RESPONSE" | grep -q "detail"; then
                echo "⚠ Endpoint exists but returned error: $RESPONSE"
            else
                echo "✗ Bot registration endpoint not working (no response or timeout)"
            fi
        else
            echo "✗ Could not determine version"
        fi
    else
        echo "✗ Service not responding (build might be in progress)"
    fi
    
    echo "Waiting 30 seconds before next check..."
    sleep 30
done

echo ""
echo "❌ DEPLOYMENT MONITOR TIMEOUT - Build may have failed"
echo "Check Render dashboard for build logs"
exit 1