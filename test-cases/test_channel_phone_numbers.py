"""Tests for Channel Phone Numbers API endpoints.

Source: core/api/v1/channel_phone_numbers.py
"""

import pytest
from uuid import UUID
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException

EXPECTED_ORG_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


# ─── Fixtures ───

@pytest.fixture
def sample_phone_number_data():
    return {
        "phone_number": "+15551234567",
        "phone_number_sid": "PN_sid_123",
        "phone_number_auth_token": "auth_token_abc",
        "provider": "twilio",
        "channel_id": 1,
    }


# ─── GET /api/v1/agent_channel_phone_number/get_channel_phone_numbers ───

class TestGetChannelPhoneNumbers:
    """Tests for GET /api/v1/agent_channel_phone_number/get_channel_phone_numbers"""

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_get_phone_numbers_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_channel_phone_numbers.return_value = [
            {"id": 1, "phone_number": "+15551234567"}
        ]
        response = client_as_member.get("/api/v1/agent_channel_phone_number/get_channel_phone_numbers?channel_id=1")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_get_phone_numbers_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_channel_phone_numbers.return_value = []
        response = client_as_member.get("/api/v1/agent_channel_phone_number/get_channel_phone_numbers?channel_id=1")
        assert response.status_code == 200
        assert response.json() == []

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

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_upsert_phone_number_success(self, mock_service_cls, client_as_member, sample_phone_number_data):
        mock_service_cls.return_value.upsert_channel_phone_numbers.return_value = {"id": 1}
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json=sample_phone_number_data
        )
        assert response.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_upsert_phone_number_missing_phone_number(self, mock_service_cls, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={"phone_number_sid": "sid", "phone_number_auth_token": "tok", "provider": "twilio"}
        )
        assert response.status_code == 400
        assert "phone_number is required" in response.json()["detail"]

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_upsert_phone_number_missing_sid(self, mock_service_cls, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={"phone_number": "+15551234567", "phone_number_auth_token": "tok", "provider": "twilio"}
        )
        assert response.status_code == 400
        assert "phone_number_sid is required" in response.json()["detail"]

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_upsert_phone_number_missing_auth_token(self, mock_service_cls, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={"phone_number": "+15551234567", "phone_number_sid": "sid", "provider": "twilio"}
        )
        assert response.status_code == 400
        assert "phone_number_auth_token is required" in response.json()["detail"]

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_upsert_phone_number_missing_provider(self, mock_service_cls, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/upsert_channel_phone_number",
            json={"phone_number": "+15551234567", "phone_number_sid": "sid", "phone_number_auth_token": "tok"}
        )
        assert response.status_code == 400
        assert "provider is required" in response.json()["detail"]

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_upsert_phone_number_empty_body(self, mock_service_cls, client_as_member):
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


# ─── POST /api/v1/agent_channel_phone_number/detach_channel_phone_number ───

class TestDetachChannelPhoneNumber:
    """Tests for POST /api/v1/agent_channel_phone_number/detach_channel_phone_number"""

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_detach_phone_number_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.detach_channel_phone_number.return_value = {"message": "detached"}
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/detach_channel_phone_number",
            json={"channel_id": 1, "phone_number": "+15551234567"}
        )
        assert response.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_detach_phone_number_missing_channel_id(self, mock_service_cls, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/detach_channel_phone_number",
            json={"phone_number": "+15551234567"}
        )
        assert response.status_code == 400
        assert "channel_id is required" in response.json()["detail"]

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_detach_phone_number_missing_phone_number(self, mock_service_cls, client_as_member):
        response = client_as_member.post(
            "/api/v1/agent_channel_phone_number/detach_channel_phone_number",
            json={"channel_id": 1}
        )
        assert response.status_code == 400
        assert "phone_number is required" in response.json()["detail"]

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_detach_phone_number_empty_body(self, mock_service_cls, client_as_member):
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

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_get_assigned_numbers_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_assigned_phone_numbers.return_value = [
            {"phone_number": "+15551234567", "channel_id": 1}
        ]
        response = client_as_member.get("/api/v1/agent_channel_phone_number/get_assigned_phone_numbers")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_get_assigned_numbers_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_assigned_phone_numbers.return_value = []
        response = client_as_member.get("/api/v1/agent_channel_phone_number/get_assigned_phone_numbers")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_assigned_numbers_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/agent_channel_phone_number/get_assigned_phone_numbers")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/channel_phone_number/get_twilio_phone_numbers ───

