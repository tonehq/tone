"""Tests for Channel API endpoints (EE edition).

Source: ee/api/v1/channels.py
Integration tests — real DB, real endpoints, no mocks.
"""

import pytest
import uuid


# ─── Helpers ───

def _unique_name(prefix="Channel"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_channel(client, name=None, channel_type="twilio", meta_data=None):
    """Create a channel via upsert and return JSON."""
    data = {
        "name": name or _unique_name(),
        "type": channel_type,
        "meta_data": meta_data or {},
    }
    resp = client.post("/api/v1/channel/upsert", json=data)
    assert resp.status_code == 200
    return resp.json()


# ─── POST /api/v1/channel/upsert ───

class TestUpsertChannel:
    """Tests for POST /api/v1/channel/upsert"""

    def test_upsert_channel_missing_name(self, client_as_member):
        response = client_as_member.post("/api/v1/channel/upsert", json={"type": "web"})
        assert response.status_code == 400

    def test_upsert_channel_empty_name(self, client_as_member):
        response = client_as_member.post("/api/v1/channel/upsert", json={"name": ""})
        assert response.status_code == 400

    def test_upsert_channel_empty_body(self, client_as_member):
        response = client_as_member.post("/api/v1/channel/upsert", json={})
        assert response.status_code == 400

    def test_upsert_channel_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/channel/upsert", json={"name": "Test"})
        assert response.status_code in (401, 403)

    def test_create_twilio_channel(self, client_as_member):
        """Postman: Create Twilio Channel (409 if one already exists — one per type)."""
        resp = client_as_member.post("/api/v1/channel/upsert", json={
            "name": _unique_name("Twilio"),
            "type": "twilio",
            "meta_data": {"account_sid": "ACtest123", "auth_token": "authtest123"},
        })
        assert resp.status_code in (200, 409)
        if resp.status_code == 200:
            data = resp.json()
            assert data["type"] == "twilio"
            assert "id" in data

    def test_create_exotel_channel(self, client_as_member):
        """Postman: Create Exotel Channel."""
        data = _create_channel(
            client_as_member,
            name=_unique_name("Exotel"),
            channel_type="exotel",
            meta_data={"account_sid": "exotel123", "api_key": "key", "api_token": "token"},
        )
        assert data["type"] == "exotel"

    def test_create_web_channel(self, client_as_member):
        """Postman: Create Web Channel."""
        data = _create_channel(
            client_as_member,
            name=_unique_name("Web"),
            channel_type="web",
            meta_data={},
        )
        assert data["type"] == "web"

    def test_create_google_meet_channel(self, client_as_member):
        """Postman: Create Google Meet Channel."""
        data = _create_channel(
            client_as_member,
            name=_unique_name("GMeet"),
            channel_type="google_meet",
            meta_data={"client_id": "cid", "client_secret": "csecret", "refresh_token": "rtoken"},
        )
        assert data["type"] == "google_meet"

    def test_create_zoom_channel(self, client_as_member):
        """Postman: Create Zoom Channel."""
        data = _create_channel(
            client_as_member,
            name=_unique_name("Zoom"),
            channel_type="zoom",
            meta_data={"client_id": "cid", "client_secret": "csecret", "account_id": "aid"},
        )
        assert data["type"] == "zoom"

    def test_update_channel(self, client_as_member):
        """Postman: Update Channel via id."""
        created = _create_channel(client_as_member, channel_type="web")
        resp = client_as_member.post("/api/v1/channel/upsert", json={
            "id": created["id"],
            "name": "Updated Channel",
            "type": "web",
            "meta_data": {"updated": True},
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Channel"


# ─── GET /api/v1/channel/list ───

class TestGetAllChannels:
    """Tests for GET /api/v1/channel/list"""

    def test_get_all_channels_returns_200(self, client_as_member):
        response = client_as_member.get("/api/v1/channel/list")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_all_channels_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/channel/list")
        assert response.status_code in (401, 403)

    def test_get_all_channels_includes_created(self, client_as_member):
        """Create a channel, list all, verify it appears."""
        created = _create_channel(client_as_member, channel_type="web")
        response = client_as_member.get("/api/v1/channel/list")
        assert response.status_code == 200
        channels = response.json()
        assert any(c["id"] == created["id"] for c in channels)


# ─── GET /api/v1/channel/get ───

class TestGetChannel:
    """Tests for GET /api/v1/channel/get"""

    def test_get_channel_missing_id(self, client_as_member):
        response = client_as_member.get("/api/v1/channel/get")
        assert response.status_code == 422

    def test_get_channel_invalid_id(self, client_as_member):
        response = client_as_member.get("/api/v1/channel/get?channel_id=abc")
        assert response.status_code == 422

    def test_get_channel_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/channel/get?channel_id=1")
        assert response.status_code in (401, 403)

    def test_get_channel_not_found(self, client_as_member):
        response = client_as_member.get("/api/v1/channel/get?channel_id=999999")
        assert response.status_code == 404

    def test_get_channel_success(self, client_as_member):
        created = _create_channel(client_as_member, channel_type="web")
        response = client_as_member.get(f"/api/v1/channel/get?channel_id={created['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]


# ─── GET /api/v1/channel/get_by_type ───

class TestGetChannelByType:
    """Tests for GET /api/v1/channel/get_by_type"""

    def test_get_by_type_missing_type(self, client_as_member):
        response = client_as_member.get("/api/v1/channel/get_by_type")
        assert response.status_code == 422

    def test_get_by_type_web(self, client_as_member):
        _create_channel(client_as_member, channel_type="web")
        response = client_as_member.get("/api/v1/channel/get_by_type?type=web")
        assert response.status_code == 200


# ─── DELETE /api/v1/channel/delete ───

class TestDeleteChannel:
    """Tests for DELETE /api/v1/channel/delete"""

    def test_delete_channel_missing_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/channel/delete")
        assert response.status_code == 422

    def test_delete_channel_invalid_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/channel/delete?channel_id=abc")
        assert response.status_code == 422

    def test_delete_channel_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/channel/delete?channel_id=1")
        assert response.status_code in (401, 403)

    def test_delete_channel_not_found(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/channel/delete?channel_id=999999")
        assert response.status_code == 404

    def test_delete_channel_success(self, client_as_admin):
        created = _create_channel(client_as_admin, channel_type="web")
        resp = client_as_admin.delete(f"/api/v1/channel/delete?channel_id={created['id']}")
        assert resp.status_code == 200
        get_resp = client_as_admin.get(f"/api/v1/channel/get?channel_id={created['id']}")
        assert get_resp.status_code == 404
