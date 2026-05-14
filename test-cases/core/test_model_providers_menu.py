"""Tests for Model Providers Menu API endpoints (Core edition).

Source: core/api/v1/model_providers_menu.py
"""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# POST /api/v1/model-providers-menu/upsert
# ---------------------------------------------------------------------------
class TestUpsertModelProviderMenu:
    @patch("ee.api.v1.model_providers_menu.ModelProviderMenuService")
    def test_success(self, mock_service_cls, client_as_admin):
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
        assert resp.json()["name"] == "openai"
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

    @patch("ee.api.v1.model_providers_menu.ModelProviderMenuService")
    def test_missing_required_fields(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/model-providers-menu/upsert",
            json={
                "name": "openai",
                "display_name": "OpenAI",
            },
        )
        assert resp.status_code == 400

    @patch("ee.api.v1.model_providers_menu.ModelProviderMenuService")
    def test_missing_name(self, mock_service_cls, client_as_admin):
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


# ---------------------------------------------------------------------------
# POST /api/v1/model-providers-menu/list
# ---------------------------------------------------------------------------
class TestListModelProviderMenus:
    @patch("ee.api.v1.model_providers_menu.ModelProviderMenuService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_model_provider_menus.return_value = {
            "data": [{"id": 1, "name": "openai"}],
            "pagination": {"page": 1, "page_size": 10, "total": 1},
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

    @patch("ee.api.v1.model_providers_menu.ModelProviderMenuService")
    def test_with_filters(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_model_provider_menus.return_value = {
            "data": [],
            "pagination": {"page": 1, "page_size": 5, "total": 0},
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
    @patch("ee.api.v1.model_providers_menu.ModelProviderMenuService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_model_provider_menu.return_value = {
            "id": 1,
            "name": "openai",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/model-providers-menu/get", json={"provider_id": 1}
        )

        assert resp.status_code == 200
        assert resp.json()["name"] == "openai"
        mock_instance.get_model_provider_menu.assert_called_once_with(1)

    def test_missing_provider_id(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-providers-menu/get", json={})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/v1/model-providers-menu/delete
# ---------------------------------------------------------------------------
class TestDeleteModelProviderMenu:
    @patch("ee.api.v1.model_providers_menu.ModelProviderMenuService")
    def test_success(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.delete_model_provider_menu.return_value = {"message": "Deleted"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/model-providers-menu/delete", params={"provider_id": 1}
        )

        assert resp.status_code == 200
        mock_instance.delete_model_provider_menu.assert_called_once_with(1)

    def test_missing_provider_id(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/model-providers-menu/delete")
        assert resp.status_code == 422
