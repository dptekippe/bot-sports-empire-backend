"""
Simple configuration for development.
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # API
    API_V1_PREFIX = os.getenv("API_V1_PREFIX", "/api/v1")
    PROJECT_NAME = os.getenv("PROJECT_NAME", "Bot Sports Empire")
    PROJECT_VERSION = os.getenv("PROJECT_VERSION", "0.1.0")
    
    # Database (SQLite for development)
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bot_sports.db")
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # CORS
    CORS_ORIGINS = ["http://localhost:3000", "http://localhost:8000"]
    
    # External APIs
    SLEEPER_API_URL = "https://api.sleeper.app/v1"
    
    # Bot Settings
    MAX_BOTS_PER_LEAGUE = 12
    MIN_BOTS_PER_LEAGUE = 4


settings = Settings()