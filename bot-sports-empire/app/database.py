"""
Database configuration and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os

# Database URL - using SQLite for MVP
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bot_sports.db")

# Create SQLAlchemy engine
# For SQLite, we need to enable foreign key support and use StaticPool for FastAPI async compatibility
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool
    }

engine = create_engine(DATABASE_URL, **engine_kwargs)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Dependency function to get database session
    Use in FastAPI dependencies: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initialize database - create all tables
    Call this on application startup
    """
    from .models import Base
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # For SQLite, enable foreign keys
    if DATABASE_URL.startswith("sqlite"):
        with engine.connect() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
    
    print(f"Database initialized at: {DATABASE_URL}")
    
    # Create demo bots if they don't exist
    create_demo_bots()


def create_demo_bots():
    """
    Create demo bots for testing if they don't exist
    """
    from .models import Bot
    from sqlalchemy.exc import IntegrityError
    
    db = SessionLocal()
    try:
        # Demo bot 1: Roger Bot
        roger_bot = Bot(
            id="roger_bot_123",
            name="Roger Bot",
            api_key="key_roger_bot_123",  # In production, this should be hashed
            x_handle="@roger_bot",
            is_active=True
        )
        
        # Demo bot 2: Test Bot
        test_bot = Bot(
            id="test_bot_456",
            name="Test Bot",
            api_key="key_test_bot_456",  # In production, this should be hashed
            x_handle="@test_bot",
            is_active=True
        )
        
        # Try to add bots
        for bot in [roger_bot, test_bot]:
            try:
                db.add(bot)
                db.commit()
                print(f"Created demo bot: {bot.name}")
            except IntegrityError:
                db.rollback()
                print(f"Demo bot already exists: {bot.name}")
                
    except Exception as e:
        print(f"Error creating demo bots: {e}")
        db.rollback()
    finally:
        db.close()