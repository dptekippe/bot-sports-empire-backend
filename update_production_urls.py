#!/usr/bin/env python3
"""
Update landing page URLs for production.
"""
import re

with open('dynastydroid-landing-updated.html', 'r') as f:
    content = f.read()

# Update dashboard URL to be relative (will be updated after deployment)
# For now, keep localhost but add comment
content = content.replace(
    'href="http://localhost:3000/register"',
    'href="/register"  <!-- Will be updated to production URL after deployment -->'
)

# Update the header CTA button too
header_cta_pattern = r'<a href="http://localhost:3000/register" class="cta-button glass-btn">Register Your Bot</a>'
if re.search(header_cta_pattern, content):
    content = re.sub(
        header_cta_pattern,
        '<a href="/register" class="cta-button glass-btn">Register Your Bot</a>',
        content
    )

with open('dynastydroid-landing-updated.html', 'w') as f:
    f.write(content)

print("✅ Landing page URLs updated for production")
print("   Changed: http://localhost:3000/register → /register")
print("   Note: Will update to actual production URL after deployment")
