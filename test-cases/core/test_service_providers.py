"""Tests for Service Providers API endpoints (Core edition).

Source: core/api/v1/service_providers.py
Postman: postman_collection/service_providers.postman_collection.json
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# POST /api/v1/service-providers/upsert
# ---------------------------------------------------------------------------
class TestUpsertServiceProvider:
    @patch("core.api.v1.service_providers.AccountService")
    @patch("core.api.v1.service_providers.ServiceProviderService")
    def test_create_success(self, mock_service_cls, mock_account_cls, client_as_admin):
        """Postman: Upsert Service Provider - Create (200)."""
        mock_instance = MagicMock()
        mock_instance.upsert_service_provider.return_value = {
            "id": 1,
            "uuid": "550e8400-e29b-41d4-a716-446655440000",
            "name": "openai",
            "display_name": "OpenAI",
            "provider_type": "llm",
            "auth_type": "api_key",
            "status": "active",
            "supports_streaming": True,
            "is_system": False,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/service-providers/upsert",
            json={
                "name": "openai",
                "display_name": "OpenAI",
                "provider_type": "llm",
                "auth_type": "api_key",
                "description": "OpenAI LLM Provider",
                "logo_url": "https://example.com/openai.png",
                "website_url": "https://openai.com",
                "documentation_url": "https://platform.openai.com/docs",
                "base_url": "https://api.openai.com/v1",
                "supports_streaming": True,
                "config_schema": {},
                "is_system": False,
                "api_key": {
                    "api_key": "sk-...",
                    "name": "OpenAI Key",
                },
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "openai"
        assert data["provider_type"] == "llm"
        mock_instance.upsert_service_provider.assert_called_once_with(
            name="openai",
            display_name="OpenAI",
            provider_type="llm",
            auth_type="api_key",
            description="OpenAI LLM Provider",
            logo_url="https://example.com/openai.png",
            website_url="https://openai.com",
            documentation_url="https://platform.openai.com/docs",
            base_url="https://api.openai.com/v1",
            supports_streaming=True,
            config_schema={},
            is_system=False,
            provider_status=None,
            provider_id=None,
        )

    @patch("core.api.v1.service_providers.ServiceProviderService")
    def test_create_minimal(self, mock_service_cls, client_as_admin):
        """Minimal required fields only."""
        mock_instance = MagicMock()
        mock_instance.upsert_service_provider.return_value = {
            "id": 1,
            "name": "openai",
            "display_name": "OpenAI",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/service-providers/upsert",
            json={
                "name": "openai",
                "display_name": "OpenAI",
                "provider_type": "llm",
                "auth_type": "api_key",
            },
        )

        assert resp.status_code == 200
        assert resp.json()["name"] == "openai"
        mock_instance.upsert_service_provider.assert_called_once_with(
            name="openai",
            display_name="OpenAI",
            provider_type="llm",
            auth_type="api_key",
            description=None,
            logo_url=None,
            website_url=None,
            documentation_url=None,
            base_url=None,
            supports_streaming=False,
            config_schema=None,
            is_system=False,
            provider_status=None,
            provider_id=None,
        )

    @patch("core.api.v1.service_providers.ServiceProviderService")
    def test_with_optional_fields(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_service_provider.return_value = {"id": 1}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/service-providers/upsert",
            json={
                "name": "openai",
                "display_name": "OpenAI",
                "provider_type": "llm",
                "auth_type": "api_key",
                "description": "OpenAI LLM provider",
                "logo_url": "https://example.com/logo.png",
                "supports_streaming": True,
                "is_system": True,
                "status": "active",
                "id": 42,
            },
        )

        assert resp.status_code == 200
        mock_instance.upsert_service_provider.assert_called_once_with(
            name="openai",
            display_name="OpenAI",
            provider_type="llm",
            auth_type="api_key",
            description="OpenAI LLM provider",
            logo_url="https://example.com/logo.png",
            website_url=None,
            documentation_url=None,
            base_url=None,
            supports_streaming=True,
            config_schema=None,
            is_system=True,
            provider_status="active",
            provider_id=42,
        )

    def test_missing_fields(self, client_as_admin):
        """Postman: Upsert Service Provider - Missing Fields (400)."""
        resp = client_as_admin.post(
            "/api/v1/service-providers/upsert",
            json={
                "display_name": "OpenAI",
                "provider_type": "llm",
                "auth_type": "api_key",
            },
        )
        assert resp.status_code == 400
        assert "name" in resp.json()["detail"]

    def test_missing_display_name(self, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/service-providers/upsert",
            json={
                "name": "openai",
                "provider_type": "llm",
                "auth_type": "api_key",
            },
        )
        assert resp.status_code == 400

    def test_missing_provider_type(self, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/service-providers/upsert",
            json={
                "name": "openai",
                "display_name": "OpenAI",
                "auth_type": "api_key",
            },
        )
        assert resp.status_code == 400

    def test_missing_auth_type(self, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/service-providers/upsert",
            json={
                "name": "openai",
                "display_name": "OpenAI",
                "provider_type": "llm",
            },
        )
        assert resp.status_code == 400

    @patch("core.api.v1.service_providers.ServiceProviderService")
    def test_service_error(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_service_provider.side_effect = HTTPException(
            status_code=409, detail="Duplicate name+type"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/service-providers/upsert",
            json={
                "name": "openai",
                "display_name": "OpenAI",
                "provider_type": "llm",
                "auth_type": "api_key",
            },
        )
        assert resp.status_code == 409

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/service-providers/upsert",
            json={
                "name": "openai",
                "display_name": "OpenAI",
                "provider_type": "llm",
                "auth_type": "api_key",
            },
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/service-providers/list
# ---------------------------------------------------------------------------
class TestListServiceProviders:
    @patch("core.api.v1.service_providers.ServiceProviderService")
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Get All Service Providers - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.get_all_service_providers.return_value = {
            "data": [
                {
                    "id": 1,
                    "name": "openai",
                    "display_name": "OpenAI",
                    "provider_type": "llm",
                    "status": "active",
                }
            ],
            "pagination": {
                "page": 1,
                "page_size": 10,
                "total": 1,
                "total_pages": 1,
            },
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/service-providers/list",
            json={
                "provider_type": "llm",
                "name": "open",
                "status": "active",
                "sort": "-created_at",
                "page": 1,
                "page_size": 10,
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "pagination" in data
        mock_instance.get_all_service_providers.assert_called_once_with(
            provider_type="llm",
            name="open",
            status_filter="active",
            sort_by="created_at",
            sort_order="desc",
            page=1,
            page_size=10,
            exclude_existing_services=False,
        )

    @patch("core.api.v1.service_providers.ServiceProviderService")
    def test_empty_body(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_service_providers.return_value = {
            "data": [],
            "pagination": {"page": 1, "page_size": None, "total": 0, "total_pages": 0},
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post("/api/v1/service-providers/list", json={})

        assert resp.status_code == 200
        mock_instance.get_all_service_providers.assert_called_once_with(
            provider_type=None,
            name=None,
            status_filter=None,
            sort_by="created_at",
            sort_order="desc",
            page=1,
            page_size=None,
            exclude_existing_services=False,
        )

    @patch("core.api.v1.service_providers.ServiceProviderService")
    def test_with_filters_and_pagination(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_service_providers.return_value = {
            "data": [],
            "pagination": {"page": 2, "page_size": 5, "total": 0, "total_pages": 0},
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/service-providers/list",
            json={
                "provider_type": "stt",
                "name": "deep",
                "status": "active",
                "sort": "name",
                "page": 2,
                "page_size": 5,
            },
        )

        assert resp.status_code == 200
        mock_instance.get_all_service_providers.assert_called_once_with(
            provider_type="stt",
            name="deep",
            status_filter="active",
            sort_by="name",
            sort_order="asc",
            page=2,
            page_size=5,
            exclude_existing_services=False,
        )


# ---------------------------------------------------------------------------
# POST /api/v1/service-providers/get
# ---------------------------------------------------------------------------
class TestGetServiceProvider:
    @patch("core.api.v1.service_providers.ServiceProviderService")
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Get Service Provider - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.get_service_provider.return_value = {
            "id": 1,
            "name": "openai",
            "display_name": "OpenAI",
            "provider_type": "llm",
            "auth_type": "api_key",
            "status": "active",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/service-providers/get", json={"provider_id": 1}
        )

        assert resp.status_code == 200
        assert resp.json()["name"] == "openai"
        mock_instance.get_service_provider.assert_called_once_with(1)

    def test_missing_provider_id(self, client_as_member):
        """Postman: Get Service Provider - Missing ID (400)."""
        resp = client_as_member.post("/api/v1/service-providers/get", json={})
        assert resp.status_code == 400
        assert "provider_id is required" in resp.json()["detail"]

    @patch("core.api.v1.service_providers.ServiceProviderService")
    def test_not_found(self, mock_service_cls, client_as_member):
        """Postman: Get Service Provider - Not Found (404)."""
        mock_instance = MagicMock()
        mock_instance.get_service_provider.side_effect = HTTPException(
            status_code=404, detail="Service provider not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/service-providers/get", json={"provider_id": 999}
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_invalid_provider_id(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/service-providers/get", json={"provider_id": "abc"}
        )
        assert resp.status_code == 400
        assert "integer" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# DELETE /api/v1/service-providers/delete
# ---------------------------------------------------------------------------
class TestDeleteServiceProvider:
    @patch("core.api.v1.service_providers.ServiceProviderService")
    def test_success(self, mock_service_cls, client_as_admin):
        """Postman: Delete Service Provider - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.delete_service_provider.return_value = {
            "message": "Service provider deleted successfully"
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/service-providers/delete", params={"provider_id": 1}
        )

        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()
        mock_instance.delete_service_provider.assert_called_once_with(1)

    @patch("core.api.v1.service_providers.ServiceProviderService")
    def test_not_found(self, mock_service_cls, client_as_admin):
        """Postman: Delete Service Provider - Not Found (404)."""
        mock_instance = MagicMock()
        mock_instance.delete_service_provider.side_effect = HTTPException(
            status_code=404, detail="Service provider not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/service-providers/delete", params={"provider_id": 999}
        )
        assert resp.status_code == 404

    @patch("core.api.v1.service_providers.ServiceProviderService")
    def test_system_provider_cannot_be_deleted(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.delete_service_provider.side_effect = HTTPException(
            status_code=403, detail="System providers cannot be deleted"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/service-providers/delete", params={"provider_id": 1}
        )
        assert resp.status_code == 403
        assert "System" in resp.json()["detail"]

    def test_missing_provider_id(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/service-providers/delete")
        assert resp.status_code == 422
