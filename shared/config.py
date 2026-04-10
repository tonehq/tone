import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


def get_infisical_secrets() -> dict:
    token = os.getenv("INFISICAL_TOKEN")
    project_id = os.getenv("INFISICAL_PROJECT_ID")

    if not token or not project_id:
        return {}

    try:
        from infisical_sdk import InfisicalSDKClient

        environment = os.getenv("INFISICAL_ENV", "dev")

        client = InfisicalSDKClient(
            host="https://app.infisical.com",
            token=token
        )

        secrets_response = client.secrets.list_secrets(
            project_id=project_id,
            environment_slug=environment,
            secret_path="/"
        )

        secrets = {}
        for secret in secrets_response.secrets:
            secrets[secret.secretKey] = secret.secretValue

        return secrets

    except Exception:
        return {}


class Settings:
    def __init__(self):
        infisical_secrets = get_infisical_secrets()

        def get_secret(key: str, default: str = "") -> str:
            return infisical_secrets.get(key) or os.getenv(key, default)

        self.DATABASE_URL: str = get_secret("DATABASE_URL")
        self.JWT_SECRET_KEY: str = get_secret("JWT_SECRET_KEY", "your-secret-key-here")
        self.JWT_ALGORITHM: str = "HS256"
        self.ACCESS_TOKEN_EXPIRE_HOURS: int = 24

        self.ENVIRONMENT: str = get_secret("ENV", "development")

        self.APPLICATION_URL: str = get_secret("APPLICATION_URL", "http://localhost:3000")
        self.RESEND_API_KEY: str = get_secret("RESEND_API_KEY", "")

        self.LICENSE_KEY: Optional[str] = get_secret("TONE_LICENSE_KEY") or None
        self.SKIP_LICENSE_CHECK: bool = get_secret("SKIP_LICENSE_CHECK", "false").lower() == "true"

        self.DEFAULT_ORG_ID: str = get_secret("DEFAULT_ORG_ID", "00000000-0000-0000-0000-000000000001")

        # Auth token for scripts/API calls
        self.AUTH_TOKEN: str = get_secret("AUTH_TOKEN", "")

        # Redis
        self.REDIS_URL: str = get_secret("REDIS_URL", "redis://localhost:6379/0")

        # Cloudflare R2 storage
        self.R2_ACCESS_KEY_ID: str = get_secret("R2_ACCESS_KEY_ID", "")
        self.R2_SECRET_ACCESS_KEY: str = get_secret("R2_SECRET_ACCESS_KEY", "")
        self.R2_BUCKET_NAME: str = get_secret("R2_BUCKET_NAME", "")
        self.R2_ENDPOINT_URL: str = get_secret("R2_ENDPOINT_URL", "")


settings = Settings()
