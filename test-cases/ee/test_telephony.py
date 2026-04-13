"""Tests for Telephony WebSocket endpoint (EE edition).

Source: ee/api/v1/telephony.py (re-exports core/api/v1/telephony.py)
Integration tests — real server, no mocks.
"""

import pytest
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
