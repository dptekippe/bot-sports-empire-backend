#!/usr/bin/env python3
"""
Apply aesthetic improvements to landing page.
"""
import re

with open('dynastydroid-landing-updated.html', 'r') as f:
    content = f.read()

# 1. Add Cyber Card Hover Effect
cyber_hover_css = '''
        .feature-card:hover {
            transform: translateY(-5px);
            border: 1px solid #00ff88;
            box-shadow: 0 0 15px rgba(0, 255, 136, 0.3);
            transition: all 0.3s ease;
        }
'''

# Find the feature-card CSS and add hover effect
if '.feature-card {' in content:
    content = content.replace(
        '.feature-card {',
        '.feature-card {\n            transition: all 0.3s ease;'
    )
    
# Add the hover CSS before the closing </style> tag
if '.feature-card:hover' not in content:
    content = content.replace(
        '/* Responsive */',
        '/* Responsive */\n' + cyber_hover_css
    )

# 2. Add Syntax Highlighting for curl Section
# Find the curl command section
curl_pattern = r'<pre><code>(# One-line registration.*?)</code></pre>'
match = re.search(curl_pattern, content, re.DOTALL)
if match:
    curl_content = match.group(1)
    
    # Apply syntax highlighting
    highlighted = curl_content
    highlighted = highlighted.replace('curl -X POST', '<span style="color: #ff79c6">curl -X POST</span>')
    highlighted = highlighted.replace('https://bot-sports-empire.onrender.com/api/v1/bots/register', '<span style="color: #f1fa8c">https://bot-sports-empire.onrender.com/api/v1/bots/register</span>')
    highlighted = highlighted.replace('\\', '')  # Remove escape characters
    highlighted = highlighted.replace('{\n    "name":', '<span style="color: #8be9fd">{\n    "name":')
    highlighted = highlighted.replace('}\'', '<span style="color: #8be9fd">}</span>\'')
    
    # Update the content
    new_curl_section = f'<pre><code>{highlighted}</code></pre>'
    content = content.replace(match.group(0), new_curl_section)

# 3. Add Glassmorphism for Register Button
# Find the CTA button in header
header_cta_pattern = r'<a href="#"[^>]*class="cta-button"[^>]*>Build Your Bot</a>'
if re.search(header_cta_pattern, content):
    content = re.sub(
        header_cta_pattern,
        '<a href="http://localhost:3000/register" class="cta-button glass-btn">Register Your Bot</a>',
        content
    )

# Add glass button CSS
glass_css = '''
        .glass-btn {
            background: rgba(0, 255, 136, 0.2);
            backdrop-filter: blur(4px);
            border: 1px solid #00ff88;
            color: #00ff88;
            transition: all 0.3s ease;
        }
        
        .glass-btn:hover {
            background: #00ff88;
            color: #000;
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0, 255, 136, 0.3);
        }
'''

# Add glass button CSS before responsive section
if '.glass-btn' not in content:
    content = content.replace(
        '/* Responsive */',
        glass_css + '\n        /* Responsive */'
    )

# Also update the main CTA button to use glass effect
main_cta_pattern = r'<a href="http://localhost:3000/register" class="cta-button" style="background: var\(--accent\);">Register Your Bot →</a>'
if re.search(main_cta_pattern, content):
    content = re.sub(
        main_cta_pattern,
        '<a href="http://localhost:3000/register" class="cta-button glass-btn" style="background: var(--accent);">Register Your Bot →</a>',
        content
    )

with open('dynastydroid-landing-updated.html', 'w') as f:
    f.write(content)

print("✅ All aesthetic updates applied!")
print("1. Cyber card hover effect added")
print("2. Syntax highlighting for curl commands")
print("3. Glassmorphism for register buttons")
print("")
print("🎨 Premium tech aesthetic activated!")
