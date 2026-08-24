"""Shared helpers for telephony call metadata."""

from typing import Optional, Tuple

from loguru import logger


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


def pinned_ws_url(default_ws_url: str, tag: str) -> Tuple[str, Optional[str], Optional[int], Optional[str]]:
    """Resolve the media-stream WebSocket URL, honoring pod pinning.

    Returns ``(ws_url, pod_name, pod_ordinal, node_name)`` — the pinned pod URL when
    pinning is enabled and succeeds, otherwise ``default_ws_url``. Shared by the
    inbound ``/twiml``, outbound ``/twiml/outbound`` and SIP routing paths so every
    answered call dials the same pinned voice pod.
    """
    from core.database.session import get_db_context
    from core.services.pod_picker import PodPicker
    from shared.config import settings

    ws_url = default_ws_url
    pod_name = None
    pod_ordinal = None
    node_name = None
    if settings.POD_PINNING_ENABLED:
        try:
            pinned_url = None
            with get_db_context() as db:
                picker = PodPicker(db)
                pod = picker.pick()
                pinned_url = picker.url_for(pod)
                if pod is not None:
                    pod_name = pod.name
                    pod_ordinal = pod.ordinal
                    node_name = pod.node.name if pod.node is not None else None
            if pinned_url:
                ws_url = pinned_url
        except Exception:
            logger.exception("[{}] pod pinning failed, falling back to /ws", tag)
    return ws_url, pod_name, pod_ordinal, node_name


def default_media_ws_url(base_url: str) -> str:
    """Turn a public HTTP base URL into the ``wss://host/ws`` media endpoint.

    Used by callers with no inbound request to derive the host from (the SIP call
    engine, scheduled dials) so the media leg lands on the same ``/ws`` endpoint a
    carrier-bridged call uses.
    """
    base = (base_url or "").strip().rstrip("/")
    if not base:
        return ""
    if base.startswith("https://"):
        base = f"wss://{base[len('https://'):]}"
    elif base.startswith("http://"):
        base = f"ws://{base[len('http://'):]}"
    return f"{base}/ws"
