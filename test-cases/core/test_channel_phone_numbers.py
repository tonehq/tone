"""Tests for Channel Phone Numbers API endpoints (Core edition).

Source: core/api/v1/channel_phone_numbers.py
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException
from fastapi.testclient import TestClient

from main import app, api_v1
from core.database.session import get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_phone_number():
    return {
        "id": 1,
        "phone_number": "+1234567890",
        "phone_number_sid": "PN123",
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
            "provider": "twilio",
            "channel_id": 10,
        },
    ]


@pytest.fixture
def upsert_payload():
    return {
        "phone_number": "+1234567890",
        "phone_number_sid": "PN123",
        "provider": "twilio",
        "channel_id": 10,
    }


@pytest.fixture
def public_client(mock_db):
    """Client with only DB override -- for no-auth endpoints."""
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /api/v1/channel_phone_number/upsert
# ---------------------------------------------------------------------------

class TestUpsertChannelPhoneNumber:
    """Tests for POST /api/v1/channel_phone_number/upsert"""

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_success(self, mock_service_cls, client_as_member, upsert_payload, sample_phone_number):
        mock_service_cls.return_value.upsert_channel_phone_number.return_value = (
            sample_phone_number
        )
        resp = client_as_member.post(
            "/api/v1/channel_phone_number/upsert", json=upsert_payload
        )
        assert resp.status_code == 200
        mock_service_cls.return_value.upsert_channel_phone_number.assert_called_once_with(
            upsert_payload,
        )

    def test_missing_phone_number(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/channel_phone_number/upsert",
            json={"phone_number_sid": "PN1", "provider": "twilio", "channel_id": 10},
        )
        assert resp.status_code == 400
        assert "phone_number" in resp.json()["detail"].lower()

    def test_missing_phone_number_sid(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/channel_phone_number/upsert",
            json={"phone_number": "+1", "provider": "twilio", "channel_id": 10},
        )
        assert resp.status_code == 400
        assert "phone_number_sid" in resp.json()["detail"].lower()

    def test_missing_provider(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/channel_phone_number/upsert",
            json={"phone_number": "+1", "phone_number_sid": "PN1", "channel_id": 10},
        )
        assert resp.status_code == 400
        assert "provider" in resp.json()["detail"].lower()

    def test_missing_channel_id(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/channel_phone_number/upsert",
            json={"phone_number": "+1", "phone_number_sid": "PN1", "provider": "twilio"},
        )
        assert resp.status_code == 400
        assert "channel_id" in resp.json()["detail"].lower()

    def test_unauthenticated(self, client_unauthenticated, upsert_payload):
        resp = client_unauthenticated.post(
            "/api/v1/channel_phone_number/upsert", json=upsert_payload
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_service_error(self, mock_service_cls, client_as_member, upsert_payload):
        mock_service_cls.return_value.upsert_channel_phone_number.side_effect = Exception(
            "DB error"
        )
        resp = client_as_member.post(
            "/api/v1/channel_phone_number/upsert", json=upsert_payload
        )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/v1/channel_phone_number/list
# ---------------------------------------------------------------------------

class TestListChannelPhoneNumbers:
    """Tests for GET /api/v1/channel_phone_number/list"""

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_success(self, mock_service_cls, client_as_member, sample_phone_numbers):
        mock_service_cls.return_value.get_all_channel_phone_numbers.return_value = (
            sample_phone_numbers
        )
        resp = client_as_member.get("/api/v1/channel_phone_number/list")
        assert resp.status_code == 200
        assert len(resp.json()) == 2
        mock_service_cls.return_value.get_all_channel_phone_numbers.assert_called_once_with(
            channel_id=None,
        )

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_with_channel_id_filter(self, mock_service_cls, client_as_member, sample_phone_numbers):
        mock_service_cls.return_value.get_all_channel_phone_numbers.return_value = (
            sample_phone_numbers
        )
        resp = client_as_member.get(
            "/api/v1/channel_phone_number/list", params={"channel_id": 10}
        )
        assert resp.status_code == 200
        mock_service_cls.return_value.get_all_channel_phone_numbers.assert_called_once_with(
            channel_id=10,
        )

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_channel_phone_numbers.return_value = []
        resp = client_as_member.get("/api/v1/channel_phone_number/list")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/channel_phone_number/list")
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_channel_phone_numbers.side_effect = Exception(
            "DB error"
        )
        resp = client_as_member.get("/api/v1/channel_phone_number/list")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/v1/channel_phone_number/get_by_channel
# ---------------------------------------------------------------------------

class TestGetPhoneNumbersByChannel:
    """Tests for GET /api/v1/channel_phone_number/get_by_channel"""

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_success(self, mock_service_cls, client_as_member, sample_phone_numbers):
        mock_service_cls.return_value.get_all_channel_phone_numbers.return_value = (
            sample_phone_numbers
        )
        resp = client_as_member.get(
            "/api/v1/channel_phone_number/get_by_channel", params={"channel_id": 10}
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2
        mock_service_cls.return_value.get_all_channel_phone_numbers.assert_called_once_with(
            channel_id=10,
        )

    def test_missing_channel_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/channel_phone_number/get_by_channel")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/channel_phone_number/get_by_channel", params={"channel_id": 10}
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_channel_phone_numbers.side_effect = Exception(
            "DB error"
        )
        resp = client_as_member.get(
            "/api/v1/channel_phone_number/get_by_channel", params={"channel_id": 10}
        )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/v1/channel_phone_number/get
# ---------------------------------------------------------------------------

class TestGetChannelPhoneNumber:
    """Tests for GET /api/v1/channel_phone_number/get"""

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_success(self, mock_service_cls, client_as_member, sample_phone_number):
        mock_service_cls.return_value.get_channel_phone_number.return_value = sample_phone_number
        resp = client_as_member.get(
            "/api/v1/channel_phone_number/get", params={"phone_number_id": 1}
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == 1
        mock_service_cls.return_value.get_channel_phone_number.assert_called_once_with(1)

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_channel_phone_number.return_value = None
        resp = client_as_member.get(
            "/api/v1/channel_phone_number/get", params={"phone_number_id": 999}
        )
        assert resp.status_code == 200

    def test_missing_phone_number_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/channel_phone_number/get")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/channel_phone_number/get", params={"phone_number_id": 1}
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_channel_phone_number.side_effect = Exception("DB error")
        resp = client_as_member.get(
            "/api/v1/channel_phone_number/get", params={"phone_number_id": 1}
        )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# DELETE /api/v1/channel_phone_number/delete (require_admin_or_owner)
# ---------------------------------------------------------------------------

class TestDeleteChannelPhoneNumber:
    """Tests for DELETE /api/v1/channel_phone_number/delete"""

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_success(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.delete_channel_phone_number.return_value = {
            "message": "deleted"
        }
        resp = client_as_admin.delete(
            "/api/v1/channel_phone_number/delete", params={"phone_number_id": 1}
        )
        assert resp.status_code == 200
        mock_service_cls.return_value.delete_channel_phone_number.assert_called_once_with(1)

    def test_missing_phone_number_id(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/channel_phone_number/delete")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete(
            "/api/v1/channel_phone_number/delete", params={"phone_number_id": 1}
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_service_error(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.delete_channel_phone_number.side_effect = Exception(
            "DB error"
        )
        resp = client_as_admin.delete(
            "/api/v1/channel_phone_number/delete", params={"phone_number_id": 1}
        )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/v1/channel_phone_number/get_twilio_phone_numbers (NO AUTH)
# ---------------------------------------------------------------------------

class TestGetTwilioPhoneNumbers:
    """Tests for GET /api/v1/channel_phone_number/get_twilio_phone_numbers (public)"""

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_success(self, mock_service_cls, public_client, sample_phone_numbers):
        mock_service_cls.return_value.get_twilio_phone_numbers.return_value = sample_phone_numbers
        resp = public_client.get(
            "/api/v1/channel_phone_number/get_twilio_phone_numbers",
            params={"type": "twilio"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2
        mock_service_cls.return_value.get_twilio_phone_numbers.assert_called_once_with(
            channel_type="twilio", channel_id=None, agent_id=None,
        )

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_with_optional_params(self, mock_service_cls, public_client, sample_phone_numbers):
        mock_service_cls.return_value.get_twilio_phone_numbers.return_value = sample_phone_numbers
        resp = public_client.get(
            "/api/v1/channel_phone_number/get_twilio_phone_numbers",
            params={"type": "twilio", "channel_id": 10, "agent_id": 5},
        )
        assert resp.status_code == 200
        mock_service_cls.return_value.get_twilio_phone_numbers.assert_called_once_with(
            channel_type="twilio", channel_id=10, agent_id=5,
        )

    def test_missing_type(self, public_client):
        resp = public_client.get("/api/v1/channel_phone_number/get_twilio_phone_numbers")
        assert resp.status_code == 422

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_service_error(self, mock_service_cls, public_client):
        mock_service_cls.return_value.get_twilio_phone_numbers.side_effect = Exception("err")
        resp = public_client.get(
            "/api/v1/channel_phone_number/get_twilio_phone_numbers",
            params={"type": "twilio"},
        )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/v1/channel_phone_number/get_phone_number_list_to_buy
# ---------------------------------------------------------------------------

class TestGetPhoneNumberListToBuy:
    """Tests for GET /api/v1/channel_phone_number/get_phone_number_list_to_buy"""

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_phone_number_list_to_buy.return_value = [
            {"phone_number": "+1111111111", "friendly_name": "US Number"}
        ]
        resp = client_as_member.get(
            "/api/v1/channel_phone_number/get_phone_number_list_to_buy",
            params={"type": "twilio"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        mock_service_cls.return_value.get_phone_number_list_to_buy.assert_called_once_with(
            channel_type="twilio", user_id=ANY,
        )

    def test_missing_type(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/channel_phone_number/get_phone_number_list_to_buy"
        )
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/channel_phone_number/get_phone_number_list_to_buy",
            params={"type": "twilio"},
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_phone_number_list_to_buy.side_effect = Exception("err")
        resp = client_as_member.get(
            "/api/v1/channel_phone_number/get_phone_number_list_to_buy",
            params={"type": "twilio"},
        )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# POST /api/v1/channel_phone_number/buy_phone_number
# ---------------------------------------------------------------------------

class TestBuyPhoneNumber:
    """Tests for POST /api/v1/channel_phone_number/buy_phone_number"""

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.buy_phone_number.return_value = {
            "message": "Phone number purchased"
        }
        resp = client_as_member.post(
            "/api/v1/channel_phone_number/buy_phone_number",
            json={"phone_number": "+1234567890", "channel_name": "twilio"},
        )
        assert resp.status_code == 200
        mock_service_cls.return_value.buy_phone_number.assert_called_once_with(
            data={"phone_number": "+1234567890", "channel_name": "twilio"},
            user_id=ANY,
        )

    def test_missing_phone_number(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/channel_phone_number/buy_phone_number",
            json={"channel_name": "twilio"},
        )
        assert resp.status_code == 400
        assert "phone_number" in resp.json()["detail"].lower()

    def test_missing_channel_name(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/channel_phone_number/buy_phone_number",
            json={"phone_number": "+1234567890"},
        )
        assert resp.status_code == 400
        assert "channel_name" in resp.json()["detail"].lower()

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/channel_phone_number/buy_phone_number",
            json={"phone_number": "+1234567890", "channel_name": "twilio"},
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.channel_phone_numbers.ChannelPhoneNumbersService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.buy_phone_number.side_effect = Exception("err")
        resp = client_as_member.post(
            "/api/v1/channel_phone_number/buy_phone_number",
            json={"phone_number": "+1234567890", "channel_name": "twilio"},
        )
        assert resp.status_code == 500
