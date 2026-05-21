"""Tests for Channels API endpoints (Core edition).

Source: core/api/v1/channels.py
Postman: channels.postman_collection.json
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException
from fastapi.testclient import TestClient

from main import app, api_v1
from core.database.session import get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_channel():
    return {
        "id": 1,
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Twilio Channel",
        "type": "twilio",
        "status": "active",
        "meta_data": {},
        "created_at": "2026-01-15T10:00:00",
    }


@pytest.fixture
def sample_channels(sample_channel):
    return [
        sample_channel,
        {"id": 2, "name": "Web Channel", "type": "web", "status": "active"},
    ]


@pytest.fixture
def public_client(mock_db):
    """Client with only DB override -- for no-auth endpoints like get_by_type."""
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /api/v1/channel/upsert
# ---------------------------------------------------------------------------

class TestUpsertChannel:
    """Tests for POST /api/v1/channel/upsert"""

    @patch("core.api.v1.channels.ChannelService")
    def test_success_create(self, mock_service_cls, client_as_member, sample_channel):
        mock_service_cls.return_value.upsert_channel.return_value = sample_channel
        resp = client_as_member.post(
            "/api/v1/channel/upsert",
            json={
                "name": "Twilio Channel",
                "type": "twilio",
                "meta_data": {"account_sid": "AC...", "auth_token": "token..."},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Twilio Channel"
        assert data["type"] == "twilio"
        mock_service_cls.return_value.upsert_channel.assert_called_once()

    def test_missing_name(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/channel/upsert", json={"type": "twilio"}
        )
        assert resp.status_code == 400
        assert "name" in resp.json()["detail"].lower()

    def test_empty_name(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/channel/upsert", json={"name": ""}
        )
        assert resp.status_code == 400

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/channel/upsert", json={"name": "Channel"}
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.channels.ChannelService")
    def test_duplicate_type_conflict(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.upsert_channel.side_effect = HTTPException(
            status_code=409, detail="Channel type already exists"
        )
        resp = client_as_member.post(
            "/api/v1/channel/upsert", json={"name": "Dup Channel"}
        )
        assert resp.status_code == 409

    @patch("core.api.v1.channels.ChannelService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.upsert_channel.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.post(
            "/api/v1/channel/upsert", json={"name": "Channel"}
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/channel/list
# ---------------------------------------------------------------------------

class TestGetAllChannels:
    """Tests for GET /api/v1/channel/list"""

    @patch("core.api.v1.channels.ChannelService")
    def test_success(self, mock_service_cls, client_as_member, sample_channels):
        mock_service_cls.return_value.get_all_channels.return_value = sample_channels
        resp = client_as_member.get("/api/v1/channel/list")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "Twilio Channel"

    @patch("core.api.v1.channels.ChannelService")
    def test_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_channels.return_value = []
        resp = client_as_member.get("/api/v1/channel/list")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/channel/list")
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.channels.ChannelService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_channels.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.get("/api/v1/channel/list")
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/channel/get
# ---------------------------------------------------------------------------

class TestGetChannel:
    """Tests for GET /api/v1/channel/get"""

    @patch("core.api.v1.channels.ChannelService")
    def test_success(self, mock_service_cls, client_as_member, sample_channel):
        mock_service_cls.return_value.get_channel.return_value = sample_channel
        resp = client_as_member.get("/api/v1/channel/get", params={"channel_id": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["name"] == "Twilio Channel"

    @patch("core.api.v1.channels.ChannelService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_channel.side_effect = HTTPException(
            status_code=404, detail="Channel not found"
        )
        resp = client_as_member.get("/api/v1/channel/get", params={"channel_id": 999})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Channel not found"

    def test_missing_channel_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/channel/get")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/channel/get", params={"channel_id": 1}
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.channels.ChannelService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_channel.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.get("/api/v1/channel/get", params={"channel_id": 1})
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/channel/get_by_type (NO AUTH)
# ---------------------------------------------------------------------------

class TestGetChannelByType:
    """Tests for GET /api/v1/channel/get_by_type (public, no auth)"""

    @patch("core.api.v1.channels.ChannelService")
    def test_success(self, mock_service_cls, public_client, sample_channel):
        mock_service_cls.return_value.get_channel_by_type.return_value = sample_channel
        resp = public_client.get(
            "/api/v1/channel/get_by_type", params={"type": "twilio"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "twilio"
        mock_service_cls.return_value.get_channel_by_type.assert_called_once_with("twilio")

    def test_missing_type(self, public_client):
        resp = public_client.get("/api/v1/channel/get_by_type")
        assert resp.status_code == 422

    @patch("core.api.v1.channels.ChannelService")
    def test_not_found(self, mock_service_cls, public_client):
        mock_service_cls.return_value.get_channel_by_type.return_value = None
        resp = public_client.get(
            "/api/v1/channel/get_by_type", params={"type": "unknown"}
        )
        assert resp.status_code == 200

    @patch("core.api.v1.channels.ChannelService")
    def test_service_error(self, mock_service_cls, public_client):
        mock_service_cls.return_value.get_channel_by_type.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = public_client.get(
            "/api/v1/channel/get_by_type", params={"type": "twilio"}
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/channel/list_by_type
# ---------------------------------------------------------------------------

class TestListChannelsByType:
    """Tests for GET /api/v1/channel/list_by_type"""

    @patch("core.api.v1.channels.ChannelService")
    def test_success(self, mock_service_cls, client_as_member, sample_channels):
        mock_service_cls.return_value.get_channels_by_type.return_value = [sample_channels[0]]
        resp = client_as_member.get(
            "/api/v1/channel/list_by_type", params={"type": "twilio"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["type"] == "twilio"
        mock_service_cls.return_value.get_channels_by_type.assert_called_once_with("twilio")

    @patch("core.api.v1.channels.ChannelService")
    def test_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_channels_by_type.return_value = []
        resp = client_as_member.get(
            "/api/v1/channel/list_by_type", params={"type": "unknown"}
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_missing_type(self, client_as_member):
        resp = client_as_member.get("/api/v1/channel/list_by_type")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/channel/list_by_type", params={"type": "twilio"}
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.channels.ChannelService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_channels_by_type.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.get(
            "/api/v1/channel/list_by_type", params={"type": "twilio"}
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# DELETE /api/v1/channel/delete (require_admin_or_owner)
# ---------------------------------------------------------------------------

class TestDeleteChannel:
    """Tests for DELETE /api/v1/channel/delete"""

    @patch("core.api.v1.channels.ChannelService")
    def test_success(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.delete_channel.return_value = {
            "message": "Channel deleted successfully"
        }
        resp = client_as_admin.delete(
            "/api/v1/channel/delete", params={"channel_id": 1}
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Channel deleted successfully"
        mock_service_cls.return_value.delete_channel.assert_called_once_with(1)

    @patch("core.api.v1.channels.ChannelService")
    def test_success_as_member(self, mock_service_cls, client_as_member):
        """Members can also call this since conftest overrides require_admin_or_owner."""
        mock_service_cls.return_value.delete_channel.return_value = {
            "message": "Channel deleted successfully"
        }
        resp = client_as_member.delete(
            "/api/v1/channel/delete", params={"channel_id": 1}
        )
        assert resp.status_code == 200

    def test_missing_channel_id(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/channel/delete")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete(
            "/api/v1/channel/delete", params={"channel_id": 1}
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.channels.ChannelService")
    def test_service_error(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.delete_channel.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_admin.delete(
            "/api/v1/channel/delete", params={"channel_id": 1}
        )
        assert resp.status_code in (500, 422, 400)
