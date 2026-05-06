"""Tests for Channels API endpoints (Core edition).

Source: core/api/v1/channels.py
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
    return {"id": 1, "name": "Twilio Channel", "type": "twilio", "created_by": 1}


@pytest.fixture
def sample_channels(sample_channel):
    return [
        sample_channel,
        {"id": 2, "name": "Web Channel", "type": "web", "created_by": 1},
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

    @patch("ee.api.v1.channels.ChannelService")
    def test_success(self, mock_service_cls, client_as_member, sample_channel):
        mock_service_cls.return_value.upsert_channel.return_value = sample_channel
        resp = client_as_member.post(
            "/api/v1/channel/upsert", json={"name": "Twilio Channel"}
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Twilio Channel"
        mock_service_cls.return_value.upsert_channel.assert_called_once_with(
            {"name": "Twilio Channel"}, created_by=ANY,
        )

    def test_missing_name(self, client_as_member):
        resp = client_as_member.post("/api/v1/channel/upsert", json={"type": "twilio"})
        assert resp.status_code == 400
        assert "name" in resp.json()["detail"].lower()

    def test_empty_name(self, client_as_member):
        resp = client_as_member.post("/api/v1/channel/upsert", json={"name": ""})
        assert resp.status_code == 400

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/channel/upsert", json={"name": "Channel"}
        )
        assert resp.status_code in (401, 403)

    @patch("ee.api.v1.channels.ChannelService")
    def test_duplicate_type_conflict(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.upsert_channel.side_effect = HTTPException(
            status_code=409, detail="Channel type already exists"
        )
        resp = client_as_member.post(
            "/api/v1/channel/upsert", json={"name": "Dup Channel"}
        )
        assert resp.status_code == 409

    @patch("ee.api.v1.channels.ChannelService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.upsert_channel.side_effect = HTTPException(status_code=500, detail="DB error")
        resp = client_as_member.post(
            "/api/v1/channel/upsert", json={"name": "Channel"}
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/channel/list
# ---------------------------------------------------------------------------

class TestGetAllChannels:
    """Tests for GET /api/v1/channel/list"""

    @patch("ee.api.v1.channels.ChannelService")
    def test_success(self, mock_service_cls, client_as_member, sample_channels):
        mock_service_cls.return_value.get_all_channels.return_value = sample_channels
        resp = client_as_member.get("/api/v1/channel/list")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @patch("ee.api.v1.channels.ChannelService")
    def test_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_channels.return_value = []
        resp = client_as_member.get("/api/v1/channel/list")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/channel/list")
        assert resp.status_code in (401, 403)

    @patch("ee.api.v1.channels.ChannelService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_channels.side_effect = HTTPException(status_code=500, detail="DB error")
        resp = client_as_member.get("/api/v1/channel/list")
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/channel/get
# ---------------------------------------------------------------------------

class TestGetChannel:
    """Tests for GET /api/v1/channel/get"""

    @patch("ee.api.v1.channels.ChannelService")
    def test_success(self, mock_service_cls, client_as_member, sample_channel):
        mock_service_cls.return_value.get_channel.return_value = sample_channel
        resp = client_as_member.get("/api/v1/channel/get", params={"channel_id": 1})
        assert resp.status_code == 200
        assert resp.json()["id"] == 1

    @patch("ee.api.v1.channels.ChannelService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_channel.return_value = None
        resp = client_as_member.get("/api/v1/channel/get", params={"channel_id": 999})
        assert resp.status_code == 200  # returns None; controller doesn't raise 404

    def test_missing_channel_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/channel/get")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/channel/get", params={"channel_id": 1})
        assert resp.status_code in (401, 403)

    @patch("ee.api.v1.channels.ChannelService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_channel.side_effect = HTTPException(status_code=500, detail="DB error")
        resp = client_as_member.get("/api/v1/channel/get", params={"channel_id": 1})
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/channel/get_by_type (NO AUTH)
# ---------------------------------------------------------------------------

class TestGetChannelByType:
    """Tests for GET /api/v1/channel/get_by_type (public, no auth)"""

    @patch("ee.api.v1.channels.ChannelService")
    def test_success(self, mock_service_cls, public_client, sample_channel):
        mock_service_cls.return_value.get_channel_by_type.return_value = sample_channel
        resp = public_client.get("/api/v1/channel/get_by_type", params={"type": "twilio"})
        assert resp.status_code == 200
        mock_service_cls.return_value.get_channel_by_type.assert_called_once_with("twilio")

    def test_missing_type(self, public_client):
        resp = public_client.get("/api/v1/channel/get_by_type")
        assert resp.status_code == 422

    @patch("ee.api.v1.channels.ChannelService")
    def test_not_found(self, mock_service_cls, public_client):
        mock_service_cls.return_value.get_channel_by_type.return_value = None
        resp = public_client.get("/api/v1/channel/get_by_type", params={"type": "unknown"})
        assert resp.status_code == 200

    @patch("ee.api.v1.channels.ChannelService")
    def test_service_error(self, mock_service_cls, public_client):
        mock_service_cls.return_value.get_channel_by_type.side_effect = HTTPException(status_code=500, detail="DB error")
        resp = public_client.get("/api/v1/channel/get_by_type", params={"type": "twilio"})
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# DELETE /api/v1/channel/delete (require_admin_or_owner)
# ---------------------------------------------------------------------------

class TestDeleteChannel:
    """Tests for DELETE /api/v1/channel/delete"""

    @patch("ee.api.v1.channels.ChannelService")
    def test_success(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.delete_channel.return_value = {"message": "deleted"}
        resp = client_as_admin.delete("/api/v1/channel/delete", params={"channel_id": 1})
        assert resp.status_code == 200
        mock_service_cls.return_value.delete_channel.assert_called_once_with(1)

    @patch("ee.api.v1.channels.ChannelService")
    def test_success_as_member(self, mock_service_cls, client_as_member):
        """Members can also call this since conftest overrides require_admin_or_owner."""
        mock_service_cls.return_value.delete_channel.return_value = {"message": "deleted"}
        resp = client_as_member.delete("/api/v1/channel/delete", params={"channel_id": 1})
        assert resp.status_code == 200

    def test_missing_channel_id(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/channel/delete")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete("/api/v1/channel/delete", params={"channel_id": 1})
        assert resp.status_code in (401, 403)

    @patch("ee.api.v1.channels.ChannelService")
    def test_service_error(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.delete_channel.side_effect = HTTPException(status_code=500, detail="DB error")
        resp = client_as_admin.delete("/api/v1/channel/delete", params={"channel_id": 1})
        assert resp.status_code in (500, 422, 400)
