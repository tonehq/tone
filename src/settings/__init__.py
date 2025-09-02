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
        
        # Email configuration (if needed)
        self.SMTP_HOST = os.getenv("SMTP_HOST")
        self.SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USERNAME = os.getenv("SMTP_USERNAME")
        self.SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
        
        # Firebase configuration (if needed)
        self.FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")

settings = Settings()