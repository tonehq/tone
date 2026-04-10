"""Tests for API Keys API endpoints (EE edition).

Source: ee/api/v1/api_keys.py
Integration tests — real DB, real endpoints, no mocks.
"""

import pytest


# ─── POST /api/v1/api-keys/upsert ───

class TestUpsertApiKey:
    """Tests for POST /api/v1/api-keys/upsert"""

    def test_upsert_api_key_missing_service_provider_id(self, client_as_admin):
        response = client_as_admin.post("/api/v1/api-keys/upsert", json={
            "name": "Key", "api_key": "sk-test"
        })
        assert response.status_code == 400

    def test_upsert_api_key_missing_name(self, client_as_admin):
        response = client_as_admin.post("/api/v1/api-keys/upsert", json={
            "service_provider_id": 1, "api_key": "sk-test"
        })
        assert response.status_code == 400

    def test_upsert_api_key_missing_api_key(self, client_as_admin):
        response = client_as_admin.post("/api/v1/api-keys/upsert", json={
            "service_provider_id": 1, "name": "Key"
        })
        assert response.status_code == 400

    def test_upsert_api_key_empty_body(self, client_as_admin):
        response = client_as_admin.post("/api/v1/api-keys/upsert", json={})
        assert response.status_code == 400

    def test_upsert_api_key_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/api-keys/upsert", json={
            "service_provider_id": 1, "name": "Key", "api_key": "sk-test"
        })
        assert response.status_code in (401, 403)


# ─── GET /api/v1/api-keys/list ───

class TestGetAllApiKeys:
    """Tests for GET /api/v1/api-keys/list"""

    def test_get_all_api_keys_returns_200(self, client_as_member):
        response = client_as_member.get("/api/v1/api-keys/list")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_all_api_keys_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/api-keys/list")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/api-keys/get ───

class TestGetApiKey:
    """Tests for GET /api/v1/api-keys/get"""

    def test_get_api_key_missing_id(self, client_as_member):
        response = client_as_member.get("/api/v1/api-keys/get")
        assert response.status_code == 422

    def test_get_api_key_invalid_id(self, client_as_member):
        response = client_as_member.get("/api/v1/api-keys/get?api_key_id=abc")
        assert response.status_code == 422

    def test_get_api_key_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/api-keys/get?api_key_id=1")
        assert response.status_code in (401, 403)


# ─── DELETE /api/v1/api-keys/delete ───

class TestDeleteApiKey:
    """Tests for DELETE /api/v1/api-keys/delete"""

    def test_delete_api_key_missing_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/api-keys/delete")
        assert response.status_code == 422

    def test_delete_api_key_invalid_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/api-keys/delete?api_key_id=abc")
        assert response.status_code == 422

    def test_delete_api_key_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/api-keys/delete?api_key_id=1")
        assert response.status_code in (401, 403)


# ─── POST /api/v1/api-keys/validate ───

class TestValidateApiKey:
    """Tests for POST /api/v1/api-keys/validate"""

    def test_validate_api_key_missing_api_key_id(self, client_as_admin):
        response = client_as_admin.post("/api/v1/api-keys/validate", json={
            "is_valid": True
        })
        assert response.status_code == 400

    def test_validate_api_key_missing_is_valid(self, client_as_admin):
        response = client_as_admin.post("/api/v1/api-keys/validate", json={
            "api_key_id": 1
        })
        assert response.status_code == 400

    def test_validate_api_key_empty_body(self, client_as_admin):
        response = client_as_admin.post("/api/v1/api-keys/validate", json={})
        assert response.status_code == 400

    def test_validate_api_key_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/api-keys/validate", json={
            "api_key_id": 1, "is_valid": True
        })
        assert response.status_code in (401, 403)
