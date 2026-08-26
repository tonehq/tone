"""Regression tests for the media-stream WS fallback host resolution.

When pod pinning finds no live voice pod, the ``/twiml`` answer must NOT tell the
carrier to stream media back to whatever host served the webhook (e.g. the API
pod, where the STT/LLM/TTS pipeline must never run). It must fall back to the
call-service host (``CALL_SERVER_HOST``) so the un-pinned call still lands on the
call-worker pool via ``/ws``. See ``core/utils/telephony.fallback_media_ws_url``.
"""

import shared.config as config
from core.utils.telephony import fallback_media_ws_url


def test_fallback_prefers_call_server_host_over_request_host(monkeypatch):
    # Even when /twiml is served on the API host, the fallback points at the call host.
    monkeypatch.setattr(config.settings, "CALL_SERVER_HOST", "staging-call.trytone.ai")
    assert (
        fallback_media_ws_url("staging-api.trytone.ai")
        == "wss://staging-call.trytone.ai/ws"
    )


def test_fallback_uses_request_host_when_call_server_host_unset(monkeypatch):
    # Local/dev where API and call share one process: keep the request host.
    monkeypatch.setattr(config.settings, "CALL_SERVER_HOST", "")
    assert fallback_media_ws_url("localhost:8000") == "wss://localhost:8000/ws"


def test_fallback_defaults_to_localhost_when_nothing_available(monkeypatch):
    monkeypatch.setattr(config.settings, "CALL_SERVER_HOST", "")
    assert fallback_media_ws_url(None) == "wss://localhost/ws"
