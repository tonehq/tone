"""Shared helpers for telephony call metadata."""

from typing import Optional


def provider_call_id(call_data: Optional[dict]) -> str:
    """The telephony provider's call identifier from parsed call_data.

    Twilio uses ``call_id``, Telnyx uses ``call_control_id``, and the WS stream
    falls back to ``stream_id``. Single source of truth so every transport id is
    added in one place (used by bot.py, bot_worker.py, and the pipeline runner).
    """
    call_data = call_data or {}
    return (
        call_data.get("call_id")
        or call_data.get("call_control_id")
        or call_data.get("stream_id", "")
    )
