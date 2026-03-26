"""Tests for API Keys endpoints (Core edition).

Source: core/api/v1/api_keys.py
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# POST /api/v1/api-keys/upsert
# ---------------------------------------------------------------------------
class TestUpsertApiKey:
    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_success(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_api_key.return_value = {"id": 1, "name": "My Key"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/api-keys/upsert",
            json={
                "service_provider_id": 10,
                "name": "My Key",
                "api_key": "sk-secret",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "My Key"
        mock_service_cls.assert_called_once_with(ANY, user_id=ANY)
        mock_instance.upsert_api_key.assert_called_once_with(
            service_provider_id=10,
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
            json={
                "service_provider_id": 10,
                "name": "My Key",
                "api_key": "sk-secret",
                "description": "A test key",
                "additional_credentials": {"region": "us-east"},
                "status": "active",
            },
        )

        assert resp.status_code == 200
        mock_instance.upsert_api_key.assert_called_once_with(
            service_provider_id=10,
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
    def test_missing_service_provider_id(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/api-keys/upsert",
            json={"name": "My Key", "api_key": "sk-secret"},
        )
        assert resp.status_code == 400
        assert "service_provider_id" in resp.json()["detail"]

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_missing_name(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/api-keys/upsert",
            json={"service_provider_id": 10, "api_key": "sk-secret"},
        )
        assert resp.status_code == 400

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_missing_api_key(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/api-keys/upsert",
            json={"service_provider_id": 10, "name": "My Key"},
        )
        assert resp.status_code == 400

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_service_error(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_api_key.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/api-keys/upsert",
            json={
                "service_provider_id": 10,
                "name": "My Key",
                "api_key": "sk-secret",
            },
        )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/v1/api-keys/list
# ---------------------------------------------------------------------------
class TestListApiKeys:
    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_api_keys.return_value = [
            {"id": 1, "name": "Key A"},
            {"id": 2, "name": "Key B"},
        ]
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/api-keys/list")

        assert resp.status_code == 200
        assert len(resp.json()) == 2
        mock_service_cls.assert_called_once_with(ANY, user_id=ANY)
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
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/v1/api-keys/get
# ---------------------------------------------------------------------------
class TestGetApiKey:
    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_api_key.return_value = {"id": 5, "name": "Key X"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/api-keys/get", params={"api_key_id": 5})

        assert resp.status_code == 200
        assert resp.json()["id"] == 5
        mock_instance.get_api_key.assert_called_once_with(5)

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_api_key.side_effect = HTTPException(
            status_code=404, detail="Not found"
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
        mock_instance = MagicMock()
        mock_instance.delete_api_key.return_value = {"message": "Deleted"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/api-keys/delete", params={"api_key_id": 3}
        )

        assert resp.status_code == 200
        mock_instance.delete_api_key.assert_called_once_with(3)

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
        mock_instance = MagicMock()
        mock_instance.validate_api_key.return_value = {"id": 1, "is_valid": True}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/api-keys/validate",
            json={"api_key_id": 1, "is_valid": True},
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

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_missing_api_key_id(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/api-keys/validate",
            json={"is_valid": True},
        )
        assert resp.status_code == 400

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_missing_is_valid(self, mock_service_cls, client_as_admin):
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
