"""Tests for Channel Phone Numbers API endpoints (EE edition).

Source: ee/api/v1/channel_phone_numbers.py, ee/api/v1/agent_channel_phone_numbers.py
Integration tests — real DB, real endpoints, no mocks.
"""

import pytest
import uuid


# ─── Helpers ───

def _get_or_create_channel(client, channel_type="twilio"):
    """Get an existing channel of the given type, or create one. Returns JSON."""
    # Try to get existing channel of this type (one per type constraint)
    resp = client.get(f"/api/v1/channel/get_by_type?type={channel_type}")
    if resp.status_code == 200:
        return resp.json()
    # Create new
    data = {
        "name": f"test-channel-{uuid.uuid4().hex[:8]}",
        "type": channel_type,
        "meta_data": {"account_sid": "ACtest", "auth_token": "authtest"},
    }
    resp = client.post("/api/v1/channel/upsert", json=data)
    assert resp.status_code == 200
    return resp.json()


# ─── GET /api/v1/agent_channel_phone_number/get_channel_phone_numbers ───

class TestGetChannelPhoneNumbers:
    """Tests for GET /api/v1/agent_channel_phone_number/get_channel_phone_numbers"""

    def test_get_phone_numbers_missing_channel_id(self, client_as_member):
        response = client_as_member.get("/api/v1/agent_channel_phone_number/get_channel_phone_numbers")
        assert response.status_code == 422

    def test_get_phone_numbers_invalid_channel_id(self, client_as_member):
        response = client_as_member.get("/api/v1/agent_channel_phone_number/get_channel_phone_numbers?channel_id=abc")
        assert response.status_code == 422

    def test_get_phone_numbers_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/agent_channel_phone_number/get_channel_phone_numbers?channel_id=1")
        assert response.status_code in (401, 403)


# ─── POST /api/v1/agent_channel_phone_number/upsert_channel_phone_number ───

class TestUpsertChannelPhoneNumber:
    """Tests for POST /api/v1/agent_channel_phone_number/upsert_channel_phone_number"""

    def test_upsert_phone_number_missing_phone_number(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={"phone_number_sid": "sid", "phone_number_auth_token": "tok", "provider": "twilio"}
        )
        assert response.status_code == 400

    def test_upsert_phone_number_missing_sid(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={"phone_number": "+15551234567", "phone_number_auth_token": "tok", "provider": "twilio"}
        )
        assert response.status_code == 400

    def test_upsert_phone_number_missing_auth_token(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={"phone_number": "+15551234567", "phone_number_sid": "sid", "provider": "twilio"}
        )
        assert response.status_code == 400

    def test_upsert_phone_number_missing_provider(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={"phone_number": "+15551234567", "phone_number_sid": "sid", "phone_number_auth_token": "tok"}
        )
        assert response.status_code == 400

    def test_upsert_phone_number_empty_body(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number", json={}
        )
        assert response.status_code == 400

    def test_upsert_phone_number_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={"phone_number": "+15551234567", "phone_number_sid": "s", "phone_number_auth_token": "t", "provider": "twilio"}
        )
        assert response.status_code in (401, 403)

    def test_upsert_phone_number_missing_channel_id(self, client_as_member):
        """Postman: Missing channel_id — API accepts null channel_id."""
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={
                "phone_number": f"+1555{uuid.uuid4().hex[:7]}",
                "phone_number_sid": "sid123",
                "phone_number_auth_token": "tok123",
                "provider": "twilio",
            }
        )
        assert response.status_code in (200, 409)

    def test_upsert_phone_number_channel_not_found(self, client_as_member):
        """Postman: Channel Not Found (channel_id=999999)."""
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={
                "phone_number": "+15551234567",
                "phone_number_sid": "sid123",
                "phone_number_auth_token": "tok123",
                "provider": "twilio",
                "channel_id": 999999,
            }
        )
        assert response.status_code in (400, 404)

    def test_upsert_twilio_with_new_fields(self, client_as_member):
        """Postman: Create Twilio Phone Number with country_code, number_type, capabilities."""
        channel = _get_or_create_channel(client_as_member, channel_type="twilio")
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={
                "phone_number": f"+1555{uuid.uuid4().hex[:7]}",
                "phone_number_sid": f"PN{uuid.uuid4().hex[:10]}",
                "phone_number_auth_token": "auth_token_test",
                "provider": "twilio",
                "channel_id": channel["id"],
                "country_code": "US",
                "number_type": "local",
                "friendly_name": "Test Number",
                "capabilities": {"voice": True, "sms": True, "mms": False},
            }
        )
        assert response.status_code in (200, 400, 409)

    def test_upsert_exotel_phone_number(self, client_as_member):
        """Postman: Create Exotel Phone Number."""
        channel = _get_or_create_channel(client_as_member, channel_type="exotel")
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={
                "phone_number": f"+91{uuid.uuid4().hex[:10]}",
                "phone_number_sid": f"exo{uuid.uuid4().hex[:8]}",
                "phone_number_auth_token": "exo_auth",
                "provider": "exotel",
                "channel_id": channel["id"],
                "country_code": "IN",
                "number_type": "virtual",
            }
        )
        assert response.status_code in (200, 400, 409)


