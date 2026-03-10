print("Fixing syntax error in leagues.py...")

with open('app/api/endpoints/leagues.py', 'r') as f:
    content = f.read()

# Fix the \\n issue - replace with actual newline
content = content.replace('\\\\n\\\\n', '\\n\\n')

with open('app/api/endpoints/leagues.py', 'w') as f:
    f.write(content)

print("✅ Fixed syntax error")
