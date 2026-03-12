"""Tests for API Keys API endpoints.

Source: core/api/v1/api_keys.py
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


# ─── Fixtures ───

@pytest.fixture
def sample_api_key_data():
    return {
        "service_provider_id": 1,
        "name": "Test API Key",
        "api_key": "sk-test-key-123",
    }


# ─── POST /api/v1/api-keys/upsert — Upsert API Key ───

class TestUpsertApiKey:
    """Tests for POST /api/v1/api-keys/upsert"""

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_upsert_api_key_create_success(self, mock_service_cls, client_as_admin, sample_api_key_data):
        mock_service_cls.return_value.upsert_api_key.return_value = {"id": 1, "name": "Test API Key"}
        response = client_as_admin.post("/api/v1/api-keys/upsert", json=sample_api_key_data)
        assert response.status_code == 200

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_upsert_api_key_with_optional_fields(self, mock_service_cls, client_as_admin, sample_api_key_data):
        data = {**sample_api_key_data, "description": "Test key", "expires_at": "2026-12-31"}
        mock_service_cls.return_value.upsert_api_key.return_value = {"id": 1}
        response = client_as_admin.post("/api/v1/api-keys/upsert", json=data)
        assert response.status_code == 200

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_upsert_api_key_missing_service_provider_id(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/api-keys/upsert", json={
            "name": "Key", "api_key": "sk-test"
        })
        assert response.status_code == 400
        assert "service_provider_id, name, and api_key are required" in response.json()["detail"]

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_upsert_api_key_missing_name(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/api-keys/upsert", json={
            "service_provider_id": 1, "api_key": "sk-test"
        })
        assert response.status_code == 400

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_upsert_api_key_missing_api_key(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/api-keys/upsert", json={
            "service_provider_id": 1, "name": "Key"
        })
        assert response.status_code == 400

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_upsert_api_key_empty_body(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/api-keys/upsert", json={})
        assert response.status_code == 400

    def test_upsert_api_key_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/api-keys/upsert", json={
            "service_provider_id": 1, "name": "Key", "api_key": "sk-test"
        })
        assert response.status_code in (401, 403)


# ─── GET /api/v1/api-keys/list — Get All API Keys ───

class TestGetAllApiKeys:
    """Tests for GET /api/v1/api-keys/list"""

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_get_all_api_keys_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_api_keys.return_value = [{"id": 1, "name": "Key1"}]
        response = client_as_member.get("/api/v1/api-keys/list")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_get_all_api_keys_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_api_keys.return_value = []
        response = client_as_member.get("/api/v1/api-keys/list")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_all_api_keys_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/api-keys/list")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/api-keys/get — Get API Key ───

class TestGetApiKey:
    """Tests for GET /api/v1/api-keys/get"""

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_get_api_key_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_api_key.return_value = {"id": 1, "name": "Key1"}
        response = client_as_member.get("/api/v1/api-keys/get?api_key_id=1")
        assert response.status_code == 200

    def test_get_api_key_missing_id(self, client_as_member):
        response = client_as_member.get("/api/v1/api-keys/get")
        assert response.status_code == 422

    def test_get_api_key_invalid_id(self, client_as_member):
        response = client_as_member.get("/api/v1/api-keys/get?api_key_id=abc")
        assert response.status_code == 422

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_get_api_key_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_api_key.side_effect = HTTPException(
            status_code=404, detail="API key not found"
        )
        response = client_as_member.get("/api/v1/api-keys/get?api_key_id=999")
        assert response.status_code == 404

    def test_get_api_key_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/api-keys/get?api_key_id=1")
        assert response.status_code in (401, 403)


# ─── DELETE /api/v1/api-keys/delete — Delete API Key ───

class TestDeleteApiKey:
    """Tests for DELETE /api/v1/api-keys/delete"""

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_delete_api_key_success(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.delete_api_key.return_value = {"message": "deleted"}
        response = client_as_admin.delete("/api/v1/api-keys/delete?api_key_id=1")
        assert response.status_code == 200

    def test_delete_api_key_missing_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/api-keys/delete")
        assert response.status_code == 422

    def test_delete_api_key_invalid_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/api-keys/delete?api_key_id=abc")
        assert response.status_code == 422

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_delete_api_key_not_found(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.delete_api_key.side_effect = HTTPException(
            status_code=404, detail="API key not found"
        )
        response = client_as_admin.delete("/api/v1/api-keys/delete?api_key_id=999")
        assert response.status_code == 404

    def test_delete_api_key_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/api-keys/delete?api_key_id=1")
        assert response.status_code in (401, 403)


# ─── POST /api/v1/api-keys/validate — Validate API Key ───

class TestValidateApiKey:
    """Tests for POST /api/v1/api-keys/validate"""

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_validate_api_key_valid(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.validate_api_key.return_value = {"is_valid": True}
        response = client_as_admin.post("/api/v1/api-keys/validate", json={
            "api_key_id": 1, "is_valid": True
        })
        assert response.status_code == 200

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_validate_api_key_invalid_with_error(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.validate_api_key.return_value = {"is_valid": False}
        response = client_as_admin.post("/api/v1/api-keys/validate", json={
            "api_key_id": 1, "is_valid": False, "validation_error": "Key expired"
        })
        assert response.status_code == 200

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_validate_api_key_missing_api_key_id(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/api-keys/validate", json={
            "is_valid": True
        })
        assert response.status_code == 400
        assert "api_key_id and is_valid are required" in response.json()["detail"]

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_validate_api_key_missing_is_valid(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/api-keys/validate", json={
            "api_key_id": 1
        })
        assert response.status_code == 400

    @patch("core.api.v1.api_keys.ApiKeyService")
    def test_validate_api_key_empty_body(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/api-keys/validate", json={})
        assert response.status_code == 400

    def test_validate_api_key_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/api-keys/validate", json={
            "api_key_id": 1, "is_valid": True
        })
        assert response.status_code in (401, 403)