# ─── POST /api/v1/agent_channel_phone_number/detach_channel_phone_number ───

class TestDetachChannelPhoneNumber:
    """Tests for POST /api/v1/agent_channel_phone_number/detach_channel_phone_number"""

    def test_detach_phone_number_missing_channel_id(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/detach_channel_phone_number",
            json={"phone_number": "+15551234567"}
        )
        assert response.status_code == 400

    def test_detach_phone_number_missing_phone_number(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/detach_channel_phone_number",
            json={"channel_id": 1}
        )
        assert response.status_code == 400

    def test_detach_phone_number_empty_body(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/detach_channel_phone_number", json={}
        )
        assert response.status_code == 400

    def test_detach_phone_number_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post(
            "/api/v1/agent_channel_phone_number/detach_channel_phone_number",
            json={"channel_id": 1, "phone_number": "+15551234567"}
        )
        assert response.status_code in (401, 403)


# ─── GET /api/v1/agent_channel_phone_number/get_assigned_phone_numbers ───

class TestGetAssignedPhoneNumbers:
    """Tests for GET /api/v1/agent_channel_phone_number/get_assigned_phone_numbers"""

    def test_get_assigned_numbers_returns_200(self, client_as_member):
        response = client_as_member.get("/api/v1/agent_channel_phone_number/get_assigned_phone_numbers")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_assigned_numbers_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/agent_channel_phone_number/get_assigned_phone_numbers")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/channel_phone_number/get ───

class TestGetChannelPhoneNumber:
    """Tests for GET /api/v1/channel_phone_number/get"""

    def test_get_phone_number_missing_id(self, client_as_member):
        response = client_as_member.get("/api/v1/channel_phone_number/get")
        assert response.status_code == 422

    def test_get_phone_number_invalid_id(self, client_as_member):
        response = client_as_member.get("/api/v1/channel_phone_number/get?phone_number_id=abc")
        assert response.status_code == 422

    def test_get_phone_number_not_found(self, client_as_member):
        response = client_as_member.get("/api/v1/channel_phone_number/get?phone_number_id=999999")
        assert response.status_code in (404, 400)

    def test_get_phone_number_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/channel_phone_number/get?phone_number_id=1")
        assert response.status_code in (401, 403)


# ─── DELETE /api/v1/channel_phone_number/delete ───

class TestDeleteChannelPhoneNumber:
    """Tests for DELETE /api/v1/channel_phone_number/delete"""

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
    """Tests for GET /api/v1/channel_phone_number/get_twilio_phone_numbers"""

    def test_get_twilio_numbers_missing_type(self, client_as_member):
        response = client_as_member.get("/api/v1/channel_phone_number/get_twilio_phone_numbers")
        assert response.status_code == 422

    def test_get_twilio_numbers_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/channel_phone_number/get_twilio_phone_numbers?type=twilio")
        assert response.status_code in (401, 403)

    def test_get_twilio_numbers_invalid_type(self, client_as_member):
        """Postman: Invalid Channel Type."""
        response = client_as_member.get("/api/v1/channel_phone_number/get_twilio_phone_numbers?type=invalid_type")
        assert response.status_code in (200, 400, 404)


# ─── GET /api/v1/channel_phone_number/get_phone_number_list_to_buy ───

class TestGetPhoneNumberListToBuy:
    """Tests for GET /api/v1/channel_phone_number/get_phone_number_list_to_buy"""

    def test_get_list_to_buy_missing_type(self, client_as_member):
        response = client_as_member.get("/api/v1/channel_phone_number/get_phone_number_list_to_buy")
        assert response.status_code == 422

    def test_get_list_to_buy_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/channel_phone_number/get_phone_number_list_to_buy?type=twilio")
        assert response.status_code in (401, 403)


# ─── POST /api/v1/channel_phone_number/buy_phone_number ───

class TestBuyPhoneNumber:
    """Tests for POST /api/v1/channel_phone_number/buy_phone_number"""

    def test_buy_phone_number_missing_phone_number(self, client_as_member):
        response = client_as_member.post("/api/v1/channel_phone_number/buy_phone_number", json={
            "channel_name": "Main Twilio"
        })
        assert response.status_code == 400

    def test_buy_phone_number_missing_channel_name(self, client_as_member):
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
        """Postman: Channel Not Found when buying."""
        response = client_as_member.post("/api/v1/channel_phone_number/buy_phone_number", json={
            "phone_number": "+15559876543", "channel_name": "nonexistent-channel-xyz"
        })
        assert response.status_code in (400, 404)
