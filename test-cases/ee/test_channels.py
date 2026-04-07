"""Tests for Channel API endpoints.

Source: core/api/v1/channels.py
"""

import pytest
from uuid import UUID
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException

EXPECTED_ORG_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
EXPECTED_USER_ID = 1


# ─── Fixtures ───

@pytest.fixture
def sample_channel_data():
    return {
        "name": "Test Channel",
        "type": "web",
        "config": {},
    }


# ─── POST /api/v1/channel/upsert — Upsert Channel ───

class TestUpsertChannel:
    """Tests for POST /api/v1/channel/upsert"""

    @patch("ee.api.v1.channels.ChannelService")
    def test_upsert_channel_create_success(self, mock_service_cls, client_as_member, sample_channel_data):
        mock_service_cls.return_value.upsert_channel.return_value = {"id": 1, **sample_channel_data}
        response = client_as_member.post("/api/v1/channel/upsert", json=sample_channel_data)
        assert response.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID, user_id=EXPECTED_USER_ID)

    @patch("ee.api.v1.channels.ChannelService")
    def test_upsert_channel_update_success(self, mock_service_cls, client_as_member):
        data = {"id": 1, "name": "Updated Channel"}
        mock_service_cls.return_value.upsert_channel.return_value = data
        response = client_as_member.post("/api/v1/channel/upsert", json=data)
        assert response.status_code == 200

    @patch("ee.api.v1.channels.ChannelService")
    def test_upsert_channel_missing_name(self, mock_service_cls, client_as_member):
        response = client_as_member.post("/api/v1/channel/upsert", json={"type": "web"})
        assert response.status_code == 400
        assert "name is required" in response.json()["detail"]

    @patch("ee.api.v1.channels.ChannelService")
    def test_upsert_channel_empty_name(self, mock_service_cls, client_as_member):
        response = client_as_member.post("/api/v1/channel/upsert", json={"name": ""})
        assert response.status_code == 400

    @patch("ee.api.v1.channels.ChannelService")
    def test_upsert_channel_empty_body(self, mock_service_cls, client_as_member):
        response = client_as_member.post("/api/v1/channel/upsert", json={})
        assert response.status_code == 400

    @patch("ee.api.v1.channels.ChannelService")
    def test_upsert_channel_with_type(self, mock_service_cls, client_as_member):
        data = {"name": "Twilio Channel", "type": "twilio"}
        mock_service_cls.return_value.upsert_channel.return_value = {"id": 1, **data}
        response = client_as_member.post("/api/v1/channel/upsert", json=data)
        assert response.status_code == 200

    @patch("ee.api.v1.channels.ChannelService")
    def test_upsert_channel_duplicate_type(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.upsert_channel.side_effect = HTTPException(
            status_code=409, detail="Channel with this type already exists"
        )
        response = client_as_member.post("/api/v1/channel/upsert", json={
            "name": "Dup Channel", "type": "twilio"
        })
        assert response.status_code == 409

    @patch("ee.api.v1.channels.ChannelService")
    def test_upsert_channel_service_error(self, mock_service_cls, client_as_member, sample_channel_data):
        mock_service_cls.return_value.upsert_channel.side_effect = HTTPException(
            status_code=500, detail="Internal error"
        )
        response = client_as_member.post("/api/v1/channel/upsert", json=sample_channel_data)
        assert response.status_code == 500

    def test_upsert_channel_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/channel/upsert", json={"name": "Test"})
        assert response.status_code in (401, 403)


# ─── GET /api/v1/channel/list — Get All Channels ───

class TestGetAllChannels:
    """Tests for GET /api/v1/channel/list"""

    @patch("ee.api.v1.channels.ChannelService")
    def test_get_all_channels_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_channels.return_value = [{"id": 1, "name": "Web"}]
        response = client_as_member.get("/api/v1/channel/list")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID, user_id=EXPECTED_USER_ID)

    @patch("ee.api.v1.channels.ChannelService")
    def test_get_all_channels_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_channels.return_value = []
        response = client_as_member.get("/api/v1/channel/list")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_all_channels_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/channel/list")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/channel/get — Get Channel ───

class TestGetChannel:
    """Tests for GET /api/v1/channel/get"""

    @patch("ee.api.v1.channels.ChannelService")
    def test_get_channel_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_channel.return_value = {"id": 1, "name": "Web"}
        response = client_as_member.get("/api/v1/channel/get?channel_id=1")
        assert response.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID, user_id=EXPECTED_USER_ID)

    def test_get_channel_missing_id(self, client_as_member):
        response = client_as_member.get("/api/v1/channel/get")
        assert response.status_code == 422

    def test_get_channel_invalid_id(self, client_as_member):
        response = client_as_member.get("/api/v1/channel/get?channel_id=abc")
        assert response.status_code == 422

    @patch("ee.api.v1.channels.ChannelService")
    def test_get_channel_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_channel.side_effect = HTTPException(
            status_code=404, detail="Channel not found"
        )
        response = client_as_member.get("/api/v1/channel/get?channel_id=999")
        assert response.status_code == 404

    def test_get_channel_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/channel/get?channel_id=1")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/channel/get_by_type — Get Channel By Type ───

class TestGetChannelByType:
    """Tests for GET /api/v1/channel/get_by_type"""

    @patch("ee.api.v1.channels.ChannelService")
    def test_get_by_type_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_channel_by_type.return_value = {"id": 1, "type": "twilio"}
        response = client_as_member.get("/api/v1/channel/get_by_type?type=twilio")
        assert response.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)

    def test_get_by_type_missing_type(self, client_as_member):
        response = client_as_member.get("/api/v1/channel/get_by_type")
        assert response.status_code == 422

    @patch("ee.api.v1.channels.ChannelService")
    def test_get_by_type_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_channel_by_type.side_effect = HTTPException(
            status_code=404, detail="Channel not found"
        )
        response = client_as_member.get("/api/v1/channel/get_by_type?type=nonexistent")
        assert response.status_code == 404


# ─── DELETE /api/v1/channel/delete — Delete Channel ───

class TestDeleteChannel:
    """Tests for DELETE /api/v1/channel/delete"""

    @patch("ee.api.v1.channels.ChannelService")
    def test_delete_channel_success(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.delete_channel.return_value = {"message": "deleted"}
        response = client_as_admin.delete("/api/v1/channel/delete?channel_id=1")
        assert response.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID, user_id=EXPECTED_USER_ID)

    def test_delete_channel_missing_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/channel/delete")
        assert response.status_code == 422

    def test_delete_channel_invalid_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/channel/delete?channel_id=abc")
        assert response.status_code == 422

    @patch("ee.api.v1.channels.ChannelService")
    def test_delete_channel_not_found(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.delete_channel.side_effect = HTTPException(
            status_code=404, detail="Channel not found"
        )
        response = client_as_admin.delete("/api/v1/channel/delete?channel_id=999")
        assert response.status_code == 404

    def test_delete_channel_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/channel/delete?channel_id=1")
        assert response.status_code in (401, 403)
