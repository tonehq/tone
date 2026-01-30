import os
from typing import Optional
from dotenv import load_dotenv
import traceback
load_dotenv()


def get_infisical_secrets() -> dict:
    """Fetch secrets from Infisical"""
    
    # Check if we should use Infisical (based on environment)
    use_infisical = os.getenv("USE_INFISICAL", "true").lower() == "true"
    
    if not use_infisical:
        return {}
    
    try:
        from infisical_sdk import InfisicalSDKClient

        client = InfisicalSDKClient(
            host=os.getenv("INFISICAL_SITE_URL", "https://app.infisical.com"),
            token=os.getenv("INFISICAL_TOKEN"),
        )

        project_id = os.getenv("INFISICAL_PROJECT_ID")
        environment = os.getenv("INFISICAL_ENV", os.getenv("ENV", "dev"))

        secrets_response = client.secrets.list_secrets(
            project_id=project_id,
            environment_slug=environment,
            secret_path="/",
        )
        print(f"Fetched secrets from Infisical")

        secrets = {}
        for secret in secrets_response.secrets:
            secrets[secret.secretKey] = secret.secretValue
        print(f"Infisical secrets keys: {list(secrets.keys())}")
        return secrets
        
    except Exception as e:
        print(traceback.format_exc())
        print(f"Warning: Failed to fetch secrets from Infisical: {e}")
        return {}


class Settings:
    def __init__(self):
        # Fetch secrets from Infisical
        infisical_secrets = get_infisical_secrets()
        
        # Helper to get value from Infisical first, then env, then default
        def get_secret(key: str, default: str = "") -> str:
            print(f"Fetching secret for key: {key}")
            print(f"Infisical secrets available: {list(infisical_secrets.keys())}")
            return infisical_secrets.get(key) or os.getenv(key, default)
        
        self.DATABASE_URL: str = get_secret("CE_DATABASE_URL", get_secret("DATABASE_URL", ""))
        self.JWT_SECRET_KEY: str = get_secret("JWT_SECRET_KEY", "your-secret-key-here")
        self.JWT_ALGORITHM: str = "HS256"
        self.ACCESS_TOKEN_EXPIRE_HOURS: int = 24
        
        self.ENVIRONMENT: str = get_secret("ENV", "development")
        self.FIREBASE_PROJECT_ID: Optional[str] = get_secret("FIREBASE_PROJECT_ID") or None
        
        self.APPLICATION_URL: str = get_secret("APPLICATION_URL", "http://localhost:3000")
        self.RESEND_API_KEY: str = get_secret("RESEND_API_KEY", "")
        
        self.IS_MULTI_TENANT: bool = False
        self.DEFAULT_ORG_ID: str = get_secret("DEFAULT_ORG_ID", "00000000-0000-0000-0000-000000000001")


settings = Settings()