#!/bin/bash
echo "=== FINAL DEPLOYMENT MONITOR ==="
echo "Monitoring: https://bot-sports-empire.onrender.com"
echo "Ultra minimal deployment pushed at: $(date)"
echo "Version should be: 5.0.0"
echo "Bot registration endpoint: POST /api/v1/bots/register"
echo ""
echo "This will monitor for 10 minutes (20 checks)"
echo ""

for i in {1..20}; do
    echo ""
    echo "=== Check #$i at $(date) ==="
    
    # Check root endpoint for version
    echo "Checking version..."
    ROOT_RESPONSE=$(curl -s --max-time 10 https://bot-sports-empire.onrender.com/)
    if echo "$ROOT_RESPONSE" | grep -q '"version":"5.0.0"'; then
        echo "✅ VERSION 5.0.0 DETECTED!"
        
        # Test bot registration endpoint
        echo "Testing bot registration endpoint..."
        TEST_NAME="test_$(date +%s)"
        REGISTER_RESPONSE=$(curl -s --max-time 10 -X POST https://bot-sports-empire.onrender.com/api/v1/bots/register \
            -H "Content-Type: application/json" \
            -d "{\"name\":\"$TEST_NAME\",\"display_name\":\"Test Bot\",\"description\":\"Test from monitor\",\"personality\":\"balanced\",\"owner_id\":\"monitor\"}")
        
        if echo "$REGISTER_RESPONSE" | grep -q '"success":true'; then
            echo "✅ BOT REGISTRATION ENDPOINT WORKING!"
            echo "✅ DEPLOYMENT COMPLETE AND SUCCESSFUL!"
            echo ""
            echo "Response: $REGISTER_RESPONSE"
            exit 0
        else
            echo "⚠ Version 5.0.0 but registration failed:"
            echo "Response: $REGISTER_RESPONSE"
        fi
    elif echo "$ROOT_RESPONSE" | grep -q '"version":"'; then
        VERSION=$(echo "$ROOT_RESPONSE" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
        echo "Current version: $VERSION (waiting for 5.0.0)"
    else
        echo "⚠ Could not determine version (service might be building)"
    fi
    
    # Check health endpoint
    echo "Checking health endpoint..."
    HEALTH_RESPONSE=$(curl -s --max-time 10 https://bot-sports-empire.onrender.com/health 2>/dev/null || echo "DOWN")
    if [ "$HEALTH_RESPONSE" != "DOWN" ]; then
        echo "Health: $HEALTH_RESPONSE" | head -1
    else
        echo "Health endpoint down (build in progress)"
    fi
    
    echo "Waiting 30 seconds before next check..."
    sleep 30
done

echo ""
echo "❌ MONITOR TIMEOUT - Deployment may have failed"
echo "Current status:"
curl -s https://bot-sports-empire.onrender.com/ | grep -o '"version":"[^"]*"'
echo ""
echo "Bot registration test:"
curl -s -X POST https://bot-sports-empire.onrender.com/api/v1/bots/register \
    -H "Content-Type: application/json" \
    -d '{"name":"final_test","display_name":"Final Test","description":"Test"}' | head -3
exit 1