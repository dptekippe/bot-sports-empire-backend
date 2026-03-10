import re

with open('app/api/endpoints/leagues.py', 'r') as f:
    content = f.read()

# Find and replace the status and league_type lines
# Look for the pattern: 'status': league.status.value if hasattr(league.status, 'value') else str(league.status),
content = content.replace(
    "'status': league.status.value if hasattr(league.status, 'value') else str(league.status),",
    "'status': str(league.status).upper(),"
)

# Also fix league_type
content = content.replace(
    "'league_type': league.league_type.value if hasattr(league.league_type, 'value') else str(league.league_type),",
    "'league_type': str(league.league_type).upper(),"
)

with open('app/api/endpoints/leagues.py', 'w') as f:
    f.write(content)

print("✅ Applied uppercase conversion fix!")