class TestGetTwilioPhoneNumbers:
    """Tests for GET /api/v1/channel_phone_number/get_twilio_phone_numbers"""

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_get_twilio_numbers_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_twilio_phone_numbers.return_value = [
            {"phone_number": "+15551234567", "friendly_name": "Main"}
        ]
        response = client_as_member.get("/api/v1/channel_phone_number/get_twilio_phone_numbers?type=twilio")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_get_twilio_numbers_with_channel_id(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_twilio_phone_numbers.return_value = []
        response = client_as_member.get(
            "/api/v1/channel_phone_number/get_twilio_phone_numbers?type=twilio&channel_id=1"
        )
        assert response.status_code == 200

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_get_twilio_numbers_with_agent_id(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_twilio_phone_numbers.return_value = []
        response = client_as_member.get(
            "/api/v1/channel_phone_number/get_twilio_phone_numbers?type=twilio&agent_id=1"
        )
        assert response.status_code == 200

    def test_get_twilio_numbers_missing_type(self, client_as_member):
        response = client_as_member.get("/api/v1/channel_phone_number/get_twilio_phone_numbers")
        assert response.status_code == 422

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_get_twilio_numbers_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_twilio_phone_numbers.return_value = []
        response = client_as_member.get("/api/v1/channel_phone_number/get_twilio_phone_numbers?type=twilio")
        assert response.status_code == 200
        assert response.json() == []

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_get_twilio_numbers_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_twilio_phone_numbers.side_effect = HTTPException(
            status_code=400, detail="Invalid channel credentials"
        )
        response = client_as_member.get("/api/v1/channel_phone_number/get_twilio_phone_numbers?type=twilio")
        assert response.status_code == 400

    def test_get_twilio_numbers_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/channel_phone_number/get_twilio_phone_numbers?type=twilio")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/channel_phone_number/get_phone_number_list_to_buy ───

class TestGetPhoneNumberListToBuy:
    """Tests for GET /api/v1/channel_phone_number/get_phone_number_list_to_buy"""

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_get_list_to_buy_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_phone_number_list_to_buy.return_value = [
            {"phone_number": "+15559876543", "monthly_cost": "1.00"}
        ]
        response = client_as_member.get("/api/v1/channel_phone_number/get_phone_number_list_to_buy?type=twilio")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        # This endpoint uses AgentChannelPhoneNumbersService(db) without org_id
        mock_service_cls.assert_called_once_with(ANY)

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_get_list_to_buy_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_phone_number_list_to_buy.return_value = []
        response = client_as_member.get("/api/v1/channel_phone_number/get_phone_number_list_to_buy?type=twilio")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_list_to_buy_missing_type(self, client_as_member):
        response = client_as_member.get("/api/v1/channel_phone_number/get_phone_number_list_to_buy")
        assert response.status_code == 422

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_get_list_to_buy_invalid_channel_type(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_phone_number_list_to_buy.side_effect = HTTPException(
            status_code=400, detail="Invalid channel type"
        )
        response = client_as_member.get("/api/v1/channel_phone_number/get_phone_number_list_to_buy?type=invalid")
        assert response.status_code == 400

    def test_get_list_to_buy_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/channel_phone_number/get_phone_number_list_to_buy?type=twilio")
        assert response.status_code in (401, 403)


# ─── POST /api/v1/channel_phone_number/buy_phone_number ───

class TestBuyPhoneNumber:
    """Tests for POST /api/v1/channel_phone_number/buy_phone_number"""

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_buy_phone_number_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.buy_phone_number.return_value = {
            "phone_number": "+15559876543", "message": "purchased"
        }
        response = client_as_member.post("/api/v1/channel_phone_number/buy_phone_number", json={
            "phone_number": "+15559876543",
            "channel_name": "Main Twilio"
        })
        assert response.status_code == 200
        # This endpoint uses AgentChannelPhoneNumbersService(db) without org_id
        mock_service_cls.assert_called_once_with(ANY)

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_buy_phone_number_missing_phone_number(self, mock_service_cls, client_as_member):
        response = client_as_member.post("/api/v1/channel_phone_number/buy_phone_number", json={
            "channel_name": "Main Twilio"
        })
        assert response.status_code == 400
        assert "phone_number" in response.json()["detail"]

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_buy_phone_number_missing_channel_name(self, mock_service_cls, client_as_member):
        response = client_as_member.post("/api/v1/channel_phone_number/buy_phone_number", json={
            "phone_number": "+15559876543"
        })
        assert response.status_code == 400
        assert "channel_name" in response.json()["detail"]

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_buy_phone_number_empty_body(self, mock_service_cls, client_as_member):
        response = client_as_member.post("/api/v1/channel_phone_number/buy_phone_number", json={})
        assert response.status_code == 400

    @patch("ee.api.v1.agent_channel_phone_numbers.AgentChannelPhoneNumbersService")
    def test_buy_phone_number_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.buy_phone_number.side_effect = HTTPException(
            status_code=400, detail="Missing Twilio credentials"
        )
        response = client_as_member.post("/api/v1/channel_phone_number/buy_phone_number", json={
            "phone_number": "+15559876543",
            "channel_name": "Main Twilio"
        })
        assert response.status_code == 400

    def test_buy_phone_number_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/channel_phone_number/buy_phone_number", json={
            "phone_number": "+15559876543",
            "channel_name": "Main Twilio"
        })
        assert response.status_code in (401, 403)
