import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.DATABASE_URL: str = os.getenv("CE_DATABASE_URL", os.getenv("DATABASE_URL", ""))

        self.JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
        self.JWT_ALGORITHM: str = "HS256"
        self.ACCESS_TOKEN_EXPIRE_HOURS: int = 24

        self.ENVIRONMENT: str = os.getenv("ENV", "development")
        self.FIREBASE_PROJECT_ID: Optional[str] = os.getenv("FIREBASE_PROJECT_ID")

        self.APPLICATION_URL: str = os.getenv("APPLICATION_URL", "http://localhost:3000")
        self.RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "re_SMutgeWp_3aVdrY5NmdVztr7TVvv6MQB2")

        self.IS_MULTI_TENANT: bool = False
        self.DEFAULT_ORG_ID: str = os.getenv("DEFAULT_ORG_ID", "00000000-0000-0000-0000-000000000001")


settings = Settings()
