"""Tests for Agent Channel Phone Numbers API endpoints (Core edition).

Source: core/api/v1/agent_channel_phone_numbers.py
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_phone_number():
    return {
        "id": 1,
        "phone_number": "+1234567890",
        "phone_number_sid": "PN123",
        "phone_number_auth_token": "tok123",
        "provider": "twilio",
        "channel_id": 10,
    }


@pytest.fixture
def sample_phone_numbers(sample_phone_number):
    return [
        sample_phone_number,
        {
            "id": 2,
            "phone_number": "+0987654321",
            "phone_number_sid": "PN456",
            "phone_number_auth_token": "tok456",
            "provider": "twilio",
            "channel_id": 10,
        },
    ]


@pytest.fixture
def upsert_payload():
    return {
        "phone_number": "+1234567890",
        "phone_number_sid": "PN123",
        "phone_number_auth_token": "tok123",
        "provider": "twilio",
    }


@pytest.fixture
def detach_payload():
    return {"channel_id": 10, "phone_number": "+1234567890"}


# ---------------------------------------------------------------------------
# GET /api/v1/agent_channel_phone_number/get_channel_phone_numbers
# ---------------------------------------------------------------------------

class TestGetChannelPhoneNumbers:
    """Tests for GET /api/v1/agent_channel_phone_number/get_channel_phone_numbers"""

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_success(self, mock_service_cls, client_as_member, sample_phone_numbers):
        mock_service_cls.return_value.get_channel_phone_numbers.return_value = sample_phone_numbers
        resp = client_as_member.get(
            "/api/v1/agent_channel_phone_number/get_channel_phone_numbers",
            params={"channel_id": 10},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2
        mock_service_cls.return_value.get_channel_phone_numbers.assert_called_once_with(10)

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_channel_phone_numbers.return_value = []
        resp = client_as_member.get(
            "/api/v1/agent_channel_phone_number/get_channel_phone_numbers",
            params={"channel_id": 999},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_missing_channel_id(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/agent_channel_phone_number/get_channel_phone_numbers"
        )
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/agent_channel_phone_number/get_channel_phone_numbers",
            params={"channel_id": 10},
        )
        assert resp.status_code in (401, 403)

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_channel_phone_numbers.side_effect = HTTPException(status_code=500, detail="DB error")
        resp = client_as_member.get(
            "/api/v1/agent_channel_phone_number/get_channel_phone_numbers",
            params={"channel_id": 10},
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# POST /api/v1/agent_channel_phone_number/upsert_channel_phone_number
# ---------------------------------------------------------------------------

class TestUpsertChannelPhoneNumber:
    """Tests for POST /api/v1/agent_channel_phone_number/upsert_channel_phone_number"""

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_success(self, mock_service_cls, client_as_member, upsert_payload, sample_phone_number):
        mock_service_cls.return_value.upsert_channel_phone_numbers.return_value = (
            sample_phone_number
        )
        resp = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json=upsert_payload,
        )
        assert resp.status_code == 200
        mock_service_cls.return_value.upsert_channel_phone_numbers.assert_called_once_with(
            upsert_payload,
        )

    def test_missing_phone_number(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={"phone_number_sid": "PN1", "phone_number_auth_token": "tok", "provider": "twilio"},
        )
        assert resp.status_code == 400
        assert "phone_number" in resp.json()["detail"].lower()

    def test_missing_phone_number_sid(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={"phone_number": "+1", "phone_number_auth_token": "tok", "provider": "twilio"},
        )
        assert resp.status_code == 400
        assert "phone_number_sid" in resp.json()["detail"].lower()

    def test_missing_phone_number_auth_token(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={"phone_number": "+1", "phone_number_sid": "PN1", "provider": "twilio"},
        )
        assert resp.status_code == 400
        assert "phone_number_auth_token" in resp.json()["detail"].lower()

    def test_missing_provider(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={"phone_number": "+1", "phone_number_sid": "PN1", "phone_number_auth_token": "tok"},
        )
        assert resp.status_code == 400
        assert "provider" in resp.json()["detail"].lower()

    def test_unauthenticated(self, client_unauthenticated, upsert_payload):
        resp = client_unauthenticated.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json=upsert_payload,
        )
        assert resp.status_code in (401, 403)

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_service_error(self, mock_service_cls, client_as_member, upsert_payload):
        mock_service_cls.return_value.upsert_channel_phone_numbers.side_effect = Exception(
            "DB error"
        )
        resp = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json=upsert_payload,
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# POST /api/v1/agent_channel_phone_number/detach_channel_phone_number
# ---------------------------------------------------------------------------

class TestDetachChannelPhoneNumber:
    """Tests for POST /api/v1/agent_channel_phone_number/detach_channel_phone_number"""

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_success(self, mock_service_cls, client_as_member, detach_payload):
        mock_service_cls.return_value.detach_channel_phone_number.return_value = {
            "message": "detached"
        }
        resp = client_as_member.post(
            "/api/v1/agent_channel_phone_number/detach_channel_phone_number",
            json=detach_payload,
        )
        assert resp.status_code == 200
        mock_service_cls.return_value.detach_channel_phone_number.assert_called_once_with(
            detach_payload,
        )

    def test_missing_channel_id(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent_channel_phone_number/detach_channel_phone_number",
            json={"phone_number": "+1234567890"},
        )
        assert resp.status_code == 400
        assert "channel_id" in resp.json()["detail"].lower()

    def test_missing_phone_number(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent_channel_phone_number/detach_channel_phone_number",
            json={"channel_id": 10},
        )
        assert resp.status_code == 400
        assert "phone_number" in resp.json()["detail"].lower()

    def test_unauthenticated(self, client_unauthenticated, detach_payload):
        resp = client_unauthenticated.post(
            "/api/v1/agent_channel_phone_number/detach_channel_phone_number",
            json=detach_payload,
        )
        assert resp.status_code in (401, 403)

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_service_error(self, mock_service_cls, client_as_member, detach_payload):
        mock_service_cls.return_value.detach_channel_phone_number.side_effect = Exception(
            "DB error"
        )
        resp = client_as_member.post(
            "/api/v1/agent_channel_phone_number/detach_channel_phone_number",
            json=detach_payload,
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/agent_channel_phone_number/get_assigned_phone_numbers
# ---------------------------------------------------------------------------

class TestGetAssignedPhoneNumbers:
    """Tests for GET /api/v1/agent_channel_phone_number/get_assigned_phone_numbers"""

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_success(self, mock_service_cls, client_as_member, sample_phone_numbers):
        mock_service_cls.return_value.get_assigned_phone_numbers.return_value = sample_phone_numbers
        resp = client_as_member.get(
            "/api/v1/agent_channel_phone_number/get_assigned_phone_numbers"
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_assigned_phone_numbers.return_value = []
        resp = client_as_member.get(
            "/api/v1/agent_channel_phone_number/get_assigned_phone_numbers"
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/agent_channel_phone_number/get_assigned_phone_numbers"
        )
        assert resp.status_code in (401, 403)

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_assigned_phone_numbers.side_effect = Exception(
            "DB error"
        )
        resp = client_as_member.get(
            "/api/v1/agent_channel_phone_number/get_assigned_phone_numbers"
        )
        assert resp.status_code in (500, 422, 400)
