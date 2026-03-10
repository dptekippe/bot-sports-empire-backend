with open('app/api/endpoints/leagues.py', 'r') as f:
    lines = f.readlines()

# Remove the stray \n line
new_lines = []
for line in lines:
    if line.strip() == '\\n':
        print("Found stray \\n line, removing...")
        continue  # Skip this line
    new_lines.append(line)

with open('app/api/endpoints/leagues.py', 'w') as f:
    f.writelines(new_lines)

print("✅ Fixed stray \\n line")
