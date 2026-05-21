"""Tests for Model Providers Menu API endpoints (Core edition).

Source: core/api/v1/model_providers_menu.py
Postman: postman_collection/model_providers_menu.postman_collection.json
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# POST /api/v1/model-providers-menu/upsert
# ---------------------------------------------------------------------------
class TestUpsertModelProviderMenu:
    @patch("core.api.v1.model_providers_menu.ModelProviderMenuService")
    def test_create_success(self, mock_service_cls, client_as_admin):
        """Postman: Upsert - Create (200)."""
        mock_instance = MagicMock()
        mock_instance.upsert_model_provider_menu.return_value = {
            "id": 1,
            "name": "openai",
            "display_name": "OpenAI",
            "provider_type": "llm",
            "auth_type": "api_key",
            "status": "active",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/model-providers-menu/upsert",
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
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "openai"
        assert data["provider_type"] == "llm"
        mock_instance.upsert_model_provider_menu.assert_called_once_with(
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

    @patch("core.api.v1.model_providers_menu.ModelProviderMenuService")
    def test_minimal_fields(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_model_provider_menu.return_value = {
            "id": 1,
            "name": "openai",
            "display_name": "OpenAI",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/model-providers-menu/upsert",
            json={
                "name": "openai",
                "display_name": "OpenAI",
                "provider_type": "llm",
                "auth_type": "api_key",
            },
        )

        assert resp.status_code == 200
        mock_instance.upsert_model_provider_menu.assert_called_once_with(
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

    def test_missing_required_fields(self, client_as_admin):
        """Postman: Upsert - Missing Fields (400)."""
        resp = client_as_admin.post(
            "/api/v1/model-providers-menu/upsert",
            json={
                "name": "openai",
                "display_name": "OpenAI",
            },
        )
        assert resp.status_code == 400
        assert "name, display_name, provider_type, and auth_type are required" in resp.json()["detail"]

    def test_missing_name(self, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/model-providers-menu/upsert",
            json={
                "display_name": "OpenAI",
                "provider_type": "llm",
                "auth_type": "api_key",
            },
        )
        assert resp.status_code == 400
        assert "name" in resp.json()["detail"]

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/model-providers-menu/upsert",
            json={
                "name": "openai",
                "display_name": "OpenAI",
                "provider_type": "llm",
                "auth_type": "api_key",
            },
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/model-providers-menu/list
# ---------------------------------------------------------------------------
class TestListModelProviderMenus:
    @patch("core.api.v1.model_providers_menu.ModelProviderMenuService")
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Get All - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.get_all_model_provider_menus.return_value = {
            "data": [
                {
                    "id": 1,
                    "name": "openai",
                    "display_name": "OpenAI",
                    "provider_type": "llm",
                    "status": "active",
                    "logo_url": "https://example.com/openai.png",
                    "website_url": "https://openai.com",
                    "documentation_url": "https://platform.openai.com/docs",
                    "base_url": "https://api.openai.com/v1",
                    "config_schema": {},
                    "meta_data_schema": {},
                    "models": [],
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
            "/api/v1/model-providers-menu/list",
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
        mock_instance.get_all_model_provider_menus.assert_called_once_with(
            provider_type="llm",
            name="open",
            status_filter="active",
            sort_by="created_at",
            sort_order="desc",
            page=1,
            page_size=10,
        )

    @patch("core.api.v1.model_providers_menu.ModelProviderMenuService")
    def test_empty_body(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_model_provider_menus.return_value = {
            "data": [],
            "pagination": {"page": 1, "page_size": None, "total": 0, "total_pages": 0},
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post("/api/v1/model-providers-menu/list", json={})

        assert resp.status_code == 200
        mock_instance.get_all_model_provider_menus.assert_called_once_with(
            provider_type=None,
            name=None,
            status_filter=None,
            sort_by="created_at",
            sort_order="desc",
            page=1,
            page_size=None,
        )

    @patch("core.api.v1.model_providers_menu.ModelProviderMenuService")
    def test_with_filters(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_model_provider_menus.return_value = {
            "data": [],
            "pagination": {"page": 2, "page_size": 5, "total": 0, "total_pages": 0},
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/model-providers-menu/list",
            json={
                "provider_type": "llm",
                "name": "openai",
                "status": "active",
                "sort": "name",
                "page": 2,
                "page_size": 5,
            },
        )

        assert resp.status_code == 200
        mock_instance.get_all_model_provider_menus.assert_called_once_with(
            provider_type="llm",
            name="openai",
            status_filter="active",
            sort_by="name",
            sort_order="asc",
            page=2,
            page_size=5,
        )


# ---------------------------------------------------------------------------
# POST /api/v1/model-providers-menu/get
# ---------------------------------------------------------------------------
class TestGetModelProviderMenu:
    @patch("core.api.v1.model_providers_menu.ModelProviderMenuService")
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Get - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.get_model_provider_menu.return_value = {
            "id": 1,
            "name": "openai",
            "display_name": "OpenAI",
            "provider_type": "llm",
            "status": "active",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/model-providers-menu/get", json={"provider_id": 1}
        )

        assert resp.status_code == 200
        assert resp.json()["name"] == "openai"
        mock_instance.get_model_provider_menu.assert_called_once_with(1)

    def test_missing_provider_id(self, client_as_member):
        """Postman: Get - Missing ID (400)."""
        resp = client_as_member.post("/api/v1/model-providers-menu/get", json={})
        assert resp.status_code == 400
        assert "provider_id is required" in resp.json()["detail"]

    @patch("core.api.v1.model_providers_menu.ModelProviderMenuService")
    def test_not_found(self, mock_service_cls, client_as_member):
        """Postman: Get - Not Found (404)."""
        mock_instance = MagicMock()
        mock_instance.get_model_provider_menu.side_effect = HTTPException(
            status_code=404, detail="Model provider menu not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/model-providers-menu/get", json={"provider_id": 999}
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_invalid_provider_id(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/model-providers-menu/get", json={"provider_id": "abc"}
        )
        assert resp.status_code == 400
        assert "integer" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# POST /api/v1/model-providers-menu/list-with-accounts
# ---------------------------------------------------------------------------
class TestListProvidersWithAccounts:
    @patch("core.api.v1.model_providers_menu.ModelProviderMenuService")
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: List With Accounts - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.get_providers_with_accounts.return_value = [
            {
                "id": 1,
                "name": "openai",
                "display_name": "OpenAI",
                "provider_type": "llm",
                "accounts": [
                    {
                        "id": 1,
                        "name": "OpenAI Production",
                        "status": "active",
                    }
                ],
            }
        ]
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/model-providers-menu/list-with-accounts",
            json={"provider_type": "llm"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "openai"
        mock_instance.get_providers_with_accounts.assert_called_once_with(
            provider_type="llm",
        )

    @patch("core.api.v1.model_providers_menu.ModelProviderMenuService")
    def test_empty_body(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_providers_with_accounts.return_value = []
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/model-providers-menu/list-with-accounts", json={}
        )

        assert resp.status_code == 200
        mock_instance.get_providers_with_accounts.assert_called_once_with(
            provider_type=None,
        )


# ---------------------------------------------------------------------------
# DELETE /api/v1/model-providers-menu/delete
# ---------------------------------------------------------------------------
class TestDeleteModelProviderMenu:
    @patch("core.api.v1.model_providers_menu.ModelProviderMenuService")
    def test_success(self, mock_service_cls, client_as_admin):
        """Postman: Delete - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.delete_model_provider_menu.return_value = {
            "message": "Model provider menu deleted successfully"
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/model-providers-menu/delete", params={"provider_id": 1}
        )

        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()
        mock_instance.delete_model_provider_menu.assert_called_once_with(1)

    @patch("core.api.v1.model_providers_menu.ModelProviderMenuService")
    def test_not_found(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.delete_model_provider_menu.side_effect = HTTPException(
            status_code=404, detail="Not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/model-providers-menu/delete", params={"provider_id": 999}
        )
        assert resp.status_code == 404

    def test_missing_provider_id(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/model-providers-menu/delete")
        assert resp.status_code == 422
