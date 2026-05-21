"""Tests for Accounts API endpoints (Core edition).

Source: core/api/v1/accounts.py
Postman collection: postman_collection/accounts.postman_collection.json
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# POST /api/v1/accounts/upsert
# ---------------------------------------------------------------------------
class TestUpsertAccount:
    """Tests for POST /api/v1/accounts/upsert"""

    @patch("ee.api.v1.accounts.AccountService")
    def test_upsert_create_with_api_key_value(self, mock_service_cls, client_as_admin):
        """Postman: Upsert Account - Create With API Key Value (200)"""
        mock_instance = MagicMock()
        mock_instance.upsert_account.return_value = {
            "id": 1,
            "uuid": "c9d0e1f2-a3b4-5678-9abc-789012345678",
            "name": "OpenAI LLM",
            "description": "OpenAI LLM account",
            "service_type": "llm",
            "model_provider_menu_id": 1,
            "hosting_provider_id": None,
            "api_key_id": 1,
            "api_key_hint": "sk-a...3...",
            "config": {},
            "status": "active",
            "is_default": True,
            "is_public": False,
            "tags": ["production"],
            "created_at": 1710201600,
            "updated_at": 1710201600,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/accounts/upsert",
            json={
                "model_provider_menu_id": 1,
                "name": "OpenAI LLM",
                "service_type": "llm",
                "config": {},
                "api_key_value": "sk-abc123...",
                "api_key_name": "OpenAI Key",
                "description": "OpenAI LLM account",
                "is_default": True,
                "is_public": False,
                "tags": ["production"],
                "status": "active",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "OpenAI LLM"
        assert data["service_type"] == "llm"
        mock_instance.upsert_account.assert_called_once_with(
            model_provider_menu_id=1,
            name="OpenAI LLM",
            service_type="llm",
            config={},
            api_key_id=None,
            description="OpenAI LLM account",
            is_default=True,
            is_public=False,
            tags=["production"],
            account_uuid=None,
            account_status="active",
            api_key_value="sk-abc123...",
            api_key_name="OpenAI Key",
            additional_credentials=None,
        )

    @patch("ee.api.v1.accounts.AccountService")
    def test_upsert_create_with_existing_api_key_id(self, mock_service_cls, client_as_admin):
        """Postman: Upsert Account - Create With Existing API Key ID (200)"""
        mock_instance = MagicMock()
        mock_instance.upsert_account.return_value = {
            "id": 1,
            "uuid": "c9d0e1f2-a3b4-5678-9abc-789012345678",
            "name": "OpenAI LLM",
            "description": "OpenAI LLM account",
            "service_type": "llm",
            "model_provider_menu_id": 1,
            "api_key_id": 1,
            "api_key_hint": "sk-a...3...",
            "config": {},
            "status": "active",
            "is_default": True,
            "is_public": False,
            "tags": None,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/accounts/upsert",
            json={
                "model_provider_menu_id": 1,
                "name": "OpenAI LLM",
                "service_type": "llm",
                "config": {},
                "api_key_id": 1,
                "description": "OpenAI LLM account",
                "is_default": True,
                "status": "active",
            },
        )

        assert resp.status_code == 200
        mock_instance.upsert_account.assert_called_once_with(
            model_provider_menu_id=1,
            name="OpenAI LLM",
            service_type="llm",
            config={},
            api_key_id=1,
            description="OpenAI LLM account",
            is_default=True,
            is_public=False,
            tags=None,
            account_uuid=None,
            account_status="active",
            api_key_value=None,
            api_key_name=None,
            additional_credentials=None,
        )

    @patch("ee.api.v1.accounts.AccountService")
    def test_upsert_create_with_additional_credentials(self, mock_service_cls, client_as_admin):
        """Postman: Upsert Account - Create With Additional Credentials (200)"""
        mock_instance = MagicMock()
        mock_instance.upsert_account.return_value = {
            "id": 3,
            "uuid": "e1f2a3b4-c5d6-7890-bcde-901234567890",
            "name": "PlayHT TTS",
            "description": None,
            "service_type": "tts",
            "model_provider_menu_id": 8,
            "api_key_id": 3,
            "api_key_hint": "pk-a...3...",
            "config": {},
            "status": "active",
            "is_default": False,
            "is_public": False,
            "tags": None,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/accounts/upsert",
            json={
                "model_provider_menu_id": 8,
                "name": "PlayHT TTS",
                "service_type": "tts",
                "config": {},
                "api_key_value": "pk-abc123...",
                "api_key_name": "PlayHT Key",
                "additional_credentials": {"user_id": "usr_123"},
                "is_default": False,
                "status": "active",
            },
        )

        assert resp.status_code == 200
        mock_instance.upsert_account.assert_called_once_with(
            model_provider_menu_id=8,
            name="PlayHT TTS",
            service_type="tts",
            config={},
            api_key_id=None,
            description=None,
            is_default=False,
            is_public=False,
            tags=None,
            account_uuid=None,
            account_status="active",
            api_key_value="pk-abc123...",
            api_key_name="PlayHT Key",
            additional_credentials={"user_id": "usr_123"},
        )

    @patch("ee.api.v1.accounts.AccountService")
    def test_upsert_update_existing(self, mock_service_cls, client_as_admin):
        """Postman: Upsert Account - Update Existing (200)"""
        mock_instance = MagicMock()
        mock_instance.upsert_account.return_value = {
            "id": 1,
            "uuid": "c9d0e1f2-a3b4-5678-9abc-789012345678",
            "name": "OpenAI LLM - Updated",
            "description": None,
            "service_type": "llm",
            "model_provider_menu_id": 1,
            "api_key_id": 1,
            "api_key_hint": "sk-a...3...",
            "config": {},
            "status": "active",
            "is_default": True,
            "is_public": False,
            "tags": None,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/accounts/upsert",
            json={
                "uuid": "c9d0e1f2-a3b4-5678-9abc-789012345678",
                "model_provider_menu_id": 1,
                "name": "OpenAI LLM - Updated",
                "service_type": "llm",
                "config": {},
                "api_key_id": 1,
                "is_default": True,
                "status": "active",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "OpenAI LLM - Updated"
        mock_instance.upsert_account.assert_called_once_with(
            model_provider_menu_id=1,
            name="OpenAI LLM - Updated",
            service_type="llm",
            config={},
            api_key_id=1,
            description=None,
            is_default=True,
            is_public=False,
            tags=None,
            account_uuid="c9d0e1f2-a3b4-5678-9abc-789012345678",
            account_status="active",
            api_key_value=None,
            api_key_name=None,
            additional_credentials=None,
        )

    @patch("ee.api.v1.accounts.AccountService")
    def test_upsert_missing_name_and_service_type(self, mock_service_cls, client_as_admin):
        """Postman: Upsert Account - Missing Name And Service Type (400)"""
        resp = client_as_admin.post(
            "/api/v1/accounts/upsert",
            json={
                "model_provider_menu_id": 1,
                "name": "My Account",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "name and service_type are required"

    @patch("ee.api.v1.accounts.AccountService")
    def test_upsert_missing_model_provider_menu_id(self, mock_service_cls, client_as_admin):
        """Postman: Upsert Account - Missing Model Provider Menu ID (400)"""
        resp = client_as_admin.post(
            "/api/v1/accounts/upsert",
            json={
                "name": "Test Account",
                "service_type": "llm",
                "config": {},
            },
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "model_provider_menu_id is required"

    @patch("ee.api.v1.accounts.AccountService")
    def test_upsert_missing_name(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/accounts/upsert",
            json={
                "model_provider_menu_id": 1,
                "service_type": "stt",
                "config": {},
            },
        )
        assert resp.status_code == 400

    @patch("ee.api.v1.accounts.AccountService")
    def test_upsert_missing_service_type(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/accounts/upsert",
            json={
                "model_provider_menu_id": 1,
                "name": "My STT",
                "config": {},
            },
        )
        assert resp.status_code == 400

    @patch("ee.api.v1.accounts.AccountService")
    def test_upsert_duplicate_name_and_type(self, mock_service_cls, client_as_admin):
        """Postman: Upsert Account - Duplicate Name And Type (409)"""
        mock_instance = MagicMock()
        mock_instance.upsert_account.side_effect = HTTPException(
            status_code=409, detail="An account with this name and type already exists in this organization"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/accounts/upsert",
            json={
                "model_provider_menu_id": 1,
                "name": "OpenAI LLM",
                "service_type": "llm",
                "config": {},
                "api_key_id": 2,
            },
        )
        assert resp.status_code == 409
        assert resp.json()["detail"] == "An account with this name and type already exists in this organization"

    @patch("ee.api.v1.accounts.AccountService")
    def test_upsert_model_provider_menu_not_found(self, mock_service_cls, client_as_admin):
        """Postman: Upsert Account - Model Provider Menu Not Found (404)"""
        mock_instance = MagicMock()
        mock_instance.upsert_account.side_effect = HTTPException(
            status_code=404, detail="Model provider menu not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/accounts/upsert",
            json={
                "model_provider_menu_id": 9999,
                "name": "Bad Provider",
                "service_type": "llm",
                "config": {},
            },
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Model provider menu not found"

    @patch("ee.api.v1.accounts.AccountService")
    def test_upsert_api_key_not_found(self, mock_service_cls, client_as_admin):
        """Postman: Upsert Account - API Key Not Found (404)"""
        mock_instance = MagicMock()
        mock_instance.upsert_account.side_effect = HTTPException(
            status_code=404, detail="API key not found or inactive"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/accounts/upsert",
            json={
                "model_provider_menu_id": 1,
                "name": "Test Account",
                "service_type": "llm",
                "config": {},
                "api_key_id": 9999,
            },
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "API key not found or inactive"

    @patch("ee.api.v1.accounts.AccountService")
    def test_upsert_config_defaults_to_empty(self, mock_service_cls, client_as_admin):
        """Config is optional and defaults to {} when omitted."""
        mock_instance = MagicMock()
        mock_instance.upsert_account.return_value = {"id": 1}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/accounts/upsert",
            json={
                "model_provider_menu_id": 1,
                "name": "My STT",
                "service_type": "stt",
            },
        )
        assert resp.status_code == 200

    @patch("ee.api.v1.accounts.AccountService")
    def test_upsert_service_error(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_account.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/accounts/upsert",
            json={
                "model_provider_menu_id": 1,
                "name": "My STT",
                "service_type": "stt",
                "config": {},
            },
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/accounts/list
# ---------------------------------------------------------------------------
class TestListAccounts:
    """Tests for GET /api/v1/accounts/list"""

    @patch("ee.api.v1.accounts.AccountService")
    def test_list_accounts_success(self, mock_service_cls, client_as_member):
        """Postman: Get All Accounts - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.get_all_accounts.return_value = [
            {
                "id": 1,
                "uuid": "c9d0e1f2-a3b4-5678-9abc-789012345678",
                "name": "OpenAI LLM",
                "display_name": "OpenAI LLM",
                "description": "OpenAI LLM account",
                "service_type": "llm",
                "model_provider_menu_id": 1,
                "service_provider_name": "OpenAI",
                "provider_type": "llm",
                "api_key_id": 1,
                "api_key_hint": "sk-a...3...",
                "config": {},
                "status": "active",
                "is_default": True,
                "is_public": False,
                "tags": None,
                "usage_count": 42,
                "last_used_at": 1710288000,
                "created_at": 1710201600,
                "models": [
                    {"id": 1, "model_provider_menu_id": 1, "name": "gpt-4.1"},
                    {"id": 2, "model_provider_menu_id": 1, "name": "gpt-4o"},
                ],
                "meta_data_schema": None,
            },
            {
                "id": 2,
                "uuid": "d0e1f2a3-b4c5-6789-abcd-890123456789",
                "name": "Deepgram STT",
                "display_name": "Deepgram STT",
                "description": None,
                "service_type": "stt",
                "model_provider_menu_id": 5,
                "service_provider_name": "Deepgram",
                "provider_type": "stt",
                "api_key_id": 3,
                "api_key_hint": "dg-1...efgh",
                "config": {},
                "status": "active",
                "is_default": True,
                "is_public": False,
                "tags": None,
                "usage_count": 10,
                "last_used_at": 1710288000,
                "created_at": 1710201600,
                "models": [
                    {"id": 10, "model_provider_menu_id": 5, "name": "nova-3"},
                ],
                "meta_data_schema": None,
            },
        ]
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/accounts/list")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        mock_instance.get_all_accounts.assert_called_once_with(service_type=None)

    @patch("ee.api.v1.accounts.AccountService")
    def test_list_accounts_filter_by_llm(self, mock_service_cls, client_as_member):
        """Postman: Get All Accounts - Filter By LLM (200)"""
        mock_instance = MagicMock()
        mock_instance.get_all_accounts.return_value = [
            {
                "id": 1,
                "name": "OpenAI LLM",
                "service_type": "llm",
                "model_provider_menu_id": 1,
            },
        ]
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/accounts/list", params={"service_type": "llm"}
        )

        assert resp.status_code == 200
        mock_instance.get_all_accounts.assert_called_once_with(service_type="llm")

    @patch("ee.api.v1.accounts.AccountService")
    def test_list_accounts_empty(self, mock_service_cls, client_as_member):
        """Postman: Get All Accounts - Empty (200)"""
        mock_instance = MagicMock()
        mock_instance.get_all_accounts.return_value = []
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/accounts/list", params={"service_type": "stt"}
        )

        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /api/v1/accounts/get
