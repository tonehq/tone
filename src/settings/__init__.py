import os
from typing import Optional
from dotenv import load_dotenv

def load_config():
    """Load environment variables from .env file"""
    load_dotenv()
    print("Environment variables loaded from .env file")

class Settings:
    def __init__(self):
        # Load environment variables first
        load_config()
        # Database configuration
        self.DATABASE_URL = os.getenv(
            "DATABASE_URL", 
            "postgresql://user:password@localhost:5432/tone_db"
        )
        
        # JWT configuration
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
        self.JWT_ALGORITHM = "HS256"
        self.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        
        # Environment
        self.ENVIRONMENT = os.getenv("ENV", "development")
        self.FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")

settings = Settings()