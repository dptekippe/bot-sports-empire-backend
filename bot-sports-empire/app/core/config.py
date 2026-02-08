from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # API
    api_v1_prefix: str = "/api/v1"
    project_name: str = "Bot Sports Empire"
    project_version: str = "0.1.0"
    
    # Database
    database_url: str = "postgresql://user:password@localhost/bot_sports"
    database_test_url: str = "postgresql://user:password@localhost/bot_sports_test"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # Security
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    cors_origins: list = ["http://localhost:3000", "http://localhost:8000"]
    
    # External APIs
    sleeper_api_url: str = "https://api.sleeper.app/v1"
    
    # Bot Settings
    default_bot_api_key_length: int = 32
    max_bots_per_league: int = 12
    min_bots_per_league: int = 4
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()