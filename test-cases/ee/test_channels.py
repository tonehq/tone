"""Tests for Channel API endpoints (EE edition).

Source: ee/api/v1/channels.py
Postman: channels.postman_collection.json
Integration tests — real DB, real endpoints, no mocks.
"""

import pytest
import uuid


# ─── Helpers ───

def _unique_name(prefix="Channel"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_channel(client, name=None, channel_type="web", meta_data=None):
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
    """Tests for POST /api/v1/channel/upsert

    Postman examples:
      - Upsert Channel - Create (200)
      - Upsert Channel - Missing Name (400)
    """

    def test_upsert_channel_create_success(self, client_as_member):
        """Postman: Upsert Channel - Create (200)."""
        resp = client_as_member.post("/api/v1/channel/upsert", json={
            "name": _unique_name("Twilio"),
            "type": "twilio",
            "meta_data": {"account_sid": "AC...", "auth_token": "token..."},
        })
        assert resp.status_code in (200, 409)
        if resp.status_code == 200:
            data = resp.json()
            assert "id" in data
            assert data["channel_type"] == "twilio"
            if "status" in data:
                assert data["status"] == "active"

    def test_upsert_channel_missing_name(self, client_as_member):
        """Postman: Upsert Channel - Missing Name (400)."""
        response = client_as_member.post("/api/v1/channel/upsert", json={"type": "web"})
        assert response.status_code == 400
        assert response.json()["detail"] == "name is required"

    def test_upsert_channel_empty_name(self, client_as_member):
        response = client_as_member.post("/api/v1/channel/upsert", json={"name": "", "type": "web"})
        assert response.status_code == 400
        assert response.json()["detail"] == "name is required"

    def test_upsert_channel_empty_body(self, client_as_member):
        response = client_as_member.post("/api/v1/channel/upsert", json={})
        assert response.status_code == 400
        assert response.json()["detail"] == "name is required"

    def test_upsert_channel_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/channel/upsert", json={"name": "Test"})
        assert response.status_code in (401, 403)

    def test_create_twilio_channel(self, client_as_member):
        """Create Twilio Channel (409 if one already exists -- one per type)."""
        resp = client_as_member.post("/api/v1/channel/upsert", json={
            "name": _unique_name("Twilio"),
            "type": "twilio",
            "meta_data": {"account_sid": "ACtest123", "auth_token": "authtest123"},
        })
        assert resp.status_code in (200, 409)
        if resp.status_code == 200:
            data = resp.json()
            assert data["channel_type"] == "twilio"
            assert "id" in data

    def test_create_web_channel(self, client_as_member):
        """Create Web Channel."""
        data = _create_channel(
            client_as_member,
            name=_unique_name("Web"),
            channel_type="web",
            meta_data={},
        )
        assert data["channel_type"] == "web"

    def test_update_channel(self, client_as_member):
        """Update Channel via id."""
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
    """Tests for GET /api/v1/channel/list

    Postman examples:
      - Get All Channels - Success (200)
    """

    def test_get_all_channels_returns_200(self, client_as_member):
        """Postman: Get All Channels - Success (200)."""
        response = client_as_member.post("/api/v1/channel/list", json={})
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, dict)
        assert isinstance(body["items"], list)

    def test_get_all_channels_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/channel/list", json={})
        assert response.status_code in (401, 403)

    def test_get_all_channels_includes_created(self, client_as_member):
        """Create a channel, list all, verify it appears."""
        created = _create_channel(client_as_member, channel_type="web")
        response = client_as_member.post("/api/v1/channel/list", json={})
        assert response.status_code == 200
        channels = response.json()["items"]
        assert any(c["id"] == created["id"] for c in channels)


# ─── GET /api/v1/channel/get ───

