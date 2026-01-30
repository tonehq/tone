import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class EESettings:
    def __init__(self):
        self.DATABASE_URL: str = os.getenv("DATABASE_URL", "")

        self.JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
        self.JWT_ALGORITHM: str = "HS256"
        self.ACCESS_TOKEN_EXPIRE_HOURS: int = 24

        self.ENVIRONMENT: str = os.getenv("ENV", "development")
        self.FIREBASE_PROJECT_ID: Optional[str] = os.getenv("FIREBASE_PROJECT_ID")

        self.APPLICATION_URL: str = os.getenv("APPLICATION_URL", "http://localhost:3000")
        self.RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")

        self.IS_MULTI_TENANT: bool = True
        self.LICENSE_KEY: Optional[str] = os.getenv("EE_LICENSE_KEY")


ee_settings = EESettings()
