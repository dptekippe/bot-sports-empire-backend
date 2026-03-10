#!/usr/bin/env python3
"""
Fix landing page CTA to go to registration, not API docs.
"""
import re

with open('dynastydroid-landing-updated.html', 'r') as f:
    content = f.read()

# Update the main CTA button to go to registration
content = content.replace(
    '<a href="https://bot-sports-empire.onrender.com/docs" class="cta-button" style="background: var(--accent);">Get Your API Key →</a>',
    '<a href="http://localhost:3000/register" class="cta-button" style="background: var(--accent);">Register Your Bot →</a>'
)

# Update the note below
content = content.replace(
    'No credit card required. Free forever for basic features.',
    'Get your API key in 30 seconds. No credit card required.'
)

with open('dynastydroid-landing-updated.html', 'w') as f:
    f.write(content)

print("✅ Landing page CTA updated to point to registration form")
print("   Old: Get Your API Key → (links to API docs)")
print("   New: Register Your Bot → (links to /register)")
