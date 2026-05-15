"""Tests for Hosting Providers API endpoints (Core edition).

Source: core/api/v1/hosting_providers.py
"""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# POST /api/v1/hosting-providers/upsert
# ---------------------------------------------------------------------------
class TestUpsertHostingProvider:
    @patch("ee.api.v1.hosting_providers.HostingProviderService")
    def test_success(self, mock_service_cls, client_as_admin):
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
        assert resp.json()["name"] == "vultr"
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

    @patch("ee.api.v1.hosting_providers.HostingProviderService")
    def test_missing_required_fields(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/hosting-providers/upsert",
            json={
                "name": "vultr",
            },
        )
        assert resp.status_code == 400
        assert "display_name" in resp.json()["detail"]

    @patch("ee.api.v1.hosting_providers.HostingProviderService")
    def test_missing_name(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/hosting-providers/upsert",
            json={
                "display_name": "Vultr",
            },
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/v1/hosting-providers/list
# ---------------------------------------------------------------------------
class TestListHostingProviders:
    @patch("ee.api.v1.hosting_providers.HostingProviderService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_hosting_providers.return_value = {
            "data": [{"id": 1, "name": "vultr"}],
            "pagination": {"page": 1, "page_size": 10, "total": 1},
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

    @patch("ee.api.v1.hosting_providers.HostingProviderService")
    def test_with_filters(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_hosting_providers.return_value = {
            "data": [],
            "pagination": {"page": 1, "page_size": 5, "total": 0},
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
    @patch("ee.api.v1.hosting_providers.HostingProviderService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_hosting_provider.return_value = {
            "id": 1,
            "name": "vultr",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/hosting-providers/get", json={"provider_id": 1}
        )

        assert resp.status_code == 200
        assert resp.json()["name"] == "vultr"
        mock_instance.get_hosting_provider.assert_called_once_with(1)

    def test_missing_provider_id(self, client_as_member):
        resp = client_as_member.post("/api/v1/hosting-providers/get", json={})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/v1/hosting-providers/delete
# ---------------------------------------------------------------------------
class TestDeleteHostingProvider:
    @patch("ee.api.v1.hosting_providers.HostingProviderService")
    def test_success(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.delete_hosting_provider.return_value = {"message": "Deleted"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/hosting-providers/delete", params={"provider_id": 1}
        )

        assert resp.status_code == 200
        mock_instance.delete_hosting_provider.assert_called_once_with(1)

    def test_missing_provider_id(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/hosting-providers/delete")
        assert resp.status_code == 422
