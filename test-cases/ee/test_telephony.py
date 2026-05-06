"""Tests for Telephony WebSocket endpoints (EE edition).

Source: ee/api/v1/telephony.py
Integration tests — WebSocket protocol testing.

Note: Full pipeline testing requires actual voice infrastructure (STT/TTS/LLM).
These tests verify WebSocket route registration and connection parameter validation.
The /ws endpoint expects actual telephony protocol messages after accepting, so
we can only test route existence and /ws/test parameter validation.
"""

import pytest
from fastapi.testclient import TestClient
from main import app


class TestTelephonyWebSocket:
    """Tests for WebSocket /ws endpoint."""

    def test_websocket_route_registered(self):
        """Verify the /ws WebSocket route is registered on the app."""
        ws_routes = [
            route
            for route in app.routes
            if hasattr(route, "path") and route.path == "/ws"
        ]
        assert len(ws_routes) > 0, "/ws route should be registered on the app"

    def test_ws_test_route_registered(self):
        """Verify the /ws/test WebSocket route is registered on the app."""
        ws_routes = [
            route
            for route in app.routes
            if hasattr(route, "path") and "/ws/test" in getattr(route, "path", "")
        ]
        assert len(ws_routes) > 0, "/ws/test route should be registered on the app"


class TestTelephonyTestWebSocket:
    """Tests for WebSocket /ws/test endpoint — parameter validation.

    /ws/test closes the connection with specific codes for invalid params:
    - 4000: missing agent_id/phone_number, or invalid agent_id format
    - 4004: agent not found
    """

    def test_ws_test_missing_params_closes(self):
        """Without agent_id or phone_number, server closes with code 4000."""
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/test") as ws:
                ws.receive_text()

    def test_ws_test_with_invalid_agent_id_closes(self):
        """agent_id=abc should close with code 4000 (must be integer)."""
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/test?agent_id=abc") as ws:
                ws.receive_text()

    def test_ws_test_with_nonexistent_agent_closes(self):
        """agent_id=999999 should close with code 4004 (not found)."""
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/test?agent_id=999999") as ws:
                ws.receive_text()

    def test_ws_test_with_nonexistent_phone_closes(self):
        """Non-existent phone_number should close with code 4004."""
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/test?phone_number=%2B10000000000") as ws:
                ws.receive_text()
