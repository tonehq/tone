"""Tests for Accounts API endpoints (Core edition).

Source: core/api/v1/accounts.py (renamed from services.py)
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# POST /api/v1/accounts/upsert
# ---------------------------------------------------------------------------
class TestUpsertAccount:
    @patch("ee.api.v1.accounts.AccountService")
    def test_success(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_account.return_value = {"id": 1, "name": "My STT"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/accounts/upsert",
            json={
                "service_provider_id": 5,
                "name": "My STT",
                "service_type": "stt",
                "config": {"language": "en"},
            },
        )

        assert resp.status_code == 200
        assert resp.json()["name"] == "My STT"
        mock_instance.upsert_account.assert_called_once_with(
            service_provider_id=5,
            model_provider_menu_id=None,
            name="My STT",
            service_type="stt",
            config={"language": "en"},
            api_key_id=None,
            description=None,
            is_default=False,
            is_public=False,
            tags=None,
            account_uuid=None,
            account_status=None,
            api_key_value=None,
            api_key_name=None,
            additional_credentials=None,
        )

    @patch("ee.api.v1.accounts.AccountService")
    def test_with_optional_fields(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_account.return_value = {"id": 1}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/accounts/upsert",
            json={
                "service_provider_id": 5,
                "name": "My STT",
                "service_type": "stt",
                "config": {"language": "en"},
                "api_key_id": 10,
                "description": "Primary STT account",
                "is_default": True,
                "is_public": True,
                "tags": ["production"],
                "uuid": "abc-123",
                "status": "active",
            },
        )

        assert resp.status_code == 200
        mock_instance.upsert_account.assert_called_once_with(
            service_provider_id=5,
            model_provider_menu_id=None,
            name="My STT",
            service_type="stt",
            config={"language": "en"},
            api_key_id=10,
            description="Primary STT account",
            is_default=True,
            is_public=True,
            tags=["production"],
            account_uuid="abc-123",
            account_status="active",
            api_key_value=None,
            api_key_name=None,
            additional_credentials=None,
        )

    @patch("ee.api.v1.accounts.AccountService")
    def test_missing_provider_id(self, mock_service_cls, client_as_admin):
        """Neither service_provider_id nor model_provider_menu_id provided."""
        resp = client_as_admin.post(
            "/api/v1/accounts/upsert",
            json={
                "name": "My STT",
                "service_type": "stt",
                "config": {"language": "en"},
            },
        )
        assert resp.status_code == 400
        assert "model_provider_menu_id" in resp.json()["detail"]

    @patch("ee.api.v1.accounts.AccountService")
    def test_missing_name(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/accounts/upsert",
            json={
                "service_provider_id": 5,
                "service_type": "stt",
                "config": {"language": "en"},
            },
        )
        assert resp.status_code == 400

    @patch("ee.api.v1.accounts.AccountService")
    def test_missing_service_type(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/accounts/upsert",
            json={
                "service_provider_id": 5,
                "name": "My STT",
                "config": {"language": "en"},
            },
        )
        assert resp.status_code == 400

    @patch("ee.api.v1.accounts.AccountService")
    def test_config_defaults_to_empty(self, mock_service_cls, client_as_admin):
        """Config is optional and defaults to {} when omitted."""
        mock_instance = MagicMock()
        mock_instance.upsert_account.return_value = {"id": 1}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/accounts/upsert",
            json={
                "service_provider_id": 5,
                "name": "My STT",
                "service_type": "stt",
            },
        )
        assert resp.status_code == 200

    @patch("ee.api.v1.accounts.AccountService")
    def test_service_error(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_account.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/accounts/upsert",
            json={
                "service_provider_id": 5,
                "name": "My STT",
                "service_type": "stt",
                "config": {"language": "en"},
            },
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/accounts/list
# ---------------------------------------------------------------------------
class TestListAccounts:
    @patch("ee.api.v1.accounts.AccountService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_accounts.return_value = [
            {"id": 1, "name": "STT A"},
            {"id": 2, "name": "TTS B"},
        ]
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/accounts/list")

        assert resp.status_code == 200
        assert len(resp.json()) == 2
        mock_instance.get_all_accounts.assert_called_once_with(service_type=None)

    @patch("ee.api.v1.accounts.AccountService")
    def test_filter_by_service_type(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_accounts.return_value = [{"id": 1, "service_type": "stt"}]
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/accounts/list", params={"service_type": "stt"}
        )

        assert resp.status_code == 200
        mock_instance.get_all_accounts.assert_called_once_with(service_type="stt")

    @patch("ee.api.v1.accounts.AccountService")
    def test_empty_list(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_accounts.return_value = []
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/accounts/list")

        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /api/v1/accounts/get
# ---------------------------------------------------------------------------
class TestGetAccount:
    @patch("ee.api.v1.accounts.AccountService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_account.return_value = {"id": 3, "name": "My LLM"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/accounts/get", params={"account_id": 3})

        assert resp.status_code == 200
        assert resp.json()["id"] == 3
        mock_instance.get_account.assert_called_once_with(3)

    @patch("ee.api.v1.accounts.AccountService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_account.side_effect = HTTPException(
            status_code=404, detail="Not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/accounts/get", params={"account_id": 999})
        assert resp.status_code == 404

    def test_missing_account_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/accounts/get")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/accounts/default
# ---------------------------------------------------------------------------
class TestGetDefaultAccount:
    @patch("ee.api.v1.accounts.AccountService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_default_account.return_value = {
            "id": 1,
            "is_default": True,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/accounts/default", params={"service_type": "stt"}
        )

        assert resp.status_code == 200
        mock_instance.get_default_account.assert_called_once_with(service_type="stt")

    @patch("ee.api.v1.accounts.AccountService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_default_account.side_effect = HTTPException(
            status_code=404, detail="No default account"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/accounts/default", params={"service_type": "stt"}
        )
        assert resp.status_code == 404

    def test_missing_service_type(self, client_as_member):
        resp = client_as_member.get("/api/v1/accounts/default")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/v1/accounts/delete
# ---------------------------------------------------------------------------
class TestDeleteAccount:
    @patch("ee.api.v1.accounts.AccountService")
    def test_success(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.delete_account.return_value = {"message": "Deleted"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/accounts/delete", params={"account_id": 2}
        )

        assert resp.status_code == 200
        mock_instance.delete_account.assert_called_once_with(2)

    @patch("ee.api.v1.accounts.AccountService")
    def test_not_found(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.delete_account.side_effect = HTTPException(
            status_code=404, detail="Not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/accounts/delete", params={"account_id": 999}
        )
        assert resp.status_code == 404

    def test_missing_account_id(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/accounts/delete")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/accounts/upsert — new model_provider_menu_id path
# ---------------------------------------------------------------------------
class TestUpsertAccountNewPath:
    @patch("ee.api.v1.accounts.AccountService")
    def test_with_model_provider_menu_id(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_account.return_value = {"id": 1, "name": "OpenAI LLM"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/accounts/upsert",
            json={
                "model_provider_menu_id": 1,
                "name": "OpenAI LLM",
                "service_type": "llm",
                "config": {},
                "api_key_id": 3,
            },
        )

        assert resp.status_code == 200
        mock_instance.upsert_account.assert_called_once_with(
            service_provider_id=None,
            model_provider_menu_id=1,
            name="OpenAI LLM",
            service_type="llm",
            config={},
            api_key_id=3,
            description=None,
            is_default=False,
            is_public=False,
            tags=None,
            account_uuid=None,
            account_status=None,
            api_key_value=None,
            api_key_name=None,
            additional_credentials=None,
        )

    @patch("ee.api.v1.accounts.AccountService")
    def test_both_provider_ids(self, mock_service_cls, client_as_admin):
        """When both service_provider_id and model_provider_menu_id are provided, both are passed."""
        mock_instance = MagicMock()
        mock_instance.upsert_account.return_value = {"id": 1}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/accounts/upsert",
            json={
                "service_provider_id": 5,
                "model_provider_menu_id": 1,
                "name": "Dual",
                "service_type": "llm",
            },
        )

        assert resp.status_code == 200
