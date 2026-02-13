#!/bin/bash
# Deployment script for Bot Sports Empire to Render

echo "🚀 Deploying Bot Sports Empire to Render..."

# Check if render.yaml exists
if [ ! -f "render.yaml" ]; then
    echo "❌ render.yaml not found. Creating from updated version..."
    cp render_updated.yaml render.yaml
fi

# Check if we're in the right directory
if [ ! -f "requirements-deploy.txt" ]; then
    echo "❌ requirements-deploy.txt not found!"
    exit 1
fi

# Check if app/main.py exists
if [ ! -f "app/main.py" ]; then
    echo "❌ app/main.py not found!"
    exit 1
fi

echo "✅ All files check out."

# Instructions for manual deployment
echo ""
echo "📋 Manual Deployment Steps:"
echo "1. Go to https://dashboard.render.com"
echo "2. Select 'bot-sports-empire' service"
echo "3. Click 'Manual Deploy'"
echo "4. Select 'Deploy latest commit'"
echo ""
echo "📋 Or deploy via CLI (if render-cli is installed):"
echo "   render deploy"
echo ""
echo "📋 After deployment, test the new endpoints:"
echo "   curl https://bot-sports-empire.onrender.com/api/v1/bots/register \\"
echo "     -X POST \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"name\":\"test_bot\",\"display_name\":\"Test Bot\",\"description\":\"Test\"}'"
echo ""
echo "🎯 Don't forget to update the landing page to reference:"
echo "   POST https://bot-sports-empire.onrender.com/api/v1/bots/register"
echo "   (Will be api.dynastydroid.com after domain move)"