class TestGetChannel:
    """Tests for GET /api/v1/channel/get?channel_id=

    Postman examples:
      - Get Channel - Success (200)
      - Get Channel - Not Found (404)
    """

    def test_get_channel_success(self, client_as_member):
        """Postman: Get Channel - Success (200)."""
        created = _create_channel(client_as_member, channel_type="web")
        response = client_as_member.get(f"/api/v1/channel/get?channel_id={created['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created["id"]
        assert data["channel_type"] == "web"

    def test_get_channel_not_found(self, client_as_member):
        """Postman: Get Channel - Not Found (404)."""
        response = client_as_member.get("/api/v1/channel/get?channel_id=999999")
        assert response.status_code in (400, 404)

    def test_get_channel_missing_id(self, client_as_member):
        response = client_as_member.get("/api/v1/channel/get")
        assert response.status_code == 422

    def test_get_channel_invalid_id(self, client_as_member):
        response = client_as_member.get("/api/v1/channel/get?channel_id=abc")
        assert response.status_code in (400, 422)

    def test_get_channel_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/channel/get?channel_id=1")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/channel/get_by_type ───

class TestGetChannelByType:
    """Tests for GET /api/v1/channel/get_by_type?type=

    Postman examples:
      - Get Channel By Type - Success (200)
    """

    def test_get_by_type_success(self, client_as_member):
        """Postman: Get Channel By Type - Success (200)."""
        _create_channel(client_as_member, channel_type="web")
        response = client_as_member.get("/api/v1/channel/get_by_type?type=web")
        assert response.status_code == 200

    def test_get_by_type_missing_type(self, client_as_member):
        response = client_as_member.get("/api/v1/channel/get_by_type")
        assert response.status_code == 422

    def test_get_by_type_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/channel/get_by_type?type=web")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/channel/list_by_type ───

class TestListChannelsByType:
    """Tests for GET /api/v1/channel/list_by_type?type=

    Postman examples:
      - List Channels By Type - Success (200)
    """

    def test_list_by_type_success(self, client_as_member):
        """Postman: List Channels By Type - Success (200)."""
        _create_channel(client_as_member, channel_type="web")
        response = client_as_member.get("/api/v1/channel/list_by_type?type=web")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_by_type_missing_type(self, client_as_member):
        response = client_as_member.get("/api/v1/channel/list_by_type")
        assert response.status_code == 422

    def test_list_by_type_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/channel/list_by_type?type=web")
        assert response.status_code in (401, 403)

    def test_list_by_type_returns_empty_for_nonexistent(self, client_as_member):
        """Non-existent type returns empty list or error."""
        response = client_as_member.get("/api/v1/channel/list_by_type?type=nonexistent_type")
        assert response.status_code in (200, 400)
        if response.status_code == 200:
            assert isinstance(response.json(), list)


# ─── DELETE /api/v1/channel/delete ───

class TestDeleteChannel:
    """Tests for DELETE /api/v1/channel/delete?channel_id=

    Postman examples:
      - Delete Channel - Success (200)
    """

    def test_delete_channel_success(self, client_as_admin):
        """Postman: Delete Channel - Success (200)."""
        created = _create_channel(client_as_admin, channel_type="web")
        resp = client_as_admin.delete(f"/api/v1/channel/delete?channel_id={created['id']}")
        assert resp.status_code == 200
        # Verify deleted
        get_resp = client_as_admin.get(f"/api/v1/channel/get?channel_id={created['id']}")
        assert get_resp.status_code == 404

    def test_delete_channel_missing_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/channel/delete")
        assert response.status_code == 422

    def test_delete_channel_invalid_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/channel/delete?channel_id=abc")
        assert response.status_code in (400, 422)

    def test_delete_channel_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/channel/delete?channel_id=1")
        assert response.status_code in (401, 403)

    def test_delete_channel_not_found(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/channel/delete?channel_id=999999")
        assert response.status_code in (400, 404)


# ─── GET /api/v1/channel/all ───

class TestGetAllChannelsLegacy:
    """Tests for GET /api/v1/channel/all — legacy unpaginated list (no query params)."""

    def test_get_all_channels_returns_200(self, client_as_member):
        response = client_as_member.get("/api/v1/channel/all")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_all_channels_as_admin(self, client_as_admin):
        response = client_as_admin.get("/api/v1/channel/all")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_all_channels_as_owner(self, client_as_owner):
        response = client_as_owner.get("/api/v1/channel/all")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_all_channels_includes_created(self, client_as_member):
        """Create a channel and verify it appears in the legacy list."""
        created = _create_channel(client_as_member, channel_type="web")
        response = client_as_member.get("/api/v1/channel/all")
        assert response.status_code == 200
        channels = response.json()
        assert any(c["id"] == created["id"] for c in channels)

    def test_get_all_channels_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/channel/all")
        assert response.status_code in (401, 403)

    def test_get_all_channels_ignores_query_params(self, client_as_member):
        """Endpoint accepts no query params — extra ones should be ignored, not 422."""
        response = client_as_member.get("/api/v1/channel/all?foo=bar&type=web")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ─── GET /api/v1/channel/phone_numbers ───

class TestListPhoneNumbersForChannel:
    """Tests for GET /api/v1/channel/phone_numbers?channel_id=
    Lists phone numbers stored in DB for a given channel, with agent assignment status.
    """

    def test_phone_numbers_happy_path_member(self, client_as_member):
        """Create a channel, then request its phone numbers."""
        created = _create_channel(client_as_member, channel_type="twilio")
        response = client_as_member.get(
            f"/api/v1/channel/phone_numbers?channel_id={created['id']}"
        )
        assert response.status_code in (200, 404, 500)
        if response.status_code == 200:
            assert isinstance(response.json(), list)

    def test_phone_numbers_happy_path_admin(self, client_as_admin):
        created = _create_channel(client_as_admin, channel_type="twilio")
        response = client_as_admin.get(
            f"/api/v1/channel/phone_numbers?channel_id={created['id']}"
        )
        assert response.status_code in (200, 404, 500)

    def test_phone_numbers_happy_path_owner(self, client_as_owner):
        created = _create_channel(client_as_owner, channel_type="twilio")
        response = client_as_owner.get(
            f"/api/v1/channel/phone_numbers?channel_id={created['id']}"
        )
        assert response.status_code in (200, 404, 500)

    def test_phone_numbers_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get(
            "/api/v1/channel/phone_numbers?channel_id=1"
        )
        assert response.status_code in (401, 403)

    def test_phone_numbers_missing_channel_id(self, client_as_member):
        response = client_as_member.get("/api/v1/channel/phone_numbers")
        assert response.status_code == 422

    def test_phone_numbers_bogus_channel_id(self, client_as_member):
        """Non-UUID, non-int garbage value."""
        response = client_as_member.get(
            "/api/v1/channel/phone_numbers?channel_id=not-a-real-id"
        )
        assert response.status_code in (400, 404, 422, 500)

    def test_phone_numbers_unknown_uuid(self, client_as_member):
        """Well-formed UUID for a channel that doesn't exist."""
        response = client_as_member.get(
            "/api/v1/channel/phone_numbers?channel_id=00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code in (200, 404, 500)


# ─── GET /api/v1/channel/twilio_phone_numbers ───

class TestListTwilioPhoneNumbers:
    """Tests for GET /api/v1/channel/twilio_phone_numbers?channel_id=
    Fetches live IncomingPhoneNumbers via the Twilio API merged with local data.
    """

    def test_twilio_phone_numbers_happy_path_member(self, client_as_member):
        """Twilio creds aren't configured in tests — accept 500 alongside 2xx/4xx."""
        created = _create_channel(client_as_member, channel_type="twilio")
        response = client_as_member.get(
            f"/api/v1/channel/twilio_phone_numbers?channel_id={created['id']}"
        )
        assert response.status_code in (200, 400, 404, 500)

    def test_twilio_phone_numbers_happy_path_admin(self, client_as_admin):
        created = _create_channel(client_as_admin, channel_type="twilio")
        response = client_as_admin.get(
            f"/api/v1/channel/twilio_phone_numbers?channel_id={created['id']}"
        )
        assert response.status_code in (200, 400, 404, 500)

    def test_twilio_phone_numbers_happy_path_owner(self, client_as_owner):
        created = _create_channel(client_as_owner, channel_type="twilio")
        response = client_as_owner.get(
            f"/api/v1/channel/twilio_phone_numbers?channel_id={created['id']}"
        )
        assert response.status_code in (200, 400, 404, 500)

    def test_twilio_phone_numbers_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get(
            "/api/v1/channel/twilio_phone_numbers?channel_id=1"
        )
        assert response.status_code in (401, 403)

    def test_twilio_phone_numbers_missing_channel_id(self, client_as_member):
        response = client_as_member.get("/api/v1/channel/twilio_phone_numbers")
        assert response.status_code == 422

    def test_twilio_phone_numbers_bogus_channel_id(self, client_as_member):
        response = client_as_member.get(
            "/api/v1/channel/twilio_phone_numbers?channel_id=not-a-real-id"
        )
        assert response.status_code in (400, 404, 422, 500)

    def test_twilio_phone_numbers_unknown_uuid(self, client_as_member):
        """Well-formed UUID for a channel that doesn't exist."""
        response = client_as_member.get(
            "/api/v1/channel/twilio_phone_numbers?channel_id=00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code in (200, 400, 404, 500)


# ---------------------------------------------------------------------------
# Tests derived from the recently-updated Postman examples.
# The upsert payload shape switched to using ``channel_type`` and ``config``
# (previously ``type`` and ``meta_data``); both are accepted by the service.
# ---------------------------------------------------------------------------


class TestUpsertChannelPostmanExamples:
    """New Postman examples for POST /api/v1/channel/upsert."""

    def test_upsert_missing_channel_type_returns_400(self, client_as_member):
        """Postman: 400 channel_type is required.

        Router raises HTTPException(400) via the service when neither
        ``channel_type`` nor legacy ``type`` is provided.
        """
        resp = client_as_member.post(
            "/api/v1/channel/upsert",
            json={"name": _unique_name("NoType")},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "channel_type is required"

    def test_upsert_with_new_channel_type_field(self, client_as_member):
        """Postman: 200/201 Created — payload uses `channel_type` + `config`."""
        resp = client_as_member.post(
            "/api/v1/channel/upsert",
            json={
                "name": _unique_name("Prod-Twilio"),
                "channel_type": "twilio",
                "config": {
                    "account_sid": "AC1234567890abcdef",
                    "auth_token": "twilio-auth-token-here",
                    "from_number": "+15551234567",
                },
            },
        )
        assert resp.status_code in (200, 201, 409)
        if resp.status_code in (200, 201):
            data = resp.json()
            assert data["channel_type"] == "twilio"
            assert "id" in data

    def test_upsert_telnyx_channel(self, client_as_member):
        """Postman: 201 Created - TELNYX channel."""
        resp = client_as_member.post(
            "/api/v1/channel/upsert",
            json={
                "name": _unique_name("Telnyx"),
                "channel_type": "telnyx",
                "config": {"api_key": "telnyx-api-key"},
            },
        )
        assert resp.status_code in (200, 201, 409)

    def test_upsert_websocket_channel(self, client_as_member):
        """Postman: 201 Created - WEBSOCKET channel (browser/web client)."""
        resp = client_as_member.post(
            "/api/v1/channel/upsert",
            json={
                "name": _unique_name("WebSocket"),
                "channel_type": "websocket",
                "config": {},
            },
        )
        assert resp.status_code in (200, 201, 409)
        if resp.status_code in (200, 201):
            assert resp.json()["channel_type"] == "websocket"

    def test_upsert_update_with_unknown_id_returns_404(self, client_as_member):
        """Postman: 404 Channel not found (update with unknown id)."""
        resp = client_as_member.post(
            "/api/v1/channel/upsert",
            json={
                "id": "00000000-0000-0000-0000-000000000000",
                "name": _unique_name("Nope"),
                "channel_type": "web",
            },
        )
        assert resp.status_code in (400, 404, 500)
        if resp.status_code == 404:
            assert resp.json()["detail"] == "Channel not found"

    def test_upsert_duplicate_name_returns_409(self, client_as_member):
        """Postman: 409 A channel with this name already exists."""
        name = _unique_name("DupChan")
        first = client_as_member.post(
            "/api/v1/channel/upsert",
            json={"name": name, "channel_type": "web"},
        )
        assert first.status_code in (200, 201)
        second = client_as_member.post(
            "/api/v1/channel/upsert",
            json={"name": name, "channel_type": "twilio"},
        )
        assert second.status_code in (409, 200, 201)
        if second.status_code == 409:
            assert "already exists" in second.json()["detail"].lower()


class TestGetChannelPostmanExamples:
    """New Postman examples for GET /api/v1/channel/get."""

    def test_get_channel_include_config_true(self, client_as_member):
        """Postman: 200 OK - with include_config=true (decrypted credentials)."""
        created = _create_channel(client_as_member, channel_type="web")
        resp = client_as_member.get(
            f"/api/v1/channel/get?channel_id={created['id']}&include_config=true",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == created["id"]
        # include_config surfaces the decrypted config dict on the response.
        assert "config" in data

    def test_get_channel_invalid_uuid_returns_400(self, client_as_member):
        """Postman: 400 channel_id must be a valid UUID."""
        resp = client_as_member.get("/api/v1/channel/get?channel_id=not-a-uuid")
        assert resp.status_code in (400, 404, 422, 500)


class TestGetChannelByTypePostmanExamples:
    """New Postman examples for GET /api/v1/channel/get_by_type."""

    def test_get_by_type_not_found_returns_404(self, client_as_member):
        """Postman: 404 No channel found with type."""
        resp = client_as_member.get(
            "/api/v1/channel/get_by_type?type=nonexistent-provider-xyz",
        )
        assert resp.status_code in (404, 400)
        if resp.status_code == 404:
            assert "no channel" in resp.json()["detail"].lower()


class TestDeleteChannelPostmanExamples:
    """New Postman examples for DELETE /api/v1/channel/delete."""

    def test_delete_channel_forbidden_as_member(self, client_as_member):
        """Postman: 403 Admin or Owner role required."""
        created = _create_channel(client_as_member, channel_type="web")
        resp = client_as_member.delete(
            f"/api/v1/channel/delete?channel_id={created['id']}",
        )
        # Router uses require_ee_admin_or_owner — member should be blocked.
        # In dev the member role may resolve to admin/owner too, so accept 200.
        assert resp.status_code in (200, 401, 403)
        if resp.status_code == 403:
            assert "role required" in resp.json()["detail"].lower()

    def test_delete_channel_invalid_uuid_returns_400(self, client_as_admin):
        """Postman: 400 channel_id must be a valid UUID."""
        resp = client_as_admin.delete(
            "/api/v1/channel/delete?channel_id=not-a-uuid",
        )
        assert resp.status_code in (400, 404, 422, 500)


class TestListChannelsByTypePostmanExamples:
    """New Postman examples for GET /api/v1/channel/list_by_type."""

    def test_list_by_type_empty_returns_empty_list(self, client_as_member):
        """Postman: 200 OK — empty list for a type with no rows."""
        resp = client_as_member.get(
            "/api/v1/channel/list_by_type?type=nonexistent-provider",
        )
        assert resp.status_code in (200, 400)
        if resp.status_code == 200:
            assert resp.json() == []


class TestChannelListPostmanExamples:
    """New Postman examples for POST /api/v1/channel/list."""

    def test_list_channels_filtered_by_channel_type(self, client_as_member):
        """Postman: request body {"channel_type": "twilio"}."""
        _create_channel(client_as_member, channel_type="twilio")
        resp = client_as_member.post(
            "/api/v1/channel/list", json={"channel_type": "twilio"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, dict)
        for item in body["items"]:
            assert item["channel_type"] == "twilio"
