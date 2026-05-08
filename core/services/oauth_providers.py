from typing import Dict, Any, Optional
from core.config import settings

OAUTH_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "google_calendar": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": "https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/userinfo.email",
        "client_id": lambda: settings.GOOGLE_CLIENT_ID,
        "client_secret": lambda: settings.GOOGLE_CLIENT_SECRET,
    },
    "google_sheets": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": "https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/userinfo.email",
        "client_id": lambda: settings.GOOGLE_CLIENT_ID,
        "client_secret": lambda: settings.GOOGLE_CLIENT_SECRET,
    },
}


def get_provider_config(provider: str) -> Optional[Dict[str, Any]]:
    config = OAUTH_PROVIDERS.get(provider)
    if not config:
        return None
    return {
        "auth_url": config["auth_url"],
        "token_url": config["token_url"],
        "scopes": config["scopes"],
        "client_id": config["client_id"](),
        "client_secret": config["client_secret"](),
    }


def get_supported_providers() -> list:
    return list(OAUTH_PROVIDERS.keys())
