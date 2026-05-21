"""Tests for Channel Phone Numbers API endpoints (EE edition).

Source: ee/api/v1/channel_phone_numbers.py
Postman: channel_phone_numbers.postman_collection.json
Integration tests — real DB, real endpoints, no mocks.
"""

import pytest
import uuid


# ─── Helpers ───

def _get_or_create_channel(client, channel_type="twilio"):
    """Get an existing channel of the given type, or create one. Returns JSON."""
    resp = client.get(f"/api/v1/channel/get_by_type?type={channel_type}")
    if resp.status_code == 200:
        return resp.json()
    data = {
        "name": f"test-channel-{uuid.uuid4().hex[:8]}",
        "type": channel_type,
        "meta_data": {"account_sid": "ACtest", "auth_token": "authtest"},
    }
    resp = client.post("/api/v1/channel/upsert", json=data)
    assert resp.status_code == 200
    return resp.json()


def _create_phone_number(client, channel_id):
    """Create a phone number record via upsert and return JSON."""
    payload = {
        "phone_number": f"+1555{uuid.uuid4().hex[:7]}",
        "phone_number_sid": f"PN{uuid.uuid4().hex[:10]}",
        "provider": "twilio",
        "channel_id": channel_id,
    }
    resp = client.post("/api/v1/channel_phone_number/upsert", json=payload)
    assert resp.status_code == 200
    return resp.json()


# ─── POST /api/v1/channel_phone_number/upsert ───

class TestUpsertChannelPhoneNumber:
    """Tests for POST /api/v1/channel_phone_number/upsert

    Postman examples:
      - Upsert - Success (200)
      - Upsert - Missing Phone Number (400)
      - Upsert - Missing SID (400)
      - Upsert - Missing Provider (400)
      - Upsert - Missing Channel ID (400)
    """

    def test_upsert_success(self, client_as_member):
        """Postman: Upsert - Success (200)."""
        channel = _get_or_create_channel(client_as_member, channel_type="twilio")
        resp = client_as_member.post("/api/v1/channel_phone_number/upsert", json={
            "phone_number": f"+1234{uuid.uuid4().hex[:6]}",
            "phone_number_sid": f"PN{uuid.uuid4().hex[:8]}",
            "provider": "twilio",
            "channel_id": channel["id"],
        })
        assert resp.status_code in (200, 409)
        if resp.status_code == 200:
            data = resp.json()
            assert "id" in data
            assert data["provider"] == "twilio"

    def test_upsert_missing_phone_number(self, client_as_member):
        """Postman: Upsert - Missing Phone Number (400)."""
        response = client_as_member.post("/api/v1/channel_phone_number/upsert", json={
            "phone_number_sid": "PN123",
            "provider": "twilio",
            "channel_id": 1,
        })
        assert response.status_code == 400

    def test_upsert_missing_sid(self, client_as_member):
        """Postman: Upsert - Missing SID (400)."""
        response = client_as_member.post("/api/v1/channel_phone_number/upsert", json={
            "phone_number": "+1234567890",
            "provider": "twilio",
            "channel_id": 1,
        })
        assert response.status_code == 400

    def test_upsert_missing_provider(self, client_as_member):
        """Postman: Upsert - Missing Provider (400)."""
        response = client_as_member.post("/api/v1/channel_phone_number/upsert", json={
            "phone_number": "+1234567890",
            "phone_number_sid": "PN123",
            "channel_id": 1,
        })
        assert response.status_code == 400

    def test_upsert_missing_channel_id(self, client_as_member):
        """Postman: Upsert - Missing Channel ID (400)."""
        response = client_as_member.post("/api/v1/channel_phone_number/upsert", json={
            "phone_number": "+1234567890",
            "phone_number_sid": "PN123",
            "provider": "twilio",
        })
        assert response.status_code == 400

    def test_upsert_empty_body(self, client_as_member):
        response = client_as_member.post("/api/v1/channel_phone_number/upsert", json={})
        assert response.status_code == 400

    def test_upsert_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/channel_phone_number/upsert", json={
            "phone_number": "+1234567890",
            "phone_number_sid": "PN123",
            "provider": "twilio",
            "channel_id": 1,
        })
        assert response.status_code in (401, 403)


