from shared.config import settings


class EESettings:
    def __init__(self):
        self.DATABASE_URL: str = settings.DATABASE_URL
        self.JWT_SECRET_KEY: str = settings.JWT_SECRET_KEY
        self.JWT_ALGORITHM: str = settings.JWT_ALGORITHM
        self.ACCESS_TOKEN_EXPIRE_HOURS: int = settings.ACCESS_TOKEN_EXPIRE_HOURS
        self.ENVIRONMENT: str = settings.ENVIRONMENT
        self.APPLICATION_URL: str = settings.APPLICATION_URL
        self.RESEND_API_KEY: str = settings.RESEND_API_KEY
        self.IS_MULTI_TENANT: bool = True
        self.LICENSE_KEY: str = settings.LICENSE_KEY


ee_settings = EESettings()
