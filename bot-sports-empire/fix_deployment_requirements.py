#!/usr/bin/env python3
"""
Fix deployment requirements for Render.
Creates a deployment-specific requirements.txt that avoids pydantic-core build issues.
"""

import sys

# Deployment requirements that avoid build issues
DEPLOYMENT_REQUIREMENTS = """# Core (production only)
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Database (SQLite for Render free tier)
sqlalchemy==2.0.23
alembic==1.13.1

# Data (use compatible versions)
pydantic==2.5.0
pydantic-settings==2.1.0
httpx==0.25.1

# Utilities
python-dotenv==1.0.0

# Note: Removed problematic packages:
# - psycopg2-binary (not needed for SQLite)
# - asyncpg (not needed for SQLite)
# - aiohttp (httpx is sufficient)
# - redis/celery (not needed for MVP)
# - auth packages (not needed yet)
# - dev packages (black, isort, mypy, pytest)
"""

def main():
    print("🔧 Creating deployment requirements.txt...")
    
    # Write deployment requirements
    with open("requirements-deploy.txt", "w") as f:
        f.write(DEPLOYMENT_REQUIREMENTS)
    
    print("✅ Created requirements-deploy.txt")
    print("\n📋 Contents:")
    print(DEPLOYMENT_REQUIREMENTS)
    
    print("\n🎯 Next steps:")
    print("1. Update render.yaml to use requirements-deploy.txt:")
    print("   buildCommand: pip install -r requirements-deploy.txt")
    print("2. Or rename: cp requirements-deploy.txt requirements.txt")
    print("3. Test build locally: pip install -r requirements-deploy.txt")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())