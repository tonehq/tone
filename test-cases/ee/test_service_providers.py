"""Tests for Service Providers API endpoints (EE edition).

Source: ee/api/v1/service_providers.py
Integration tests — real DB, real endpoints, no mocks.
"""

import pytest


# ─── POST /api/v1/service-providers/upsert ───

class TestUpsertServiceProvider:
    """Tests for POST /api/v1/service-providers/upsert"""

    def test_upsert_provider_missing_name(self, client_as_admin):
        response = client_as_admin.post("/api/v1/service-providers/upsert", json={
            "display_name": "Test", "provider_type": "llm", "auth_type": "api_key"
        })
        assert response.status_code == 400

    def test_upsert_provider_missing_display_name(self, client_as_admin):
        response = client_as_admin.post("/api/v1/service-providers/upsert", json={
            "name": "test", "provider_type": "llm", "auth_type": "api_key"
        })
        assert response.status_code == 400

    def test_upsert_provider_missing_provider_type(self, client_as_admin):
        response = client_as_admin.post("/api/v1/service-providers/upsert", json={
            "name": "test", "display_name": "Test", "auth_type": "api_key"
        })
        assert response.status_code == 400

    def test_upsert_provider_missing_auth_type(self, client_as_admin):
        response = client_as_admin.post("/api/v1/service-providers/upsert", json={
            "name": "test", "display_name": "Test", "provider_type": "llm"
        })
        assert response.status_code == 400

    def test_upsert_provider_empty_body(self, client_as_admin):
        response = client_as_admin.post("/api/v1/service-providers/upsert", json={})
        assert response.status_code == 400

    def test_upsert_provider_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/service-providers/upsert", json={
            "name": "t", "display_name": "T", "provider_type": "llm", "auth_type": "api_key"
        })
        assert response.status_code in (401, 403)


# ─── POST /api/v1/service-providers/list ───

class TestGetAllServiceProviders:
    """Tests for POST /api/v1/service-providers/list"""

    def test_get_all_providers_returns_200(self, client_as_member):
        response = client_as_member.post("/api/v1/service-providers/list", json={})
        assert response.status_code == 200

    def test_get_all_providers_filter_by_type(self, client_as_member):
        response = client_as_member.post("/api/v1/service-providers/list", json={
            "provider_type": "tts"
        })
        assert response.status_code == 200

    def test_get_all_providers_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/service-providers/list", json={})
        assert response.status_code in (401, 403)


# ─── POST /api/v1/service-providers/get ───

class TestGetServiceProvider:
    """Tests for POST /api/v1/service-providers/get"""

    def test_get_provider_missing_id(self, client_as_member):
        response = client_as_member.post("/api/v1/service-providers/get", json={})
        assert response.status_code == 400

    def test_get_provider_invalid_id(self, client_as_member):
        response = client_as_member.post("/api/v1/service-providers/get", json={
            "provider_id": "abc"
        })
        assert response.status_code == 400

    def test_get_provider_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/service-providers/get", json={
            "provider_id": 1
        })
        assert response.status_code in (401, 403)


# ─── DELETE /api/v1/service-providers/delete ───

class TestDeleteServiceProvider:
    """Tests for DELETE /api/v1/service-providers/delete"""

    def test_delete_provider_missing_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/service-providers/delete")
        assert response.status_code == 422

    def test_delete_provider_invalid_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/service-providers/delete?provider_id=abc")
        assert response.status_code == 422

    def test_delete_provider_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/service-providers/delete?provider_id=1")
        assert response.status_code in (401, 403)
