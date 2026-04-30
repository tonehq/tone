"""Tests for Service Providers API endpoints.

Source: core/api/v1/service_providers.py
"""

import pytest
from uuid import UUID
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException

EXPECTED_ORG_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
EXPECTED_USER_ID = 1


# ─── Fixtures ───

@pytest.fixture
def sample_provider_data():
    return {
        "name": "openai",
        "display_name": "OpenAI",
        "provider_type": "llm",
        "auth_type": "api_key",
    }


# ─── POST /api/v1/service-providers/upsert — Upsert Service Provider ───

class TestUpsertServiceProvider:
    """Tests for POST /api/v1/service-providers/upsert"""

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_upsert_provider_create_success(self, mock_service_cls, client_as_admin, sample_provider_data):
        mock_service_cls.return_value.upsert_service_provider.return_value = {"id": 1, **sample_provider_data}
        response = client_as_admin.post("/api/v1/service-providers/upsert", json=sample_provider_data)
        assert response.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID, user_id=EXPECTED_USER_ID)

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_upsert_provider_with_optional_fields(self, mock_service_cls, client_as_admin, sample_provider_data):
        data = {
            **sample_provider_data,
            "description": "LLM provider",
            "logo_url": "https://example.com/logo.png",
            "website_url": "https://openai.com",
            "supports_streaming": True,
        }
        mock_service_cls.return_value.upsert_service_provider.return_value = {"id": 1}
        response = client_as_admin.post("/api/v1/service-providers/upsert", json=data)
        assert response.status_code == 200

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_upsert_provider_missing_name(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/service-providers/upsert", json={
            "display_name": "Test", "provider_type": "llm", "auth_type": "api_key"
        })
        assert response.status_code == 400
        assert "name, display_name, provider_type, and auth_type are required" in response.json()["detail"]

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_upsert_provider_missing_display_name(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/service-providers/upsert", json={
            "name": "test", "provider_type": "llm", "auth_type": "api_key"
        })
        assert response.status_code == 400

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_upsert_provider_missing_provider_type(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/service-providers/upsert", json={
            "name": "test", "display_name": "Test", "auth_type": "api_key"
        })
        assert response.status_code == 400

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_upsert_provider_missing_auth_type(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/service-providers/upsert", json={
            "name": "test", "display_name": "Test", "provider_type": "llm"
        })
        assert response.status_code == 400

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_upsert_provider_empty_body(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/service-providers/upsert", json={})
        assert response.status_code == 400

    def test_upsert_provider_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/service-providers/upsert", json={
            "name": "t", "display_name": "T", "provider_type": "llm", "auth_type": "api_key"
        })
        assert response.status_code in (401, 403)


# ─── POST /api/v1/service-providers/list — Get All Service Providers ───

class TestGetAllServiceProviders:
    """Tests for POST /api/v1/service-providers/list"""

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_get_all_providers_success(self, mock_service_cls, client_as_member, mock_db):
        mock_service_cls.return_value.get_all_service_providers.return_value = [
            {"id": 1, "name": "openai", "provider_type": "llm"}
        ]
        mock_db.query.return_value.filter.return_value.distinct.return_value.all.return_value = []
        response = client_as_member.post("/api/v1/service-providers/list", json={})
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID, user_id=EXPECTED_USER_ID)

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_get_all_providers_filter_by_type(self, mock_service_cls, client_as_member, mock_db):
        mock_service_cls.return_value.get_all_service_providers.return_value = []
        mock_db.query.return_value.filter.return_value.distinct.return_value.all.return_value = []
        response = client_as_member.post("/api/v1/service-providers/list", json={"provider_type": "tts"})
        assert response.status_code == 200

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_get_all_providers_empty(self, mock_service_cls, client_as_member, mock_db):
        mock_service_cls.return_value.get_all_service_providers.return_value = []
        mock_db.query.return_value.filter.return_value.distinct.return_value.all.return_value = []
        response = client_as_member.post("/api/v1/service-providers/list", json={})
        assert response.status_code == 200
        assert response.json() == []

    def test_get_all_providers_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/service-providers/list", json={})
        assert response.status_code in (401, 403)


# ─── POST /api/v1/service-providers/get — Get Service Provider ───

class TestGetServiceProvider:
    """Tests for POST /api/v1/service-providers/get"""

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_get_provider_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_service_provider.return_value = {"id": 1, "name": "openai"}
        response = client_as_member.post("/api/v1/service-providers/get", json={"provider_id": 1})
        assert response.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID, user_id=EXPECTED_USER_ID)

    def test_get_provider_missing_id(self, client_as_member):
        response = client_as_member.post("/api/v1/service-providers/get", json={})
        assert response.status_code == 400

    def test_get_provider_invalid_id(self, client_as_member):
        response = client_as_member.post("/api/v1/service-providers/get", json={"provider_id": "abc"})
        assert response.status_code == 400

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_get_provider_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_service_provider.side_effect = HTTPException(
            status_code=404, detail="Provider not found"
        )
        response = client_as_member.post("/api/v1/service-providers/get", json={"provider_id": 999})
        assert response.status_code == 404

    def test_get_provider_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/service-providers/get", json={"provider_id": 1})
        assert response.status_code in (401, 403)


# ─── DELETE /api/v1/service-providers/delete — Delete Service Provider ───

class TestDeleteServiceProvider:
    """Tests for DELETE /api/v1/service-providers/delete"""

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_delete_provider_success(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.delete_service_provider.return_value = {"message": "deleted"}
        response = client_as_admin.delete("/api/v1/service-providers/delete?provider_id=1")
        assert response.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID, user_id=EXPECTED_USER_ID)

    def test_delete_provider_missing_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/service-providers/delete")
        assert response.status_code == 422

    def test_delete_provider_invalid_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/service-providers/delete?provider_id=abc")
        assert response.status_code == 422

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_delete_provider_not_found(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.delete_service_provider.side_effect = HTTPException(
            status_code=404, detail="Provider not found"
        )
        response = client_as_admin.delete("/api/v1/service-providers/delete?provider_id=999")
        assert response.status_code == 404

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_delete_provider_system_provider(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.delete_service_provider.side_effect = HTTPException(
            status_code=400, detail="Cannot delete system provider"
        )
        response = client_as_admin.delete("/api/v1/service-providers/delete?provider_id=1")
        assert response.status_code == 400

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_upsert_provider_duplicate_name_and_type(self, mock_service_cls, client_as_admin, sample_provider_data):
        mock_service_cls.return_value.upsert_service_provider.side_effect = HTTPException(
            status_code=409, detail="Provider with this name and type already exists"
        )
        response = client_as_admin.post("/api/v1/service-providers/upsert", json=sample_provider_data)
        assert response.status_code == 409

    def test_delete_provider_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/service-providers/delete?provider_id=1")
        assert response.status_code in (401, 403)
