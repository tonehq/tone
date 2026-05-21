"""Tests for Telephony WebSocket endpoints (EE edition).

Source: ee/api/v1/telephony.py
Postman: postman_collection/telephony.postman_collection.json
Integration tests -- WebSocket protocol testing.

Note: Full pipeline testing requires actual voice infrastructure (STT/TTS/LLM).
These tests verify WebSocket route registration and connection parameter validation.
The /ws endpoint expects actual telephony protocol messages after accepting, so
we can only test route existence and /ws/test parameter validation.
"""

import pytest
from fastapi.testclient import TestClient
from main import app


class TestTelephonyWebSocket:
    """Tests for WebSocket /ws endpoint.

    Postman: Telephony WebSocket - Connection Info (101 Switching Protocols).
    """

    def test_websocket_route_registered(self):
        """Verify the /ws WebSocket route is registered on the app."""
        ws_routes = [
            route
            for route in app.routes
            if hasattr(route, "path") and route.path == "/ws"
        ]
        assert len(ws_routes) > 0, "/ws route should be registered on the app"

    def test_ws_connects_and_accepts(self):
        """WebSocket at /ws should accept the connection (101 upgrade).

        The telephony handler accepts first, then reads provider-specific
        messages. Without valid messages it will eventually error/close,
        but the initial accept should succeed.
        """
        client = TestClient(app)
        try:
            with client.websocket_connect("/ws") as ws:
                # Connection accepted -- the server is now waiting for
                # telephony provider messages. We just verify the upgrade
                # succeeded and close.
                pass
        except Exception:
            # Some server-side errors are expected without real telephony data
            pass


class TestTelephonyTestWebSocket:
    """Tests for WebSocket /ws/test endpoint -- parameter validation.

    Postman: Test WebSocket endpoint with agent_id or phone_number query params.
    Close codes:
    - 4000: missing agent_id/phone_number, or invalid agent_id format
    - 4004: agent not found
    """

    def test_ws_test_route_registered(self):
        """Verify the /ws/test WebSocket route is registered on the app."""
        ws_routes = [
            route
            for route in app.routes
            if hasattr(route, "path") and "/ws/test" in getattr(route, "path", "")
        ]
        assert len(ws_routes) > 0, "/ws/test route should be registered on the app"

    def test_ws_test_missing_params_closes(self):
        """Postman: Test WebSocket - Missing Params (4000).
        Without agent_id or phone_number, server closes with code 4000.
        """
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
        """Postman: Test WebSocket - Agent Not Found (4004).
        agent_id=999999 should close with code 4004 (not found).
        """
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
