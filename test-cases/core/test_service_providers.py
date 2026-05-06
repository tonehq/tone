"""Tests for Service Providers API endpoints (Core edition).

Source: core/api/v1/service_providers.py
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# POST /api/v1/service-providers/upsert
# ---------------------------------------------------------------------------
class TestUpsertServiceProvider:
    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_success(self, mock_service_cls, client_as_admin):
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

    @patch("ee.api.v1.service_providers.ServiceProviderService")
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

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_missing_name(self, mock_service_cls, client_as_admin):
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

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_missing_display_name(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/service-providers/upsert",
            json={
                "name": "openai",
                "provider_type": "llm",
                "auth_type": "api_key",
            },
        )
        assert resp.status_code == 400

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_missing_provider_type(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/service-providers/upsert",
            json={
                "name": "openai",
                "display_name": "OpenAI",
                "auth_type": "api_key",
            },
        )
        assert resp.status_code == 400

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_missing_auth_type(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/service-providers/upsert",
            json={
                "name": "openai",
                "display_name": "OpenAI",
                "provider_type": "llm",
            },
        )
        assert resp.status_code == 400

    @patch("ee.api.v1.service_providers.ServiceProviderService")
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


# ---------------------------------------------------------------------------
# POST /api/v1/service-providers/list
# ---------------------------------------------------------------------------
class TestListServiceProviders:
    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_success(self, mock_service_cls, client_as_member, mock_db):
        mock_instance = MagicMock()
        mock_instance.get_all_service_providers.return_value = [
            {"id": 1, "name": "openai", "provider_type": "llm"},
            {"id": 2, "name": "deepgram", "provider_type": "stt"},
        ]
        mock_service_cls.return_value = mock_instance

        # Mock the Voice query for TTS filtering
        mock_db.query.return_value.filter.return_value.distinct.return_value.all.return_value = []

        resp = client_as_member.post("/api/v1/service-providers/list", json={})

        assert resp.status_code == 200
        mock_instance.get_all_service_providers.assert_called_once_with(
            provider_type=None
        )

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_filter_by_provider_type(self, mock_service_cls, client_as_member, mock_db):
        mock_instance = MagicMock()
        mock_instance.get_all_service_providers.return_value = [
            {"id": 1, "name": "openai", "provider_type": "llm"},
        ]
        mock_service_cls.return_value = mock_instance
        mock_db.query.return_value.filter.return_value.distinct.return_value.all.return_value = []

        resp = client_as_member.post(
            "/api/v1/service-providers/list", json={"provider_type": "llm"}
        )

        assert resp.status_code == 200
        mock_instance.get_all_service_providers.assert_called_once_with(
            provider_type="llm"
        )

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_tts_provider_filtered_without_voices(
        self, mock_service_cls, client_as_member, mock_db
    ):
        """TTS providers without voices should be excluded from the response."""
        mock_instance = MagicMock()
        mock_instance.get_all_service_providers.return_value = [
            {"id": 1, "name": "elevenlabs", "provider_type": "tts"},
        ]
        mock_service_cls.return_value = mock_instance

        # No voices in DB
        mock_db.query.return_value.filter.return_value.distinct.return_value.all.return_value = []

        resp = client_as_member.post("/api/v1/service-providers/list", json={})

        assert resp.status_code == 200
        # Provider id=1 is in ALLOWED_PROVIDER_IDS but is TTS with no voices
        assert len(resp.json()) == 0

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_tts_provider_included_with_voices(
        self, mock_service_cls, client_as_member, mock_db
    ):
        """TTS providers with voices should be included in the response."""
        mock_instance = MagicMock()
        mock_instance.get_all_service_providers.return_value = [
            {"id": 1, "name": "elevenlabs", "provider_type": "tts"},
        ]
        mock_service_cls.return_value = mock_instance

        # Voice exists for provider_id 1
        mock_db.query.return_value.filter.return_value.distinct.return_value.all.return_value = [
            (1,)
        ]

        resp = client_as_member.post("/api/v1/service-providers/list", json={})

        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_provider_not_in_allowed_list(
        self, mock_service_cls, client_as_member, mock_db
    ):
        """Providers not in ALLOWED_PROVIDER_IDS are excluded."""
        mock_instance = MagicMock()
        mock_instance.get_all_service_providers.return_value = [
            {"id": 9999, "name": "unknown", "provider_type": "llm"},
        ]
        mock_service_cls.return_value = mock_instance
        mock_db.query.return_value.filter.return_value.distinct.return_value.all.return_value = []

        resp = client_as_member.post("/api/v1/service-providers/list", json={})

        assert resp.status_code == 200
        assert len(resp.json()) == 0

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_empty_list(self, mock_service_cls, client_as_member, mock_db):
        mock_instance = MagicMock()
        mock_instance.get_all_service_providers.return_value = []
        mock_service_cls.return_value = mock_instance
        mock_db.query.return_value.filter.return_value.distinct.return_value.all.return_value = []

        resp = client_as_member.post("/api/v1/service-providers/list", json={})

        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# POST /api/v1/service-providers/get
# ---------------------------------------------------------------------------
class TestGetServiceProvider:
    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_service_provider.return_value = {
            "id": 1,
            "name": "openai",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/service-providers/get", json={"provider_id": 1}
        )

        assert resp.status_code == 200
        assert resp.json()["name"] == "openai"
        mock_instance.get_service_provider.assert_called_once_with(1)

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_service_provider.side_effect = HTTPException(
            status_code=404, detail="Not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/service-providers/get", json={"provider_id": 999}
        )
        assert resp.status_code == 404

    def test_missing_provider_id(self, client_as_member):
        resp = client_as_member.post("/api/v1/service-providers/get", json={})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/v1/service-providers/delete
# ---------------------------------------------------------------------------
class TestDeleteServiceProvider:
    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_success(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.delete_service_provider.return_value = {"message": "Deleted"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/service-providers/delete", params={"provider_id": 5}
        )

        assert resp.status_code == 200
        mock_instance.delete_service_provider.assert_called_once_with(5)

    @patch("ee.api.v1.service_providers.ServiceProviderService")
    def test_not_found(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.delete_service_provider.side_effect = HTTPException(
            status_code=404, detail="Not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/service-providers/delete", params={"provider_id": 999}
        )
        assert resp.status_code == 404

    @patch("ee.api.v1.service_providers.ServiceProviderService")
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
