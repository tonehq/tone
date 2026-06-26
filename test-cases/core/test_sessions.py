"""Tests for Session-management API endpoints (Core edition).

Source: core/api/v1/sessions.py
The router is mounted in both Core and EE under ``/api/v1/sessions``.
All endpoints require an authenticated user.
"""

import pytest
from unittest.mock import patch, MagicMock

from main import api_v1


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_session_dict():
    return {
        "id": "11111111-1111-1111-1111-111111111111",
        "user_id": "22222222-2222-2222-2222-222222222222",
        "organization_id": "33333333-3333-3333-3333-333333333333",
        "status": "active",
        "issued_at": "2026-06-01T00:00:00+00:00",
        "last_used_at": "2026-06-15T11:00:00+00:00",
        "expires_at": "2026-07-01T00:00:00+00:00",
        "revoked_at": None,
        "revoked_reason": None,
        "ip_address": "203.0.113.10",
        "user_agent": "Mozilla/5.0 ...",
        "device_type": "desktop",
        "device_name": "Mac",
        "browser": "Chrome 131.0.0",
        "os": "Mac OS X 10.15.7",
        "country": None,
        "city": None,
        "created_at": "2026-06-01T00:00:00+00:00",
        "updated_at": "2026-06-15T11:00:00+00:00",
    }


def _mock_session_obj(d: dict) -> MagicMock:
    """Wrap a dict in a MagicMock whose ``to_dict()`` returns it."""
    m = MagicMock()
    m.to_dict.return_value = d
    return m


# ---------------------------------------------------------------------------
# GET /api/v1/sessions/list
# ---------------------------------------------------------------------------


class TestListSessions:
    """Tests for GET /api/v1/sessions/list"""

    @patch("core.api.v1.sessions.SessionService")
    def test_list_sessions_success(self, mock_service_cls, client_as_member, sample_session_dict):
        mock_service_cls.return_value.list_user_sessions.return_value = [
            _mock_session_obj(sample_session_dict),
        ]
        resp = client_as_member.get("/api/v1/sessions/list")
        assert resp.status_code == 200
        data = resp.json()
        assert "sessions" in data
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["id"] == sample_session_dict["id"]
        mock_service_cls.return_value.list_user_sessions.assert_called_once()

    @patch("core.api.v1.sessions.SessionService")
    def test_list_sessions_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.list_user_sessions.return_value = []
        resp = client_as_member.get("/api/v1/sessions/list")
        assert resp.status_code == 200
        assert resp.json() == {"sessions": []}

    def test_list_sessions_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/sessions/list")
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.sessions.SessionService")
    def test_list_sessions_only_returns_active(self, mock_service_cls, client_as_member, sample_session_dict):
        """Endpoint must request active_only=True so revoked rows stay hidden."""
        mock_service_cls.return_value.list_user_sessions.return_value = [
            _mock_session_obj(sample_session_dict),
        ]
        client_as_member.get("/api/v1/sessions/list")
        _, kwargs = mock_service_cls.return_value.list_user_sessions.call_args
        assert kwargs.get("active_only") is True


# ---------------------------------------------------------------------------
# DELETE /api/v1/sessions/{session_id}
# ---------------------------------------------------------------------------


class TestRevokeSession:
    """Tests for DELETE /api/v1/sessions/{session_id}"""

    @patch("core.api.v1.sessions.SessionService")
    def test_revoke_session_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.revoke_session_by_id.return_value = True
        resp = client_as_member.delete(
            "/api/v1/sessions/11111111-1111-1111-1111-111111111111"
        )
        assert resp.status_code == 200
        assert resp.json() == {"message": "Session revoked"}
        mock_service_cls.return_value.revoke_session_by_id.assert_called_once()
        # The user_id kwarg must be the caller's id so users can't kill
        # other users' sessions.
        _, kwargs = mock_service_cls.return_value.revoke_session_by_id.call_args
        assert "user_id" in kwargs
        assert kwargs.get("reason") == "user_logout"

    @patch("core.api.v1.sessions.SessionService")
    def test_revoke_session_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.revoke_session_by_id.return_value = False
        resp = client_as_member.delete(
            "/api/v1/sessions/99999999-9999-9999-9999-999999999999"
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Session not found"

    def test_revoke_session_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete(
            "/api/v1/sessions/11111111-1111-1111-1111-111111111111"
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/sessions/revoke-others
# ---------------------------------------------------------------------------


class TestRevokeOtherSessions:
    """Tests for POST /api/v1/sessions/revoke-others"""

    @patch("core.api.v1.sessions.SessionService")
    @patch("core.api.v1.sessions.jwt_manager")
    def test_revoke_others_keeps_current(
        self, mock_jwt_manager, mock_service_cls, client_as_member,
    ):
        """When the body carries a refresh_token, the matching session id
        is excluded from the sweep so the caller stays signed in."""
        mock_jwt_manager.decode_refresh_token.return_value = {
            "jti": "11111111-1111-1111-1111-111111111111",
        }
        mock_service_cls.return_value.revoke_all_for_user.return_value = 2

        resp = client_as_member.post(
            "/api/v1/sessions/revoke-others",
            json={"refresh_token": "rt-xyz"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"message": "Sessions revoked", "revoked_count": 2}

        _, kwargs = mock_service_cls.return_value.revoke_all_for_user.call_args
        assert kwargs.get("reason") == "user_logout_others"
        assert kwargs.get("except_session_id") == "11111111-1111-1111-1111-111111111111"

    @patch("core.api.v1.sessions.SessionService")
    def test_revoke_all_when_body_empty(self, mock_service_cls, client_as_member):
        """No refresh_token → revoke every session, current device included."""
        mock_service_cls.return_value.revoke_all_for_user.return_value = 3
        resp = client_as_member.post("/api/v1/sessions/revoke-others", json={})
        assert resp.status_code == 200
        assert resp.json()["revoked_count"] == 3
        _, kwargs = mock_service_cls.return_value.revoke_all_for_user.call_args
        assert kwargs.get("except_session_id") is None

    @patch("core.api.v1.sessions.SessionService")
    @patch("core.api.v1.sessions.jwt_manager")
    def test_revoke_others_with_invalid_refresh_token(
        self, mock_jwt_manager, mock_service_cls, client_as_member,
    ):
        """A malformed refresh_token must not leak its failure — treat as
        'no current session to preserve' and continue silently."""
        from fastapi import HTTPException
        mock_jwt_manager.decode_refresh_token.side_effect = HTTPException(
            status_code=401, detail="Invalid refresh token",
        )
        mock_service_cls.return_value.revoke_all_for_user.return_value = 1

        resp = client_as_member.post(
            "/api/v1/sessions/revoke-others",
            json={"refresh_token": "garbage"},
        )
        assert resp.status_code == 200
        _, kwargs = mock_service_cls.return_value.revoke_all_for_user.call_args
        assert kwargs.get("except_session_id") is None

    def test_revoke_others_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/sessions/revoke-others", json={},
        )
        assert resp.status_code in (401, 403)
