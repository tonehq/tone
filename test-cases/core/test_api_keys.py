"""Tests for API Keys endpoints (Core edition).

Source: core/api/v1/api_keys.py
Postman: postman_collection/api_keys.postman_collection.json
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# POST /api/v1/api-keys/upsert  (multipart/form-data)
# ---------------------------------------------------------------------------
class TestUpsertApiKey:
    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_create_success(self, mock_service_cls, client_as_admin):
        """Postman: Upsert API Key - Create (200)."""
        mock_instance = MagicMock()
        mock_instance.upsert_api_key.return_value = {
            "id": 1,
            "uuid": "550e8400-e29b-41d4-a716-446655440000",
            "name": "OpenAI Key",
            "status": "active",
            "account_id": 1,
            "created_at": "2026-01-15T10:00:00",
            "updated_at": "2026-01-15T10:00:00",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/api-keys/upsert",
            data={
                "name": "OpenAI Key",
                "api_key": "sk-...",
                "account_id": "1",
                "description": "Production OpenAI key",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "OpenAI Key"
        assert data["status"] == "active"
        mock_instance.upsert_api_key.assert_called_once_with(
            service_provider_id=None,
            account_id=1,
            name="OpenAI Key",
            api_key_value="sk-...",
            description="Production OpenAI key",
            additional_credentials=None,
            rate_limit_config=None,
            expires_at=None,
            key_uuid=None,
            key_status=None,
        )

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_with_service_provider_id(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_api_key.return_value = {"id": 1, "name": "My Key"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/api-keys/upsert",
            data={
                "service_provider_id": "10",
                "name": "My Key",
                "api_key": "sk-secret",
            },
        )

        assert resp.status_code == 200
        mock_instance.upsert_api_key.assert_called_once_with(
            service_provider_id=10,
            account_id=None,
            name="My Key",
            api_key_value="sk-secret",
            description=None,
            additional_credentials=None,
            rate_limit_config=None,
            expires_at=None,
            key_uuid=None,
            key_status=None,
        )

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_with_optional_fields(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_api_key.return_value = {"id": 1}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/api-keys/upsert",
            data={
                "name": "My Key",
                "api_key": "sk-secret",
                "description": "A test key",
                "additional_credentials": '{"region": "us-east"}',
                "key_status": "active",
            },
        )

        assert resp.status_code == 200
        mock_instance.upsert_api_key.assert_called_once_with(
            service_provider_id=None,
            account_id=None,
            name="My Key",
            api_key_value="sk-secret",
            description="A test key",
            additional_credentials={"region": "us-east"},
            rate_limit_config=None,
            expires_at=None,
            key_uuid=None,
            key_status="active",
        )

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_update_with_uuid(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_api_key.return_value = {"id": 1, "name": "Updated Key"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/api-keys/upsert",
            data={
                "name": "Updated Key",
                "api_key": "sk-new-secret",
                "uuid": "550e8400-e29b-41d4-a716-446655440000",
            },
        )

        assert resp.status_code == 200
        mock_instance.upsert_api_key.assert_called_once_with(
            service_provider_id=None,
            account_id=None,
            name="Updated Key",
            api_key_value="sk-new-secret",
            description=None,
            additional_credentials=None,
            rate_limit_config=None,
            expires_at=None,
            key_uuid="550e8400-e29b-41d4-a716-446655440000",
            key_status=None,
        )

    def test_missing_api_key_and_file(self, client_as_admin):
        """Postman: Upsert API Key - Missing Key (400)."""
        resp = client_as_admin.post(
            "/api/v1/api-keys/upsert",
            data={"name": "My Key"},
        )
        assert resp.status_code == 400
        assert "Either a file or api_key must be provided" in resp.json()["detail"]

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_service_error(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_api_key.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/api-keys/upsert",
            data={
                "name": "My Key",
                "api_key": "sk-secret",
            },
        )
        assert resp.status_code in (500, 422, 400)

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/api-keys/upsert",
            data={"name": "My Key", "api_key": "sk-secret"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/api-keys/list
# ---------------------------------------------------------------------------
class TestListApiKeys:
    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Get All API Keys - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.get_all_api_keys.return_value = [
            {
                "id": 1,
                "uuid": "550e8400-e29b-41d4-a716-446655440000",
                "name": "OpenAI Key",
                "status": "active",
                "account_id": 1,
            }
        ]
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/api-keys/list")

        assert resp.status_code == 200
        assert len(resp.json()) == 1
        mock_instance.get_all_api_keys.assert_called_once()

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_empty_list(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_api_keys.return_value = []
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/api-keys/list")

        assert resp.status_code == 200
        assert resp.json() == []

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_api_keys.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/api-keys/list")
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# POST /api/v1/api-keys/list_by_provider
# ---------------------------------------------------------------------------
class TestListByProvider:
    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: List By Provider - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.list_by_provider.return_value = {
            "data": [{"id": 1, "name": "OpenAI Key", "status": "active"}],
            "pagination": {"page": 1, "page_size": 20, "total": 1},
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/api-keys/list_by_provider",
            json={"service_provider_id": 1, "status": "active", "page": 1, "page_size": 20},
        )

        assert resp.status_code == 200
        mock_instance.list_by_provider.assert_called_once_with(
            service_provider_id=1,
            status_filter="active",
            page=1,
            page_size=20,
        )

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_with_pagination(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.list_by_provider.return_value = {
            "data": [],
            "pagination": {"page": 2, "page_size": 10, "total": 0},
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/api-keys/list_by_provider",
            json={"service_provider_id": 5, "page": 2, "page_size": 10, "status": "active"},
        )

        assert resp.status_code == 200
        mock_instance.list_by_provider.assert_called_once_with(
            service_provider_id=5,
            status_filter="active",
            page=2,
            page_size=10,
        )

    def test_missing_service_provider_id(self, client_as_member):
        """Postman: List By Provider - Missing ID (400)."""
        resp = client_as_member.post("/api/v1/api-keys/list_by_provider", json={})
        assert resp.status_code == 400
        assert "service_provider_id is required" in resp.json()["detail"]

    def test_invalid_service_provider_id(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/api-keys/list_by_provider",
            json={"service_provider_id": "abc"},
        )
        assert resp.status_code == 400
        assert "integer" in resp.json()["detail"]

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/api-keys/list_by_provider",
            json={"service_provider_id": 5},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/api-keys/list_by_account
# ---------------------------------------------------------------------------
class TestListByAccount:
    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: List By Account - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.list_by_account.return_value = {
            "data": [{"id": 1, "name": "OpenAI Key", "status": "active"}],
            "pagination": {"page": 1, "page_size": 20, "total": 1},
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/api-keys/list_by_account",
            json={"account_id": 1, "status": "active", "page": 1, "page_size": 20},
        )

        assert resp.status_code == 200
        mock_instance.list_by_account.assert_called_once_with(
            account_id=1,
            status_filter="active",
            page=1,
            page_size=20,
        )

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_with_pagination(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.list_by_account.return_value = {
            "data": [],
            "pagination": {"page": 2, "page_size": 10, "total": 0, "total_pages": 0},
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/api-keys/list_by_account",
            json={"account_id": 3, "page": 2, "page_size": 10, "status": "active"},
        )

        assert resp.status_code == 200
        mock_instance.list_by_account.assert_called_once_with(
            account_id=3,
            status_filter="active",
            page=2,
            page_size=10,
        )

    def test_missing_account_id(self, client_as_member):
        """Postman: List By Account - Missing ID (400)."""
        resp = client_as_member.post("/api/v1/api-keys/list_by_account", json={})
        assert resp.status_code == 400
        assert "account_id is required" in resp.json()["detail"]

    def test_invalid_account_id(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/api-keys/list_by_account",
            json={"account_id": "abc"},
        )
        assert resp.status_code == 400
        assert "integer" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# GET /api/v1/api-keys/get
# ---------------------------------------------------------------------------
class TestGetApiKey:
    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Get API Key - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.get_api_key.return_value = {
            "id": 1,
            "uuid": "550e8400-e29b-41d4-a716-446655440000",
            "name": "OpenAI Key",
            "status": "active",
            "account_id": 1,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/api-keys/get", params={"api_key_id": 1})

        assert resp.status_code == 200
        assert resp.json()["id"] == 1
        mock_instance.get_api_key.assert_called_once_with(1)

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_not_found(self, mock_service_cls, client_as_member):
        """Postman: Get API Key - Not Found (404)."""
        mock_instance = MagicMock()
        mock_instance.get_api_key.side_effect = HTTPException(
            status_code=404, detail="API key not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/api-keys/get", params={"api_key_id": 999})
        assert resp.status_code == 404

    def test_missing_api_key_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/api-keys/get")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/v1/api-keys/delete
# ---------------------------------------------------------------------------
class TestDeleteApiKey:
    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_success(self, mock_service_cls, client_as_admin):
        """Postman: Delete API Key - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.delete_api_key.return_value = {
            "message": "API key deleted successfully"
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/api-keys/delete", params={"api_key_id": 1}
        )

        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()
        mock_instance.delete_api_key.assert_called_once_with(1)

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_not_found(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.delete_api_key.side_effect = HTTPException(
            status_code=404, detail="Not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/api-keys/delete", params={"api_key_id": 999}
        )
        assert resp.status_code == 404

    def test_missing_api_key_id(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/api-keys/delete")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/api-keys/validate
# ---------------------------------------------------------------------------
class TestValidateApiKey:
    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_success(self, mock_service_cls, client_as_admin):
        """Postman: Validate API Key - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.validate_api_key.return_value = {
            "id": 1,
            "is_valid": True,
            "validated_at": "2026-01-15T10:00:00",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/api-keys/validate",
            json={"api_key_id": 1, "is_valid": True, "validation_error": None},
        )

        assert resp.status_code == 200
        mock_instance.validate_api_key.assert_called_once_with(
            api_key_id=1, is_valid=True, validation_error=None
        )

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_with_validation_error_message(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.validate_api_key.return_value = {"id": 1, "is_valid": False}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/api-keys/validate",
            json={
                "api_key_id": 1,
                "is_valid": False,
                "validation_error": "Invalid key format",
            },
        )

        assert resp.status_code == 200
        mock_instance.validate_api_key.assert_called_once_with(
            api_key_id=1, is_valid=False, validation_error="Invalid key format"
        )

    def test_missing_api_key_id(self, client_as_admin):
        """Postman: Validate API Key - Missing Fields (400)."""
        resp = client_as_admin.post(
            "/api/v1/api-keys/validate",
            json={"is_valid": True},
        )
        assert resp.status_code == 400
        assert "api_key_id and is_valid are required" in resp.json()["detail"]

    def test_missing_is_valid(self, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/api-keys/validate",
            json={"api_key_id": 1},
        )
        assert resp.status_code == 400

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_service_error(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.validate_api_key.side_effect = HTTPException(
            status_code=404, detail="Key not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/api-keys/validate",
            json={"api_key_id": 999, "is_valid": True},
        )
        assert resp.status_code == 404
