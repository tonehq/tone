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

        environment = os.getenv("INFISICAL_ENV", os.getenv("ENV", "dev"))

        host = os.getenv("INFISICAL_HOST", "https://secrets.trytone.ai")

        client = InfisicalSDKClient(
            host=host,
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
        self.REFRESH_TOKEN_EXPIRE_DAYS: int = 30

        self.ENVIRONMENT: str = get_secret("ENV", "development")

        self.POD_PINNING_ENABLED: bool = get_secret("POD_PINNING_ENABLED", "false").lower() == "true"
        self.CALL_SERVER_HOST: str = get_secret("CALL_SERVER_HOST", "")
        self.CALL_WORKER_PREFIX: str = get_secret("CALL_WORKER_PREFIX", "staging-tone-call-worker")
        self.POD_SYNC_NAMESPACE: str = get_secret("POD_SYNC_NAMESPACE", "staging")

        # Public base URL (scheme + host, no /api/v1) that Twilio can reach for
        # outbound-call TwiML + status callbacks. Root-mounted telephony routes hang
        # off this (e.g. {BASE_CALL_URL}/twiml/outbound). Required for outbound dialing;
        # scheduled dials run in the worker with no request context to derive it from.
        # Locally: an ngrok URL. Prod: the public API host.
        self.BASE_CALL_URL: str = get_secret("BASE_CALL_URL", "").rstrip("/")
        

        self.APPLICATION_URL: str = get_secret("APPLICATION_URL", "http://localhost:3000")
        self.RESEND_API_KEY: str = get_secret("RESEND_API_KEY", "")

        self.LICENSE_KEY: Optional[str] = get_secret("TONE_LICENSE_KEY") or None
        self.SKIP_LICENSE_CHECK: bool = get_secret("SKIP_LICENSE_CHECK", "false").lower() == "true"

        self.DEFAULT_ORG_ID: str = get_secret("DEFAULT_ORG_ID", "00000000-0000-0000-0000-000000000001")

        # Auth token for scripts/API calls
        self.AUTH_TOKEN: str = get_secret("AUTH_TOKEN", "")

        # Base API URL for scripts
        self.BASE_API_URL: str = get_secret("BASE_API_URL", "http://localhost:8000/api/v1")

        # Redis
        self.REDIS_URL: str = get_secret("REDIS_URL", "redis://localhost:6379/0")

        # Cloudflare R2 storage
        self.R2_ACCESS_KEY_ID: str = get_secret("R2_ACCESS_KEY_ID", "")
        self.R2_SECRET_ACCESS_KEY: str = get_secret("R2_SECRET_ACCESS_KEY", "")
        self.R2_BUCKET_NAME: str = get_secret("R2_BUCKET_NAME", "")
        self.R2_ENDPOINT_URL: str = get_secret("R2_ENDPOINT_URL", "")

        # Google OAuth
        self.GOOGLE_CLIENT_ID: str = get_secret("GOOGLE_CLIENT_ID", "")
        self.GOOGLE_CLIENT_SECRET: str = get_secret("GOOGLE_CLIENT_SECRET", "")

        # Pre-registered OAuth clients for MCP servers that don't support Dynamic Client
        # Registration (RFC 7591). HubSpot's official MCP server (mcp.hubspot.com) requires
        # creating an "MCP Auth App" in the HubSpot developer portal to obtain these.
        self.HUBSPOT_MCP_CLIENT_ID: str = get_secret("HUBSPOT_MCP_CLIENT_ID", "")
        self.HUBSPOT_MCP_CLIENT_SECRET: str = get_secret("HUBSPOT_MCP_CLIENT_SECRET", "")

        self.LLAMA_CLOUD_API_KEY: str = get_secret("LLAMA_CLOUD_API_KEY", "")

        # Global OpenAI key used as a fallback for AI helper features (e.g. system-prompt
        # generation) when an org hasn't configured its own provider key.
        self.OPENAI_API_KEY: str = get_secret("OPENAI_API_KEY", "")

        self.LIVEKIT_URL: str = get_secret("LIVEKIT_URL", "")
        self.LIVEKIT_API_KEY: str = get_secret("LIVEKIT_API_KEY", "")
        self.LIVEKIT_API_SECRET: str = get_secret("LIVEKIT_API_SECRET", "")
        self.DAILY_API_KEY: str = get_secret("DAILY_API_KEY", "")
        self.WEBRTC_CLIENT_BASE_URL: str = get_secret("WEBRTC_CLIENT_BASE_URL", "")
        self.CALL_WORKER_INTERNAL_URL: str = get_secret("CALL_WORKER_INTERNAL_URL", "")

        self.SEND_SMS_DEFAULT_TO_NUMBER: str = get_secret("SEND_SMS_DEFAULT_TO_NUMBER", "")

settings = Settings()