# ---------------------------------------------------------------------------
class TestGetAccount:
    """Tests for GET /api/v1/accounts/get"""

    @patch("ee.api.v1.accounts.AccountService")
    def test_get_account_success(self, mock_service_cls, client_as_member):
        """Postman: Get Account - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.get_account.return_value = {
            "id": 1,
            "uuid": "c9d0e1f2-a3b4-5678-9abc-789012345678",
            "name": "OpenAI LLM",
            "description": "OpenAI LLM account",
            "service_type": "llm",
            "model_provider_menu_id": 1,
            "service_provider_name": "OpenAI",
            "provider_type": "llm",
            "api_key_id": 1,
            "api_key_hint": "sk-a...3...",
            "config": {},
            "status": "active",
            "is_default": True,
            "is_public": False,
            "tags": None,
            "usage_count": 42,
            "last_used_at": 1710288000,
            "created_at": 1710201600,
            "updated_at": 1710201600,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/accounts/get", params={"account_id": 1})

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["name"] == "OpenAI LLM"
        mock_instance.get_account.assert_called_once_with(1)

    @patch("ee.api.v1.accounts.AccountService")
    def test_get_account_not_found(self, mock_service_cls, client_as_member):
        """Postman: Get Account - Not Found (404)"""
        mock_instance = MagicMock()
        mock_instance.get_account.side_effect = HTTPException(
            status_code=404, detail="Account not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/accounts/get", params={"account_id": 9999})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Account not found"

    def test_get_account_missing_account_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/accounts/get")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/accounts/default
# ---------------------------------------------------------------------------
class TestGetDefaultAccount:
    """Tests for GET /api/v1/accounts/default"""

    @patch("ee.api.v1.accounts.AccountService")
    def test_get_default_account_llm(self, mock_service_cls, client_as_member):
        """Postman: Get Default Account - LLM (200)"""
        mock_instance = MagicMock()
        mock_instance.get_default_account.return_value = {
            "id": 1,
            "uuid": "c9d0e1f2-a3b4-5678-9abc-789012345678",
            "name": "OpenAI LLM",
            "service_type": "llm",
            "model_provider_menu_id": 1,
            "service_provider_name": "OpenAI",
            "api_key_id": 1,
            "api_key_hint": "sk-a...3...",
            "config": {},
            "status": "active",
            "is_default": True,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/accounts/default", params={"service_type": "llm"}
        )

        assert resp.status_code == 200
        mock_instance.get_default_account.assert_called_once_with(service_type="llm")

    @patch("ee.api.v1.accounts.AccountService")
    def test_get_default_account_stt(self, mock_service_cls, client_as_member):
        """Postman: Get Default Account - STT (200)"""
        mock_instance = MagicMock()
        mock_instance.get_default_account.return_value = {
            "id": 2,
            "uuid": "d0e1f2a3-b4c5-6789-abcd-890123456789",
            "name": "Deepgram STT",
            "service_type": "stt",
            "model_provider_menu_id": 5,
            "service_provider_name": "Deepgram",
            "api_key_id": 3,
            "api_key_hint": "dg-1...efgh",
            "config": {},
            "status": "active",
            "is_default": True,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/accounts/default", params={"service_type": "stt"}
        )

        assert resp.status_code == 200
        mock_instance.get_default_account.assert_called_once_with(service_type="stt")

    @patch("ee.api.v1.accounts.AccountService")
    def test_get_default_account_tts(self, mock_service_cls, client_as_member):
        """Postman: Get Default Account - TTS (200)"""
        mock_instance = MagicMock()
        mock_instance.get_default_account.return_value = {
            "id": 3,
            "uuid": "e1f2a3b4-c5d6-7890-bcde-901234567890",
            "name": "ElevenLabs TTS",
            "service_type": "tts",
            "model_provider_menu_id": 7,
            "service_provider_name": "ElevenLabs",
            "api_key_id": 5,
            "api_key_hint": "el-1...ijkl",
            "config": {},
            "status": "active",
            "is_default": True,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/accounts/default", params={"service_type": "tts"}
        )

        assert resp.status_code == 200
        mock_instance.get_default_account.assert_called_once_with(service_type="tts")

    @patch("ee.api.v1.accounts.AccountService")
    def test_get_default_account_not_found(self, mock_service_cls, client_as_member):
        """Postman: Get Default Account - Not Found (404)"""
        mock_instance = MagicMock()
        mock_instance.get_default_account.side_effect = HTTPException(
            status_code=404, detail="No default account found for type: llm"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/accounts/default", params={"service_type": "llm"}
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "No default account found for type: llm"

    def test_get_default_account_missing_service_type(self, client_as_member):
        resp = client_as_member.get("/api/v1/accounts/default")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/v1/accounts/delete
# ---------------------------------------------------------------------------
class TestDeleteAccount:
    """Tests for DELETE /api/v1/accounts/delete"""

    @patch("ee.api.v1.accounts.AccountService")
    def test_delete_account_by_id(self, mock_service_cls, client_as_admin):
        """Postman: Delete Account - By ID (200)"""
        mock_instance = MagicMock()
        mock_instance.delete_account.return_value = {"message": "Account deleted successfully"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/accounts/delete", params={"account_id": 1}
        )

        assert resp.status_code == 200
        assert resp.json()["message"] == "Account deleted successfully"
        mock_instance.delete_account.assert_called_once_with(1)

    @patch("ee.api.v1.accounts.AccountService")
    def test_delete_account_by_uuid(self, mock_service_cls, client_as_admin):
        """Postman: Delete Account - By UUID (200)"""
        mock_instance = MagicMock()
        mock_instance.delete_account_by_uuid.return_value = {"message": "Account deleted successfully"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/accounts/delete",
            params={"uuid": "c9d0e1f2-a3b4-5678-9abc-789012345678"},
        )

        assert resp.status_code == 200
        assert resp.json()["message"] == "Account deleted successfully"
        mock_instance.delete_account_by_uuid.assert_called_once_with(
            "c9d0e1f2-a3b4-5678-9abc-789012345678"
        )

    @patch("ee.api.v1.accounts.AccountService")
    def test_delete_account_not_found(self, mock_service_cls, client_as_admin):
        """Postman: Delete Account - Not Found (404)"""
        mock_instance = MagicMock()
        mock_instance.delete_account.side_effect = HTTPException(
            status_code=404, detail="Account not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/accounts/delete", params={"account_id": 9999}
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Account not found"

    @patch("ee.api.v1.accounts.AccountService")
    def test_delete_account_missing_params(self, mock_service_cls, client_as_admin):
        """Postman: Delete Account - Missing Params (400)"""
        resp = client_as_admin.delete("/api/v1/accounts/delete")
        assert resp.status_code == 400
        assert resp.json()["detail"] == "uuid or account_id is required"
