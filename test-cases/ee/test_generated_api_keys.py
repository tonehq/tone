"""Tests for Generated API Keys endpoints.

Source: core/api/v1/generated_api_keys.py
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


# ─── Fixtures ───

@pytest.fixture
def sample_basic_key_data():
    return {
        "name": "Test Key",
        "key_value": "tk_test_key_123",
    }


@pytest.fixture
def sample_full_key_data():
    return {
        "name": "Full Key",
        "key_value": "tk_full_key_456",
        "domains": ["example.com", "api.example.com"],
        "abuse_prevention": {"is_toggled": True, "recaptcha_secret_key": "secret", "threshold": 0.5},
        "fraud_protection": True,
    }


# ─── POST /api/v1/generated-api-keys/upsert — Upsert Basic Key ───

class TestUpsertBasicKey:
    """Tests for POST /api/v1/generated-api-keys/upsert"""

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_upsert_basic_key_create_success(self, mock_service_cls, client_as_admin, sample_basic_key_data):
        mock_service_cls.return_value.upsert_basic_key.return_value = {"id": 1, **sample_basic_key_data}
        response = client_as_admin.post("/api/v1/generated-api-keys/upsert", json=sample_basic_key_data)
        assert response.status_code == 200

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_upsert_basic_key_update_success(self, mock_service_cls, client_as_admin):
        data = {"name": "Updated Key", "key_value": "tk_updated"}
        mock_service_cls.return_value.upsert_basic_key.return_value = {"id": 1}
        response = client_as_admin.post("/api/v1/generated-api-keys/upsert?id=1", json=data)
        assert response.status_code == 200

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_upsert_basic_key_missing_name(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/generated-api-keys/upsert", json={
            "key_value": "tk_test"
        })
        assert response.status_code == 400
        assert "name and key_value are required" in response.json()["detail"]

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_upsert_basic_key_missing_key_value(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/generated-api-keys/upsert", json={
            "name": "Test Key"
        })
        assert response.status_code == 400

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_upsert_basic_key_empty_body(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/generated-api-keys/upsert", json={})
        assert response.status_code == 400

    def test_upsert_basic_key_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/generated-api-keys/upsert", json={
            "name": "Key", "key_value": "tk_test"
        })
        assert response.status_code in (401, 403)


# ─── POST /api/v1/generated-api-keys/upsert-full — Upsert Full Key ───

class TestUpsertFullKey:
    """Tests for POST /api/v1/generated-api-keys/upsert-full"""

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_upsert_full_key_create_success(self, mock_service_cls, client_as_admin, sample_full_key_data):
        mock_service_cls.return_value.upsert_full_key.return_value = {"id": 1}
        response = client_as_admin.post("/api/v1/generated-api-keys/upsert-full", json=sample_full_key_data)
        assert response.status_code == 200

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_upsert_full_key_update_success(self, mock_service_cls, client_as_admin, sample_full_key_data):
        mock_service_cls.return_value.upsert_full_key.return_value = {"id": 1}
        response = client_as_admin.post("/api/v1/generated-api-keys/upsert-full?id=1", json=sample_full_key_data)
        assert response.status_code == 200

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_upsert_full_key_minimal_required_fields(self, mock_service_cls, client_as_admin):
        data = {"name": "Min Key", "key_value": "tk_min"}
        mock_service_cls.return_value.upsert_full_key.return_value = {"id": 1}
        response = client_as_admin.post("/api/v1/generated-api-keys/upsert-full", json=data)
        assert response.status_code == 200

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_upsert_full_key_missing_name(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/generated-api-keys/upsert-full", json={
            "key_value": "tk_test"
        })
        assert response.status_code == 400
        assert "name and key_value are required" in response.json()["detail"]

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_upsert_full_key_missing_key_value(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/generated-api-keys/upsert-full", json={
            "name": "Key"
        })
        assert response.status_code == 400

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_upsert_full_key_empty_body(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/generated-api-keys/upsert-full", json={})
        assert response.status_code == 400

    def test_upsert_full_key_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/generated-api-keys/upsert-full", json={
            "name": "Key", "key_value": "tk_test"
        })
        assert response.status_code in (401, 403)


# ─── GET /api/v1/generated-api-keys/list — Get All Keys ───

class TestGetAllKeys:
    """Tests for GET /api/v1/generated-api-keys/list"""

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_get_all_keys_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_keys.return_value = [{"id": 1, "name": "Key1"}]
        response = client_as_member.get("/api/v1/generated-api-keys/list")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_get_all_keys_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_keys.return_value = []
        response = client_as_member.get("/api/v1/generated-api-keys/list")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_all_keys_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/generated-api-keys/list")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/generated-api-keys/get — Get Key ───

class TestGetKey:
    """Tests for GET /api/v1/generated-api-keys/get"""

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_get_key_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_key_by_id.return_value = {"id": 1, "name": "Key1"}
        response = client_as_member.get("/api/v1/generated-api-keys/get?key_id=1")
        assert response.status_code == 200

    def test_get_key_missing_id(self, client_as_member):
        response = client_as_member.get("/api/v1/generated-api-keys/get")
        assert response.status_code == 422

    def test_get_key_invalid_id(self, client_as_member):
        response = client_as_member.get("/api/v1/generated-api-keys/get?key_id=abc")
        assert response.status_code == 422

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_get_key_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_key_by_id.side_effect = HTTPException(
            status_code=404, detail="Key not found"
        )
        response = client_as_member.get("/api/v1/generated-api-keys/get?key_id=999")
        assert response.status_code == 404

    def test_get_key_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/generated-api-keys/get?key_id=1")
        assert response.status_code in (401, 403)


# ─── DELETE /api/v1/generated-api-keys/delete — Delete Key ───

class TestDeleteKey:
    """Tests for DELETE /api/v1/generated-api-keys/delete"""

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_delete_key_success(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.delete_key.return_value = {"message": "deleted"}
        response = client_as_admin.delete("/api/v1/generated-api-keys/delete?key_id=1")
        assert response.status_code == 200

    def test_delete_key_missing_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/generated-api-keys/delete")
        assert response.status_code == 422

    def test_delete_key_invalid_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/generated-api-keys/delete?key_id=abc")
        assert response.status_code == 422

    @patch("ee.api.v1.generated_api_keys.GeneratedApiKeyService")
    def test_delete_key_not_found(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.delete_key.side_effect = HTTPException(
            status_code=404, detail="Key not found"
        )
        response = client_as_admin.delete("/api/v1/generated-api-keys/delete?key_id=999")
        assert response.status_code == 404

    def test_delete_key_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/generated-api-keys/delete?key_id=1")
        assert response.status_code in (401, 403)
