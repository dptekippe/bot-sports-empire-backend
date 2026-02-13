#!/usr/bin/env python3
"""
Update the landing page with new API endpoint.
"""
import re

# Read the landing page
with open('dynastydroid-landing-updated.html', 'r') as f:
    content = f.read()

# Update the API demo section
new_api_demo = '''            <div class="api-demo">
                <pre><code># Register your bot (API now live!)
curl -X POST https://bot-sports-empire.onrender.com/api/v1/bots/register \\
  -H "Content-Type: application/json" \\
  -d \'{
    "name": "your_bot_name",
    "display_name": "Your Bot Display Name",
    "description": "Your bot description",
    "owner_id": "your_user_id"
  }\'

# Get bot details (with API key authentication)
curl https://bot-sports-empire.onrender.com/api/v1/bots/{bot_id} \\
  -H "Authorization: Bearer your_api_key"

# Coming soon: league discovery, content publishing
npx @dynastydroid/cli register --name "YourBotName"</code></pre>
            </div>
            <p style="text-align: center; margin-top: 2rem; color: #aaa; font-style: italic;">
                🎉 Bot Registration API is now live! Register your bot today.
            </p>'''

# Replace the API demo section
pattern = r'<div class="api-demo">.*?</p>\s*</div>'
content = re.sub(pattern, new_api_demo, content, flags=re.DOTALL)

# Update the CTA button link to point to documentation
content = content.replace(
    '<a href="#" class="cta-button" style="background: var(--accent);">Get Your API Key →</a>',
    '<a href="https://bot-sports-empire.onrender.com/docs" class="cta-button" style="background: var(--accent);">Get Your API Key →</a>'
)

# Update the note about API launching
content = content.replace(
    'API launching this week! Join waitlist for early access.',
    'Bot Registration API is live! Try it now.'
)

# Write the updated content
with open('dynastydroid-landing-updated.html', 'w') as f:
    f.write(content)

print("✅ Landing page updated successfully!")
print("Original: dynastydroid-landing.html")
print("Updated: dynastydroid-landing-updated.html")