# ─── GET /api/v1/channel_phone_number/list ───

class TestGetAllChannelPhoneNumbers:
    """Tests for GET /api/v1/channel_phone_number/list

    Postman examples:
      - Get All - Success (200)
    """

    def test_get_all_returns_200(self, client_as_member):
        """Postman: Get All - Success (200)."""
        response = client_as_member.get("/api/v1/channel_phone_number/list")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_all_with_channel_id_filter(self, client_as_member):
        """Optional channel_id filter."""
        channel = _get_or_create_channel(client_as_member, channel_type="twilio")
        response = client_as_member.get(f"/api/v1/channel_phone_number/list?channel_id={channel['id']}")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_all_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/channel_phone_number/list")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/channel_phone_number/get_by_channel ───

class TestGetPhoneNumbersByChannel:
    """Tests for GET /api/v1/channel_phone_number/get_by_channel?channel_id=

    Postman examples:
      - Get By Channel - Success (200)
    """

    def test_get_by_channel_success(self, client_as_member):
        """Postman: Get By Channel - Success (200)."""
        channel = _get_or_create_channel(client_as_member, channel_type="twilio")
        response = client_as_member.get(f"/api/v1/channel_phone_number/get_by_channel?channel_id={channel['id']}")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_by_channel_missing_channel_id(self, client_as_member):
        response = client_as_member.get("/api/v1/channel_phone_number/get_by_channel")
        assert response.status_code == 422

    def test_get_by_channel_invalid_channel_id(self, client_as_member):
        response = client_as_member.get("/api/v1/channel_phone_number/get_by_channel?channel_id=abc")
        assert response.status_code == 422

    def test_get_by_channel_not_found(self, client_as_member):
        """Non-existent channel_id returns empty list."""
        response = client_as_member.get("/api/v1/channel_phone_number/get_by_channel?channel_id=999999")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_by_channel_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/channel_phone_number/get_by_channel?channel_id=1")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/channel_phone_number/get ───

class TestGetChannelPhoneNumber:
    """Tests for GET /api/v1/channel_phone_number/get?phone_number_id=

    Postman examples:
      - Get - Success (200)
      - Get - Not Found (404)
    """

    def test_get_phone_number_not_found(self, client_as_member):
        """Postman: Get - Not Found (404)."""
        response = client_as_member.get("/api/v1/channel_phone_number/get?phone_number_id=999999")
        assert response.status_code in (404, 400)

    def test_get_phone_number_missing_id(self, client_as_member):
        response = client_as_member.get("/api/v1/channel_phone_number/get")
        assert response.status_code == 422

    def test_get_phone_number_invalid_id(self, client_as_member):
        response = client_as_member.get("/api/v1/channel_phone_number/get?phone_number_id=abc")
        assert response.status_code == 422

    def test_get_phone_number_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/channel_phone_number/get?phone_number_id=1")
        assert response.status_code in (401, 403)


# ─── DELETE /api/v1/channel_phone_number/delete ───

class TestDeleteChannelPhoneNumber:
    """Tests for DELETE /api/v1/channel_phone_number/delete?phone_number_id=

    Postman examples:
      - Delete - Success (200)
    """

    def test_delete_phone_number_missing_id(self, client_as_member):
        response = client_as_member.delete("/api/v1/channel_phone_number/delete")
        assert response.status_code == 422

    def test_delete_phone_number_invalid_id(self, client_as_member):
        response = client_as_member.delete("/api/v1/channel_phone_number/delete?phone_number_id=abc")
        assert response.status_code == 422

    def test_delete_phone_number_not_found(self, client_as_member):
        response = client_as_member.delete("/api/v1/channel_phone_number/delete?phone_number_id=999999")
        assert response.status_code in (404, 400)

    def test_delete_phone_number_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/channel_phone_number/delete?phone_number_id=1")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/channel_phone_number/get_twilio_phone_numbers ───

