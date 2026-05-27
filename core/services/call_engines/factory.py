from typing import Any, Dict, Optional

from core.services.call_engines.base import CallEngine
from core.services.call_engines.credentials import fetch_channel_credentials
from core.services.call_engines.exotel_engine import ExotelCallEngine
from core.services.call_engines.plivo_engine import PlivoCallEngine
from core.services.call_engines.telnyx_engine import TelnyxCallEngine
from core.services.call_engines.twilio_engine import TwilioCallEngine


SUPPORTED_PROVIDERS = ("twilio", "telnyx", "exotel", "plivo")


def get_call_engine(provider: str, **credentials: Any) -> CallEngine:
    key = (provider or "").strip().lower()

    if key == "twilio":
        return TwilioCallEngine(
            account_sid=credentials.get("account_sid", ""),
            auth_token=credentials.get("auth_token", ""),
        )

    if key == "telnyx":
        return TelnyxCallEngine(api_key=credentials.get("api_key", ""))

    if key == "exotel":
        return ExotelCallEngine()

    if key == "plivo":
        return PlivoCallEngine(
            auth_id=credentials.get("auth_id", ""),
            auth_token=credentials.get("auth_token", ""),
        )

    raise ValueError(
        f"Unknown call engine provider: {provider!r}. Supported: {SUPPORTED_PROVIDERS}"
    )


def build_call_engine_for_call(
    transport_type: str,
    call_data: Optional[Dict[str, Any]] = None,
) -> CallEngine:
    key = (transport_type or "").strip().lower()
    data = call_data or {}
    org_id = data.get("_org_id")
    channel_id = data.get("_channel_id")

    if key == "twilio":
        creds = data.get("_twilio_creds") or fetch_channel_credentials(
            "twilio", org_id=org_id, channel_id=channel_id
        )
        return get_call_engine(
            "twilio",
            account_sid=creds.get("account_sid", ""),
            auth_token=creds.get("auth_token", ""),
        )

    if key == "telnyx":
        creds = data.get("_telnyx_creds") or fetch_channel_credentials(
            "telnyx", org_id=org_id, channel_id=channel_id
        )
        return get_call_engine("telnyx", api_key=creds.get("api_key", ""))

    if key == "exotel":
        return get_call_engine("exotel")

    if key == "plivo":
        creds = data.get("_plivo_creds") or fetch_channel_credentials(
            "plivo", org_id=org_id, channel_id=channel_id
        )
        return get_call_engine(
            "plivo",
            auth_id=creds.get("auth_id", ""),
            auth_token=creds.get("auth_token", ""),
        )

    return get_call_engine(key)
