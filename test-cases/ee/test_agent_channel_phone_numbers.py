"""Tests for Agent Channel Phone Numbers API endpoints (EE edition).

Source: ee/api/v1/agent_channel_phone_numbers.py
Integration tests — real DB, real endpoints, no mocks.
"""

import pytest


# ─── GET /api/v1/agent_channel_phone_number/get_channel_phone_numbers ───

class TestGetChannelPhoneNumbers:
    """Tests for GET /api/v1/agent_channel_phone_number/get_channel_phone_numbers"""

    def test_missing_channel_id(self, client_as_member):
        response = client_as_member.get(
            "/api/v1/agent_channel_phone_number/get_channel_phone_numbers"
        )
        assert response.status_code == 422

    def test_invalid_channel_id(self, client_as_member):
        response = client_as_member.get(
            "/api/v1/agent_channel_phone_number/get_channel_phone_numbers?channel_id=abc"
        )
        assert response.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get(
            "/api/v1/agent_channel_phone_number/get_channel_phone_numbers?channel_id=1"
        )
        assert response.status_code in (401, 403)


# ─── POST /api/v1/agent_channel_phone_number/upsert_channel_phone_number ───

class TestUpsertChannelPhoneNumber:
    """Tests for POST /api/v1/agent_channel_phone_number/upsert_channel_phone_number"""

    def test_missing_phone_number(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={"phone_number_sid": "sid", "phone_number_auth_token": "tok", "provider": "twilio"},
        )
        assert response.status_code == 400

    def test_missing_phone_number_sid(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={"phone_number": "+15551234567", "phone_number_auth_token": "tok", "provider": "twilio"},
        )
        assert response.status_code == 400

    def test_missing_phone_number_auth_token(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={"phone_number": "+15551234567", "phone_number_sid": "sid", "provider": "twilio"},
        )
        assert response.status_code == 400

    def test_missing_provider(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={"phone_number": "+15551234567", "phone_number_sid": "sid", "phone_number_auth_token": "tok"},
        )
        assert response.status_code == 400

    def test_empty_body(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={},
        )
        assert response.status_code == 400

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={"phone_number": "+15551234567", "phone_number_sid": "s", "phone_number_auth_token": "t", "provider": "twilio"},
        )
        assert response.status_code in (401, 403)


# ─── POST /api/v1/agent_channel_phone_number/detach_channel_phone_number ───

class TestDetachChannelPhoneNumber:
    """Tests for POST /api/v1/agent_channel_phone_number/detach_channel_phone_number"""

    def test_missing_channel_id(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/detach_channel_phone_number",
            json={"phone_number": "+15551234567"},
        )
        assert response.status_code == 400

    def test_missing_phone_number(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/detach_channel_phone_number",
            json={"channel_id": 1},
        )
        assert response.status_code == 400

    def test_empty_body(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/detach_channel_phone_number",
            json={},
        )
        assert response.status_code == 400

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post(
            "/api/v1/agent_channel_phone_number/detach_channel_phone_number",
            json={"channel_id": 1, "phone_number": "+15551234567"},
        )
        assert response.status_code in (401, 403)


# ─── GET /api/v1/agent_channel_phone_number/get_assigned_phone_numbers ───

class TestGetAssignedPhoneNumbers:
    """Tests for GET /api/v1/agent_channel_phone_number/get_assigned_phone_numbers"""

    def test_returns_200(self, client_as_member):
        response = client_as_member.get(
            "/api/v1/agent_channel_phone_number/get_assigned_phone_numbers"
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get(
            "/api/v1/agent_channel_phone_number/get_assigned_phone_numbers"
        )
        assert response.status_code in (401, 403)
