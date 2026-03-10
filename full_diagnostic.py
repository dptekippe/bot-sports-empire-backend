import sys
import os
sys.path.append(os.getcwd())

print("=== FULL DIAGNOSTIC ===")

# 1. Check the schemas file
print("\n1. Checking schemas/league.py...")
try:
    with open('app/schemas/league.py', 'r') as f:
        content = f.read()
        if '_missing_' in content:
            print("✅ Found _missing_ method (case-insensitive enum)")
        else:
            print("❌ No _missing_ method found")
        if 'validate_status' in content:
            print("✅ Found validate_status validator")
        else:
            print("❌ No validate_status validator found")
except Exception as e:
    print(f"❌ Error reading schemas: {e}")

# 2. Check the endpoints file
print("\n2. Checking endpoints/leagues.py...")
try:
    with open('app/api/endpoints/leagues.py', 'r') as f:
        content = f.read()
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'league.status' in line:
                print(f"   Line {i+1}: {line.strip()}")
except Exception as e:
    print(f"❌ Error reading endpoints: {e}")

# 3. Test the actual conversion
print("\n3. Testing actual SQLAlchemy data...")
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.league import League
    
    DATABASE_URL = "sqlite:///./bot_sports.db"
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    league = db.query(League).first()
    
    print(f"   First league ID: {league.id}")
    print(f"   First league name: {league.name}")
    print(f"   league.status type: {type(league.status)}")
    print(f"   league.status value: {repr(league.status)}")
    
    # Test the conversion that should happen
    status_str = str(league.status)
    print(f"   str(league.status): {status_str}")
    print(f"   str(league.status).upper(): {status_str.upper()}")
    
    db.close()
except Exception as e:
    print(f"❌ Error testing data: {e}")

print("\n=== DIAGNOSTIC COMPLETE ===")
