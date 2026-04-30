"""Tests for Services (ServiceConfig) API endpoints (Core edition).

Source: core/api/v1/services.py
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# POST /api/v1/services/upsert
# ---------------------------------------------------------------------------
class TestUpsertService:
    @patch("core.api.v1.services.ServiceConfigService")
    def test_success(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_service.return_value = {"id": 1, "name": "My STT"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/services/upsert",
            json={
                "service_provider_id": 5,
                "name": "My STT",
                "service_type": "stt",
                "config": {"language": "en"},
            },
        )

        assert resp.status_code == 200
        assert resp.json()["name"] == "My STT"
        mock_service_cls.assert_called_once_with(ANY, user_id=ANY)
        mock_instance.upsert_service.assert_called_once_with(
            service_provider_id=5,
            name="My STT",
            service_type="stt",
            config={"language": "en"},
            api_key_id=None,
            description=None,
            is_default=False,
            is_public=False,
            tags=None,
            service_uuid=None,
            service_status=None,
            api_key_value=None,
            api_key_name=None,
            additional_credentials=None,
        )

    @patch("core.api.v1.services.ServiceConfigService")
    def test_with_optional_fields(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_service.return_value = {"id": 1}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/services/upsert",
            json={
                "service_provider_id": 5,
                "name": "My STT",
                "service_type": "stt",
                "config": {"language": "en"},
                "api_key_id": 10,
                "description": "Primary STT service",
                "is_default": True,
                "is_public": True,
                "tags": ["production"],
                "uuid": "abc-123",
                "status": "active",
            },
        )

        assert resp.status_code == 200
        mock_instance.upsert_service.assert_called_once_with(
            service_provider_id=5,
            name="My STT",
            service_type="stt",
            config={"language": "en"},
            api_key_id=10,
            description="Primary STT service",
            is_default=True,
            is_public=True,
            tags=["production"],
            service_uuid="abc-123",
            service_status="active",
            api_key_value=None,
            api_key_name=None,
            additional_credentials=None,
        )

    @patch("core.api.v1.services.ServiceConfigService")
    def test_missing_service_provider_id(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/services/upsert",
            json={
                "name": "My STT",
                "service_type": "stt",
                "config": {"language": "en"},
            },
        )
        assert resp.status_code == 400
        assert "service_provider_id" in resp.json()["detail"]

    @patch("core.api.v1.services.ServiceConfigService")
    def test_missing_name(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/services/upsert",
            json={
                "service_provider_id": 5,
                "service_type": "stt",
                "config": {"language": "en"},
            },
        )
        assert resp.status_code == 400

    @patch("core.api.v1.services.ServiceConfigService")
    def test_missing_service_type(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/services/upsert",
            json={
                "service_provider_id": 5,
                "name": "My STT",
                "config": {"language": "en"},
            },
        )
        assert resp.status_code == 400

    @patch("core.api.v1.services.ServiceConfigService")
    def test_missing_config(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/services/upsert",
            json={
                "service_provider_id": 5,
                "name": "My STT",
                "service_type": "stt",
            },
        )
        assert resp.status_code == 400

    @patch("core.api.v1.services.ServiceConfigService")
    def test_service_error(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_service.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/services/upsert",
            json={
                "service_provider_id": 5,
                "name": "My STT",
                "service_type": "stt",
                "config": {"language": "en"},
            },
        )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/v1/services/list
# ---------------------------------------------------------------------------
class TestListServices:
    @patch("core.api.v1.services.ServiceConfigService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_services.return_value = [
            {"id": 1, "name": "STT A"},
            {"id": 2, "name": "TTS B"},
        ]
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/services/list")

        assert resp.status_code == 200
        assert len(resp.json()) == 2
        mock_instance.get_all_services.assert_called_once_with(service_type=None)

    @patch("core.api.v1.services.ServiceConfigService")
    def test_filter_by_service_type(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_services.return_value = [{"id": 1, "service_type": "stt"}]
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/services/list", params={"service_type": "stt"}
        )

        assert resp.status_code == 200
        mock_instance.get_all_services.assert_called_once_with(service_type="stt")

    @patch("core.api.v1.services.ServiceConfigService")
    def test_empty_list(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_services.return_value = []
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/services/list")

        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /api/v1/services/get
# ---------------------------------------------------------------------------
class TestGetService:
    @patch("core.api.v1.services.ServiceConfigService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_service.return_value = {"id": 3, "name": "My LLM"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/services/get", params={"service_id": 3})

        assert resp.status_code == 200
        assert resp.json()["id"] == 3
        mock_instance.get_service.assert_called_once_with(3)

    @patch("core.api.v1.services.ServiceConfigService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_service.side_effect = HTTPException(
            status_code=404, detail="Not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/services/get", params={"service_id": 999})
        assert resp.status_code == 404

    def test_missing_service_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/services/get")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/services/default
# ---------------------------------------------------------------------------
class TestGetDefaultService:
    @patch("core.api.v1.services.ServiceConfigService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_default_service.return_value = {
            "id": 1,
            "is_default": True,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/services/default", params={"service_type": "stt"}
        )

        assert resp.status_code == 200
        mock_instance.get_default_service.assert_called_once_with(service_type="stt")

    @patch("core.api.v1.services.ServiceConfigService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_default_service.side_effect = HTTPException(
            status_code=404, detail="No default service"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/services/default", params={"service_type": "stt"}
        )
        assert resp.status_code == 404

    def test_missing_service_type(self, client_as_member):
        resp = client_as_member.get("/api/v1/services/default")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/v1/services/delete
# ---------------------------------------------------------------------------
class TestDeleteService:
    @patch("core.api.v1.services.ServiceConfigService")
    def test_success(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.delete_service.return_value = {"message": "Deleted"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/services/delete", params={"service_id": 2}
        )

        assert resp.status_code == 200
        mock_instance.delete_service.assert_called_once_with(2)

    @patch("core.api.v1.services.ServiceConfigService")
    def test_not_found(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.delete_service.side_effect = HTTPException(
            status_code=404, detail="Not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/services/delete", params={"service_id": 999}
        )
        assert resp.status_code == 404

    def test_missing_service_id(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/services/delete")
        assert resp.status_code == 422
