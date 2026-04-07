"""Tests for Agent Channel Phone Numbers API endpoints (EE edition).

Source: ee/api/v1/agent_channel_phone_numbers.py
"""

import pytest
from uuid import UUID
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException

EXPECTED_ORG_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


# --- Fixtures ---

@pytest.fixture
def sample_phone_data():
    return {
        "phone_number": "+15551234567",
        "phone_number_sid": "PN_sid_123",
        "phone_number_auth_token": "auth_token_abc",
        "provider": "twilio",
    }


# --- GET /api/v1/agent_channel_phone_number/get_channel_phone_numbers ---

class TestGetChannelPhoneNumbers:
    """Tests for GET /api/v1/agent_channel_phone_number/get_channel_phone_numbers"""

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_success(self, mock_svc, client_as_member):
        mock_svc.return_value.get_channel_phone_numbers.return_value = [{"id": 1}]
        response = client_as_member.get(
            "/api/v1/agent_channel_phone_number/get_channel_phone_numbers?channel_id=1"
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        mock_svc.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_empty_result(self, mock_svc, client_as_member):
        mock_svc.return_value.get_channel_phone_numbers.return_value = []
        response = client_as_member.get(
            "/api/v1/agent_channel_phone_number/get_channel_phone_numbers?channel_id=1"
        )
        assert response.status_code == 200
        assert response.json() == []

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


# --- POST /api/v1/agent_channel_phone_number/upsert_channel_phone_number ---

class TestUpsertChannelPhoneNumber:
    """Tests for POST /api/v1/agent_channel_phone_number/upsert_channel_phone_number"""

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_success(self, mock_svc, client_as_member, sample_phone_data):
        mock_svc.return_value.upsert_channel_phone_numbers.return_value = {"id": 1}
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json=sample_phone_data,
        )
        assert response.status_code == 200
        mock_svc.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_missing_phone_number(self, mock_svc, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={
                "phone_number_sid": "sid",
                "phone_number_auth_token": "tok",
                "provider": "twilio",
            },
        )
        assert response.status_code == 400
        assert "phone_number is required" in response.json()["detail"]

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_missing_phone_number_sid(self, mock_svc, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={
                "phone_number": "+15551234567",
                "phone_number_auth_token": "tok",
                "provider": "twilio",
            },
        )
        assert response.status_code == 400
        assert "phone_number_sid is required" in response.json()["detail"]

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_missing_phone_number_auth_token(self, mock_svc, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={
                "phone_number": "+15551234567",
                "phone_number_sid": "sid",
                "provider": "twilio",
            },
        )
        assert response.status_code == 400
        assert "phone_number_auth_token is required" in response.json()["detail"]

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_missing_provider(self, mock_svc, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={
                "phone_number": "+15551234567",
                "phone_number_sid": "sid",
                "phone_number_auth_token": "tok",
            },
        )
        assert response.status_code == 400
        assert "provider is required" in response.json()["detail"]

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_empty_body(self, mock_svc, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={},
        )
        assert response.status_code == 400

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_service_error(self, mock_svc, client_as_member, sample_phone_data):
        mock_svc.return_value.upsert_channel_phone_numbers.side_effect = HTTPException(
            status_code=500, detail="Internal error"
        )
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json=sample_phone_data,
        )
        assert response.status_code == 500

    def test_unauthenticated(self, client_unauthenticated, sample_phone_data):
        response = client_unauthenticated.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json=sample_phone_data,
        )
        assert response.status_code in (401, 403)


# --- POST /api/v1/agent_channel_phone_number/detach_channel_phone_number ---

class TestDetachChannelPhoneNumber:
    """Tests for POST /api/v1/agent_channel_phone_number/detach_channel_phone_number"""

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_success(self, mock_svc, client_as_member):
        mock_svc.return_value.detach_channel_phone_number.return_value = {"message": "detached"}
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/detach_channel_phone_number",
            json={"channel_id": 1, "phone_number": "+15551234567"},
        )
        assert response.status_code == 200
        mock_svc.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_missing_channel_id(self, mock_svc, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/detach_channel_phone_number",
            json={"phone_number": "+15551234567"},
        )
        assert response.status_code == 400
        assert "channel_id is required" in response.json()["detail"]

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_missing_phone_number(self, mock_svc, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/detach_channel_phone_number",
            json={"channel_id": 1},
        )
        assert response.status_code == 400
        assert "phone_number is required" in response.json()["detail"]

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_empty_body(self, mock_svc, client_as_member):
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


# --- GET /api/v1/agent_channel_phone_number/get_assigned_phone_numbers ---

class TestGetAssignedPhoneNumbers:
    """Tests for GET /api/v1/agent_channel_phone_number/get_assigned_phone_numbers"""

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_success(self, mock_svc, client_as_member):
        mock_svc.return_value.get_assigned_phone_numbers.return_value = [
            {"phone_number": "+15551234567", "channel_id": 1}
        ]
        response = client_as_member.get(
            "/api/v1/agent_channel_phone_number/get_assigned_phone_numbers"
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        mock_svc.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_empty_list(self, mock_svc, client_as_member):
        mock_svc.return_value.get_assigned_phone_numbers.return_value = []
        response = client_as_member.get(
            "/api/v1/agent_channel_phone_number/get_assigned_phone_numbers"
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get(
            "/api/v1/agent_channel_phone_number/get_assigned_phone_numbers"
        )
        assert response.status_code in (401, 403)
