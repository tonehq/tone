"""Tests for Hosting Providers API endpoints (Core edition).

Source: core/api/v1/hosting_providers.py
Postman: postman_collection/hosting_providers.postman_collection.json
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# POST /api/v1/hosting-providers/upsert
# ---------------------------------------------------------------------------
class TestUpsertHostingProvider:
    @patch("core.api.v1.hosting_providers.HostingProviderService")
    def test_create_success(self, mock_service_cls, client_as_admin):
        """Postman: Upsert - Create (200)."""
        mock_instance = MagicMock()
        mock_instance.upsert_hosting_provider.return_value = {
            "id": 1,
            "name": "vultr",
            "display_name": "Vultr",
            "status": "active",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/hosting-providers/upsert",
            json={
                "name": "vultr",
                "display_name": "Vultr",
                "description": "Vultr Cloud Hosting",
                "logo_url": "https://example.com/vultr.png",
                "website_url": "https://vultr.com",
                "is_system": False,
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "vultr"
        assert data["status"] == "active"
        mock_instance.upsert_hosting_provider.assert_called_once_with(
            name="vultr",
            display_name="Vultr",
            description="Vultr Cloud Hosting",
            logo_url="https://example.com/vultr.png",
            website_url="https://vultr.com",
            is_system=False,
            provider_status=None,
            provider_id=None,
        )

    @patch("core.api.v1.hosting_providers.HostingProviderService")
    def test_minimal_fields(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_hosting_provider.return_value = {
            "id": 1,
            "name": "vultr",
            "display_name": "Vultr",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/hosting-providers/upsert",
            json={
                "name": "vultr",
                "display_name": "Vultr",
            },
        )

        assert resp.status_code == 200
        mock_instance.upsert_hosting_provider.assert_called_once_with(
            name="vultr",
            display_name="Vultr",
            description=None,
            logo_url=None,
            website_url=None,
            is_system=False,
            provider_status=None,
            provider_id=None,
        )

    def test_missing_display_name(self, client_as_admin):
        """Postman: Upsert - Missing Fields (400)."""
        resp = client_as_admin.post(
            "/api/v1/hosting-providers/upsert",
            json={"name": "vultr"},
        )
        assert resp.status_code == 400
        assert "name and display_name are required" in resp.json()["detail"]

    def test_missing_name(self, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/hosting-providers/upsert",
            json={"display_name": "Vultr"},
        )
        assert resp.status_code == 400

    @patch("core.api.v1.hosting_providers.HostingProviderService")
    def test_with_optional_status_and_id(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_hosting_provider.return_value = {"id": 5}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/hosting-providers/upsert",
            json={
                "name": "vultr",
                "display_name": "Vultr",
                "status": "active",
                "id": 5,
            },
        )

        assert resp.status_code == 200
        mock_instance.upsert_hosting_provider.assert_called_once_with(
            name="vultr",
            display_name="Vultr",
            description=None,
            logo_url=None,
            website_url=None,
            is_system=False,
            provider_status="active",
            provider_id=5,
        )

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/hosting-providers/upsert",
            json={"name": "vultr", "display_name": "Vultr"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/hosting-providers/list
# ---------------------------------------------------------------------------
class TestListHostingProviders:
    @patch("core.api.v1.hosting_providers.HostingProviderService")
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Get All - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.get_all_hosting_providers.return_value = {
            "data": [
                {
                    "id": 1,
                    "name": "vultr",
                    "display_name": "Vultr",
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
            "/api/v1/hosting-providers/list",
            json={
                "name": "vultr",
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
        mock_instance.get_all_hosting_providers.assert_called_once_with(
            name="vultr",
            status_filter="active",
            sort_by="created_at",
            sort_order="desc",
            page=1,
            page_size=10,
        )

    @patch("core.api.v1.hosting_providers.HostingProviderService")
    def test_empty_body(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_hosting_providers.return_value = {
            "data": [],
            "pagination": {"page": 1, "page_size": None, "total": 0, "total_pages": 0},
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post("/api/v1/hosting-providers/list", json={})

        assert resp.status_code == 200
        mock_instance.get_all_hosting_providers.assert_called_once_with(
            name=None,
            status_filter=None,
            sort_by="created_at",
            sort_order="desc",
            page=1,
            page_size=None,
        )

    @patch("core.api.v1.hosting_providers.HostingProviderService")
    def test_with_filters(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_hosting_providers.return_value = {
            "data": [],
            "pagination": {"page": 1, "page_size": 5, "total": 0, "total_pages": 0},
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/hosting-providers/list",
            json={
                "name": "vultr",
                "status": "active",
                "sort": "name",
                "page": 1,
                "page_size": 5,
            },
        )

        assert resp.status_code == 200
        mock_instance.get_all_hosting_providers.assert_called_once_with(
            name="vultr",
            status_filter="active",
            sort_by="name",
            sort_order="asc",
            page=1,
            page_size=5,
        )


# ---------------------------------------------------------------------------
# POST /api/v1/hosting-providers/get
# ---------------------------------------------------------------------------
class TestGetHostingProvider:
    @patch("core.api.v1.hosting_providers.HostingProviderService")
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Get - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.get_hosting_provider.return_value = {
            "id": 1,
            "name": "vultr",
            "display_name": "Vultr",
            "status": "active",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/hosting-providers/get", json={"provider_id": 1}
        )

        assert resp.status_code == 200
        assert resp.json()["name"] == "vultr"
        mock_instance.get_hosting_provider.assert_called_once_with(1)

    def test_missing_provider_id(self, client_as_member):
        """Postman: Get - Missing ID (400)."""
        resp = client_as_member.post("/api/v1/hosting-providers/get", json={})
        assert resp.status_code == 400
        assert "provider_id is required" in resp.json()["detail"]

    def test_invalid_provider_id(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/hosting-providers/get", json={"provider_id": "abc"}
        )
        assert resp.status_code == 400
        assert "integer" in resp.json()["detail"]

    @patch("core.api.v1.hosting_providers.HostingProviderService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_hosting_provider.side_effect = HTTPException(
            status_code=404, detail="Hosting provider not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/hosting-providers/get", json={"provider_id": 999}
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/hosting-providers/delete
# ---------------------------------------------------------------------------
class TestDeleteHostingProvider:
    @patch("core.api.v1.hosting_providers.HostingProviderService")
    def test_success(self, mock_service_cls, client_as_admin):
        """Postman: Delete - Success (200)."""
        mock_instance = MagicMock()
        mock_instance.delete_hosting_provider.return_value = {
            "message": "Hosting provider deleted successfully"
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/hosting-providers/delete", params={"provider_id": 1}
        )

        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()
        mock_instance.delete_hosting_provider.assert_called_once_with(1)

    @patch("core.api.v1.hosting_providers.HostingProviderService")
    def test_not_found(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.delete_hosting_provider.side_effect = HTTPException(
            status_code=404, detail="Not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/hosting-providers/delete", params={"provider_id": 999}
        )
        assert resp.status_code == 404

    def test_missing_provider_id(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/hosting-providers/delete")
        assert resp.status_code == 422
