import os
from typing import Optional

class Settings:
    def __init__(self):
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