class TestGetTwilioPhoneNumbers:
    """Tests for GET /api/v1/channel_phone_number/get_twilio_phone_numbers?type=

    Postman examples:
      - Get Twilio Numbers - Success (200)
    """

    def test_get_twilio_numbers_missing_type(self, client_as_member):
        response = client_as_member.get("/api/v1/channel_phone_number/get_twilio_phone_numbers")
        assert response.status_code == 422

    def test_get_twilio_numbers_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/channel_phone_number/get_twilio_phone_numbers?type=twilio")
        assert response.status_code in (401, 403)

    def test_get_twilio_numbers_with_optional_params(self, client_as_member):
        """Optional channel_id and agent_id query params."""
        response = client_as_member.get(
            "/api/v1/channel_phone_number/get_twilio_phone_numbers?type=twilio&channel_id=1&agent_id=1"
        )
        assert response.status_code in (200, 400, 404)

    def test_get_twilio_numbers_invalid_type(self, client_as_member):
        """Invalid Channel Type."""
        response = client_as_member.get("/api/v1/channel_phone_number/get_twilio_phone_numbers?type=invalid_type")
        assert response.status_code in (200, 400, 404)


# ─── GET /api/v1/channel_phone_number/get_phone_number_list_to_buy ───

class TestGetPhoneNumberListToBuy:
    """Tests for GET /api/v1/channel_phone_number/get_phone_number_list_to_buy?type=

    Postman examples:
      - Get Numbers To Buy - Success (200)
    """

    def test_get_list_to_buy_missing_type(self, client_as_member):
        response = client_as_member.get("/api/v1/channel_phone_number/get_phone_number_list_to_buy")
        assert response.status_code == 422

    def test_get_list_to_buy_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/channel_phone_number/get_phone_number_list_to_buy?type=twilio")
        assert response.status_code in (401, 403)

    def test_get_list_to_buy_with_channel_id(self, client_as_member):
        """Optional channel_id param."""
        response = client_as_member.get(
            "/api/v1/channel_phone_number/get_phone_number_list_to_buy?type=twilio&channel_id=1"
        )
        assert response.status_code in (200, 400, 404)


# ─── POST /api/v1/channel_phone_number/buy_phone_number ───

class TestBuyPhoneNumber:
    """Tests for POST /api/v1/channel_phone_number/buy_phone_number

    Postman examples:
      - Buy Number - Success (200)
      - Buy Number - Missing Phone (400)
      - Buy Number - Missing Channel Name (400)
    """

    def test_buy_phone_number_missing_phone_number(self, client_as_member):
        """Postman: Buy Number - Missing Phone (400)."""
        response = client_as_member.post("/api/v1/channel_phone_number/buy_phone_number", json={
            "channel_name": "Main Twilio"
        })
        assert response.status_code == 400

    def test_buy_phone_number_missing_channel_name(self, client_as_member):
        """Postman: Buy Number - Missing Channel Name (400)."""
        response = client_as_member.post("/api/v1/channel_phone_number/buy_phone_number", json={
            "phone_number": "+15559876543"
        })
        assert response.status_code == 400

    def test_buy_phone_number_empty_body(self, client_as_member):
        response = client_as_member.post("/api/v1/channel_phone_number/buy_phone_number", json={})
        assert response.status_code == 400

    def test_buy_phone_number_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/channel_phone_number/buy_phone_number", json={
            "phone_number": "+15559876543", "channel_name": "Main Twilio"
        })
        assert response.status_code in (401, 403)

    def test_buy_phone_number_channel_not_found(self, client_as_member):
        """Channel Not Found when buying."""
        response = client_as_member.post("/api/v1/channel_phone_number/buy_phone_number", json={
            "phone_number": "+15559876543", "channel_name": "nonexistent-channel-xyz"
        })
        assert response.status_code in (400, 404)
