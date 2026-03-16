"""Tests for Channel Phone Numbers API endpoints.

Source: core/api/v1/channel_phone_numbers.py
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


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


# ─── GET /api/v1/channel_phone_number/get_channel_phone_numbers ───

class TestGetChannelPhoneNumbers:
    """Tests for GET /api/v1/channel_phone_number/get_channel_phone_numbers"""

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_get_phone_numbers_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_channel_phone_numbers.return_value = [
            {"id": 1, "phone_number": "+15551234567"}
        ]
        response = client_as_member.get("/api/v1/channel_phone_number/get_channel_phone_numbers?channel_id=1")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_get_phone_numbers_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_channel_phone_numbers.return_value = []
        response = client_as_member.get("/api/v1/channel_phone_number/get_channel_phone_numbers?channel_id=1")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_phone_numbers_missing_channel_id(self, client_as_member):
        response = client_as_member.get("/api/v1/channel_phone_number/get_channel_phone_numbers")
        assert response.status_code == 422

    def test_get_phone_numbers_invalid_channel_id(self, client_as_member):
        response = client_as_member.get("/api/v1/channel_phone_number/get_channel_phone_numbers?channel_id=abc")
        assert response.status_code == 422

    def test_get_phone_numbers_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/channel_phone_number/get_channel_phone_numbers?channel_id=1")
        assert response.status_code in (401, 403)


# ─── POST /api/v1/channel_phone_number/upsert_channel_phone_number ───

class TestUpsertChannelPhoneNumber:
    """Tests for POST /api/v1/channel_phone_number/upsert_channel_phone_number"""

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_upsert_phone_number_success(self, mock_service_cls, client_as_member, sample_phone_number_data):
        mock_service_cls.return_value.upsert_channel_phone_numbers.return_value = {"id": 1}
        response = client_as_member.post(
            "/api/v1/channel_phone_number/upsert_channel_phone_number",
            json=sample_phone_number_data
        )
        assert response.status_code == 200

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_upsert_phone_number_missing_phone_number(self, mock_service_cls, client_as_member):
        response = client_as_member.post(
            "/api/v1/channel_phone_number/upsert_channel_phone_number",
            json={"phone_number_sid": "sid", "phone_number_auth_token": "tok", "provider": "twilio"}
        )
        assert response.status_code == 400
        assert "phone_number is required" in response.json()["detail"]

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_upsert_phone_number_missing_sid(self, mock_service_cls, client_as_member):
        response = client_as_member.post(
            "/api/v1/channel_phone_number/upsert_channel_phone_number",
            json={"phone_number": "+15551234567", "phone_number_auth_token": "tok", "provider": "twilio"}
        )
        assert response.status_code == 400
        assert "phone_number_sid is required" in response.json()["detail"]

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_upsert_phone_number_missing_auth_token(self, mock_service_cls, client_as_member):
        response = client_as_member.post(
            "/api/v1/channel_phone_number/upsert_channel_phone_number",
            json={"phone_number": "+15551234567", "phone_number_sid": "sid", "provider": "twilio"}
        )
        assert response.status_code == 400
        assert "phone_number_auth_token is required" in response.json()["detail"]

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_upsert_phone_number_missing_provider(self, mock_service_cls, client_as_member):
        response = client_as_member.post(
            "/api/v1/channel_phone_number/upsert_channel_phone_number",
            json={"phone_number": "+15551234567", "phone_number_sid": "sid", "phone_number_auth_token": "tok"}
        )
        assert response.status_code == 400
        assert "provider is required" in response.json()["detail"]

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_upsert_phone_number_empty_body(self, mock_service_cls, client_as_member):
        response = client_as_member.post(
            "/api/v1/channel_phone_number/upsert_channel_phone_number", json={}
        )
        assert response.status_code == 400

    def test_upsert_phone_number_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post(
            "/api/v1/channel_phone_number/upsert_channel_phone_number",
            json={"phone_number": "+15551234567", "phone_number_sid": "s", "phone_number_auth_token": "t", "provider": "twilio"}
        )
        assert response.status_code in (401, 403)


# ─── POST /api/v1/channel_phone_number/detach_channel_phone_number ───

class TestDetachChannelPhoneNumber:
    """Tests for POST /api/v1/channel_phone_number/detach_channel_phone_number"""

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_detach_phone_number_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.detach_channel_phone_number.return_value = {"message": "detached"}
        response = client_as_member.post(
            "/api/v1/channel_phone_number/detach_channel_phone_number",
            json={"channel_id": 1, "phone_number": "+15551234567"}
        )
        assert response.status_code == 200

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_detach_phone_number_missing_channel_id(self, mock_service_cls, client_as_member):
        response = client_as_member.post(
            "/api/v1/channel_phone_number/detach_channel_phone_number",
            json={"phone_number": "+15551234567"}
        )
        assert response.status_code == 400
        assert "channel_id is required" in response.json()["detail"]

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_detach_phone_number_missing_phone_number(self, mock_service_cls, client_as_member):
        response = client_as_member.post(
            "/api/v1/channel_phone_number/detach_channel_phone_number",
            json={"channel_id": 1}
        )
        assert response.status_code == 400
        assert "phone_number is required" in response.json()["detail"]

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_detach_phone_number_empty_body(self, mock_service_cls, client_as_member):
        response = client_as_member.post(
            "/api/v1/channel_phone_number/detach_channel_phone_number", json={}
        )
        assert response.status_code == 400

    def test_detach_phone_number_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post(
            "/api/v1/channel_phone_number/detach_channel_phone_number",
            json={"channel_id": 1, "phone_number": "+15551234567"}
        )
        assert response.status_code in (401, 403)


# ─── GET /api/v1/channel_phone_number/get_assigned_phone_numbers ───

class TestGetAssignedPhoneNumbers:
    """Tests for GET /api/v1/channel_phone_number/get_assigned_phone_numbers"""

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_get_assigned_numbers_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_assigned_phone_numbers.return_value = [
            {"phone_number": "+15551234567", "channel_id": 1}
        ]
        response = client_as_member.get("/api/v1/channel_phone_number/get_assigned_phone_numbers")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_get_assigned_numbers_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_assigned_phone_numbers.return_value = []
        response = client_as_member.get("/api/v1/channel_phone_number/get_assigned_phone_numbers")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_assigned_numbers_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/channel_phone_number/get_assigned_phone_numbers")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/channel_phone_number/get_twilio_phone_numbers ───

class TestGetTwilioPhoneNumbers:
    """Tests for GET /api/v1/channel_phone_number/get_twilio_phone_numbers"""

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_get_twilio_numbers_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_twilio_phone_numbers.return_value = [
            {"phone_number": "+15551234567", "friendly_name": "Main"}
        ]
        response = client_as_member.get("/api/v1/channel_phone_number/get_twilio_phone_numbers?type=twilio")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_get_twilio_numbers_with_channel_id(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_twilio_phone_numbers.return_value = []
        response = client_as_member.get(
            "/api/v1/channel_phone_number/get_twilio_phone_numbers?type=twilio&channel_id=1"
        )
        assert response.status_code == 200

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_get_twilio_numbers_with_agent_id(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_twilio_phone_numbers.return_value = []
        response = client_as_member.get(
            "/api/v1/channel_phone_number/get_twilio_phone_numbers?type=twilio&agent_id=1"
        )
        assert response.status_code == 200

    def test_get_twilio_numbers_missing_type(self, client_as_member):
        response = client_as_member.get("/api/v1/channel_phone_number/get_twilio_phone_numbers")
        assert response.status_code == 422

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_get_twilio_numbers_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_twilio_phone_numbers.return_value = []
        response = client_as_member.get("/api/v1/channel_phone_number/get_twilio_phone_numbers?type=twilio")
        assert response.status_code == 200
        assert response.json() == []

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_get_twilio_numbers_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_twilio_phone_numbers.side_effect = HTTPException(
            status_code=400, detail="Invalid channel credentials"
        )
        response = client_as_member.get("/api/v1/channel_phone_number/get_twilio_phone_numbers?type=twilio")
        assert response.status_code == 400
