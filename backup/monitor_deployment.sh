#!/bin/bash
echo "Monitoring Render deployment..."
echo "Current version:"
curl -s https://bot-sports-empire.onrender.com/ | grep -o '"version":"[^"]*"'
echo ""
echo "Checking bot registration endpoint:"
curl -s -X POST https://bot-sports-empire.onrender.com/api/v1/bots/register -H "Content-Type: application/json" -d '{"name":"test","email":"test@example.com"}' | head -5
echo ""
echo "Deployment should complete within 5-10 minutes."