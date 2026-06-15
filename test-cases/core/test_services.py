"""Tests for Services (ServiceConfig) API endpoints (Core edition).

Source: core/api/v1/services.py
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException

from core.internal.capabilities import is_ee_enabled

# main.py mounts either the core or EE services router under
# ``/api/v1/services`` depending on whether EE is enabled. Patches must target
# the active module so the service-class mock actually intercepts the call.
_MP_SVC = (
    "ee.api.v1.services.ModelProviderService"
    if is_ee_enabled()
    else "core.api.v1.services.ModelProviderService"
)


# ---------------------------------------------------------------------------
# POST /api/v1/services/upsert
# ---------------------------------------------------------------------------
class TestUpsertService:
    @patch("ee.api.v1.services.ServiceConfigService")
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
        mock_instance.upsert_service.assert_called_once_with(
            service_provider_id=5,
            model_provider_menu_id=None,
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

    @patch("ee.api.v1.services.ServiceConfigService")
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
            model_provider_menu_id=None,
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

    @patch("ee.api.v1.services.ServiceConfigService")
    def test_missing_provider_id(self, mock_service_cls, client_as_admin):
        """Neither service_provider_id nor model_provider_menu_id provided."""
        resp = client_as_admin.post(
            "/api/v1/services/upsert",
            json={
                "name": "My STT",
                "service_type": "stt",
                "config": {"language": "en"},
            },
        )
        assert resp.status_code == 400
        assert "model_provider_menu_id" in resp.json()["detail"]

    @patch("ee.api.v1.services.ServiceConfigService")
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

    @patch("ee.api.v1.services.ServiceConfigService")
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

    @patch("ee.api.v1.services.ServiceConfigService")
    def test_config_defaults_to_empty(self, mock_service_cls, client_as_admin):
        """Config is optional and defaults to {} when omitted."""
        mock_instance = MagicMock()
        mock_instance.upsert_service.return_value = {"id": 1}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/services/upsert",
            json={
                "service_provider_id": 5,
                "name": "My STT",
                "service_type": "stt",
            },
        )
        assert resp.status_code == 200

    @patch("ee.api.v1.services.ServiceConfigService")
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
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/services/list
# ---------------------------------------------------------------------------
class TestListServices:
    @patch("ee.api.v1.services.ServiceConfigService")
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

    @patch("ee.api.v1.services.ServiceConfigService")
    def test_filter_by_service_type(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_all_services.return_value = [{"id": 1, "service_type": "stt"}]
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/services/list", params={"service_type": "stt"}
        )

        assert resp.status_code == 200
        mock_instance.get_all_services.assert_called_once_with(service_type="stt")

    @patch("ee.api.v1.services.ServiceConfigService")
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
    @patch("ee.api.v1.services.ServiceConfigService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_service.return_value = {"id": 3, "name": "My LLM"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/services/get", params={"service_id": 3})

        assert resp.status_code == 200
        assert resp.json()["id"] == 3
        mock_instance.get_service.assert_called_once_with(3)

    @patch("ee.api.v1.services.ServiceConfigService")
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
    @patch("ee.api.v1.services.ServiceConfigService")
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

    @patch("ee.api.v1.services.ServiceConfigService")
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
    @patch("ee.api.v1.services.ServiceConfigService")
    def test_success(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.delete_service.return_value = {"message": "Deleted"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/services/delete", params={"service_id": 2}
        )

        assert resp.status_code == 200
        mock_instance.delete_service.assert_called_once_with(2)

    @patch("ee.api.v1.services.ServiceConfigService")
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


# ---------------------------------------------------------------------------
# POST /api/v1/services/upsert — new model_provider_menu_id path
# ---------------------------------------------------------------------------
class TestUpsertServiceNewPath:
    @patch("ee.api.v1.services.ServiceConfigService")
    def test_with_model_provider_menu_id(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.upsert_service.return_value = {"id": 1, "name": "OpenAI LLM"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/services/upsert",
            json={
                "model_provider_menu_id": 1,
                "name": "OpenAI LLM",
                "service_type": "llm",
                "config": {},
                "api_key_id": 3,
            },
        )

        assert resp.status_code == 200
        mock_instance.upsert_service.assert_called_once_with(
            service_provider_id=None,
            model_provider_menu_id=1,
            name="OpenAI LLM",
            service_type="llm",
            config={},
            api_key_id=3,
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

    @patch("ee.api.v1.services.ServiceConfigService")
    def test_both_provider_ids(self, mock_service_cls, client_as_admin):
        """When both service_provider_id and model_provider_menu_id are provided, both are passed."""
        mock_instance = MagicMock()
        mock_instance.upsert_service.return_value = {"id": 1}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/services/upsert",
            json={
                "service_provider_id": 5,
                "model_provider_menu_id": 1,
                "name": "Dual",
                "service_type": "llm",
            },
        )

        assert resp.status_code == 200


# ===========================================================================
# Endpoints backed by ModelProviderService (Model Providers page)
# ===========================================================================
#
# These cover the routes in ``core/api/v1/services.py`` that the new
# Model Providers page hits. They patch ``ModelProviderService`` at the
# import site in the core router module.


PROVIDER_ID = "33333333-3333-3333-3333-333333333333"
MODEL_ID = "44444444-4444-4444-4444-444444444444"


# ---------------------------------------------------------------------------
# POST /api/v1/services/facets
# ---------------------------------------------------------------------------

class TestGetServiceFacets:
    """Tests for POST /api/v1/services/facets"""

    @patch(_MP_SVC)
    def test_success_no_filters(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_service_facets.return_value = {
            "service_type": {"llm": 4, "stt": 2},
        }
        resp = client_as_member.post("/api/v1/services/facets", json={})
        assert resp.status_code == 200
        assert resp.json()["service_type"]["llm"] == 4
        mock_service_cls.return_value.get_service_facets.assert_called_once_with(None)

    @patch(_MP_SVC)
    def test_success_with_filters(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_service_facets.return_value = {"service_type": {"llm": 1}}
        resp = client_as_member.post(
            "/api/v1/services/facets",
            json={"filters": [{"field": "service_type", "operator": "eq", "value": "llm"}]},
        )
        assert resp.status_code == 200
        mock_service_cls.return_value.get_service_facets.assert_called_once_with(
            [{"field": "service_type", "operator": "eq", "value": "llm"}]
        )

    def test_invalid_filter_shape(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/services/facets",
            json={"filters": [{"value": "llm"}]},
        )
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/services/facets", json={})
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/services/filter-values
# ---------------------------------------------------------------------------

class TestGetServiceFilterValues:
    """Tests for GET /api/v1/services/filter-values"""

    @patch(_MP_SVC)
    def test_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_service_filter_values.return_value = {
            "values": ["openai", "anthropic"],
        }
        resp = client_as_member.get(
            "/api/v1/services/filter-values", params={"column_name": "provider_name"},
        )
        assert resp.status_code == 200
        assert resp.json()["values"] == ["openai", "anthropic"]
        mock_service_cls.return_value.get_service_filter_values.assert_called_once_with(
            "provider_name"
        )

    def test_missing_column_name(self, client_as_member):
        resp = client_as_member.get("/api/v1/services/filter-values")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/services/filter-values", params={"column_name": "provider_name"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/services/providers/{provider_id}/keys
# ---------------------------------------------------------------------------

class TestListProviderKeys:
    """Tests for POST /api/v1/services/providers/{provider_id}/keys"""

    @patch(_MP_SVC)
    def test_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.list_provider_keys.return_value = {
            "items": [{"id": "k1", "name": "primary"}], "total": 1,
        }
        resp = client_as_member.post(
            f"/api/v1/services/providers/{PROVIDER_ID}/keys",
            json={"search": "primary"},
        )
        assert resp.status_code == 200
        assert resp.json()["items"][0]["name"] == "primary"
        mock_service_cls.return_value.list_provider_keys.assert_called_once_with(
            PROVIDER_ID, {"search": "primary"},
        )

    @patch(_MP_SVC)
    def test_empty_body_default(self, mock_service_cls, client_as_member):
        """The body has ``default={}`` so callers can omit it."""
        mock_service_cls.return_value.list_provider_keys.return_value = {"items": [], "total": 0}
        resp = client_as_member.post(f"/api/v1/services/providers/{PROVIDER_ID}/keys")
        assert resp.status_code == 200
        mock_service_cls.return_value.list_provider_keys.assert_called_once_with(PROVIDER_ID, {})

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            f"/api/v1/services/providers/{PROVIDER_ID}/keys", json={},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/services/providers/{provider_id}/keys/filter-values
# ---------------------------------------------------------------------------

class TestGetProviderKeyFilterValues:
    """Tests for GET /api/v1/services/providers/{provider_id}/keys/filter-values"""

    @patch(_MP_SVC)
    def test_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_provider_key_filter_values.return_value = {
            "values": ["primary", "fallback"],
        }
        resp = client_as_member.get(
            f"/api/v1/services/providers/{PROVIDER_ID}/keys/filter-values",
            params={"column_name": "name", "service_type": "llm"},
        )
        assert resp.status_code == 200
        assert resp.json()["values"] == ["primary", "fallback"]
        mock_service_cls.return_value.get_provider_key_filter_values.assert_called_once_with(
            PROVIDER_ID, "name", "llm",
        )

    @patch(_MP_SVC)
    def test_service_type_optional(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_provider_key_filter_values.return_value = {"values": []}
        resp = client_as_member.get(
            f"/api/v1/services/providers/{PROVIDER_ID}/keys/filter-values",
            params={"column_name": "name"},
        )
        assert resp.status_code == 200
        mock_service_cls.return_value.get_provider_key_filter_values.assert_called_once_with(
            PROVIDER_ID, "name", None,
        )

    def test_missing_column_name(self, client_as_member):
        resp = client_as_member.get(
            f"/api/v1/services/providers/{PROVIDER_ID}/keys/filter-values",
        )
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            f"/api/v1/services/providers/{PROVIDER_ID}/keys/filter-values",
            params={"column_name": "name"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/services/providers/{provider_id}/models
# ---------------------------------------------------------------------------

class TestListProviderModels:
    """Tests for POST /api/v1/services/providers/{provider_id}/models"""

    @patch(_MP_SVC)
    def test_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.list_provider_models.return_value = {
            "items": [{"id": "m1", "name": "gpt-4o"}], "total": 1,
        }
        resp = client_as_member.post(
            f"/api/v1/services/providers/{PROVIDER_ID}/models",
            json={"search": "gpt"},
        )
        assert resp.status_code == 200
        assert resp.json()["items"][0]["name"] == "gpt-4o"
        mock_service_cls.return_value.list_provider_models.assert_called_once_with(
            PROVIDER_ID, {"search": "gpt"},
        )

    @patch(_MP_SVC)
    def test_empty_body_default(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.list_provider_models.return_value = {"items": [], "total": 0}
        resp = client_as_member.post(f"/api/v1/services/providers/{PROVIDER_ID}/models")
        assert resp.status_code == 200
        mock_service_cls.return_value.list_provider_models.assert_called_once_with(PROVIDER_ID, {})

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            f"/api/v1/services/providers/{PROVIDER_ID}/models", json={},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/services/providers/{provider_id}/models/filter-values
# ---------------------------------------------------------------------------

class TestGetProviderModelFilterValues:
    """Tests for GET /api/v1/services/providers/{provider_id}/models/filter-values"""

    @patch(_MP_SVC)
    def test_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_provider_model_filter_values.return_value = {
            "values": ["gpt-4o", "gpt-4o-mini"],
        }
        resp = client_as_member.get(
            f"/api/v1/services/providers/{PROVIDER_ID}/models/filter-values",
            params={"column_name": "name", "service_type": "llm"},
        )
        assert resp.status_code == 200
        mock_service_cls.return_value.get_provider_model_filter_values.assert_called_once_with(
            PROVIDER_ID, "name", "llm",
        )

    @patch(_MP_SVC)
    def test_service_type_optional(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_provider_model_filter_values.return_value = {"values": []}
        resp = client_as_member.get(
            f"/api/v1/services/providers/{PROVIDER_ID}/models/filter-values",
            params={"column_name": "name"},
        )
        assert resp.status_code == 200
        mock_service_cls.return_value.get_provider_model_filter_values.assert_called_once_with(
            PROVIDER_ID, "name", None,
        )

    def test_missing_column_name(self, client_as_member):
        resp = client_as_member.get(
            f"/api/v1/services/providers/{PROVIDER_ID}/models/filter-values",
        )
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            f"/api/v1/services/providers/{PROVIDER_ID}/models/filter-values",
            params={"column_name": "name"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/services/providers/{provider_id}/models/create
# Admin-gated write to the global models catalog.
# ---------------------------------------------------------------------------

class TestCreateProviderModel:
    """Tests for POST /api/v1/services/providers/{provider_id}/models/create"""

    @patch(_MP_SVC)
    def test_success_as_admin(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.create_provider_model.return_value = {
            "id": MODEL_ID, "name": "gpt-4o",
        }
        body = {"name": "gpt-4o", "service_type": "llm"}
        resp = client_as_admin.post(
            f"/api/v1/services/providers/{PROVIDER_ID}/models/create", json=body,
        )
        assert resp.status_code == 201
        assert resp.json()["id"] == MODEL_ID
        mock_service_cls.return_value.create_provider_model.assert_called_once_with(
            PROVIDER_ID, body,
        )

    @patch(_MP_SVC)
    def test_conflict_propagates(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.create_provider_model.side_effect = HTTPException(
            status_code=409, detail="Model name already exists for this provider",
        )
        resp = client_as_admin.post(
            f"/api/v1/services/providers/{PROVIDER_ID}/models/create",
            json={"name": "duplicate"},
        )
        assert resp.status_code == 409

    def test_missing_body(self, client_as_admin):
        resp = client_as_admin.post(
            f"/api/v1/services/providers/{PROVIDER_ID}/models/create",
        )
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            f"/api/v1/services/providers/{PROVIDER_ID}/models/create",
            json={"name": "x"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# PATCH /api/v1/services/providers/{provider_id}/models/{model_id}
# ---------------------------------------------------------------------------

class TestUpdateProviderModel:
    """Tests for PATCH /api/v1/services/providers/{provider_id}/models/{model_id}"""

    @patch(_MP_SVC)
    def test_success_as_admin(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.update_provider_model.return_value = {
            "id": MODEL_ID, "name": "gpt-4o-2",
        }
        resp = client_as_admin.patch(
            f"/api/v1/services/providers/{PROVIDER_ID}/models/{MODEL_ID}",
            json={"name": "gpt-4o-2"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "gpt-4o-2"
        mock_service_cls.return_value.update_provider_model.assert_called_once_with(
            PROVIDER_ID, MODEL_ID, {"name": "gpt-4o-2"},
        )

    @patch(_MP_SVC)
    def test_not_found(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.update_provider_model.side_effect = HTTPException(
            status_code=404, detail="Model not found",
        )
        resp = client_as_admin.patch(
            f"/api/v1/services/providers/{PROVIDER_ID}/models/{MODEL_ID}",
            json={"name": "x"},
        )
        assert resp.status_code == 404

    def test_missing_body(self, client_as_admin):
        resp = client_as_admin.patch(
            f"/api/v1/services/providers/{PROVIDER_ID}/models/{MODEL_ID}",
        )
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.patch(
            f"/api/v1/services/providers/{PROVIDER_ID}/models/{MODEL_ID}",
            json={"name": "x"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# DELETE /api/v1/services/providers/{provider_id}/models/{model_id}
# ---------------------------------------------------------------------------

class TestDeleteProviderModel:
    """Tests for DELETE /api/v1/services/providers/{provider_id}/models/{model_id}"""

    @patch(_MP_SVC)
    def test_success_as_admin(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.delete_provider_model.return_value = {"message": "Deleted"}
        resp = client_as_admin.delete(
            f"/api/v1/services/providers/{PROVIDER_ID}/models/{MODEL_ID}",
        )
        assert resp.status_code == 200
        mock_service_cls.return_value.delete_provider_model.assert_called_once_with(
            PROVIDER_ID, MODEL_ID,
        )

    @patch(_MP_SVC)
    def test_in_use_conflict(self, mock_service_cls, client_as_admin):
        """A model referenced by agent_configs across orgs must not be removable."""
        mock_service_cls.return_value.delete_provider_model.side_effect = HTTPException(
            status_code=409, detail="Model is in use by agents",
        )
        resp = client_as_admin.delete(
            f"/api/v1/services/providers/{PROVIDER_ID}/models/{MODEL_ID}",
        )
        assert resp.status_code == 409

    @patch(_MP_SVC)
    def test_not_found(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.delete_provider_model.side_effect = HTTPException(
            status_code=404, detail="Model not found",
        )
        resp = client_as_admin.delete(
            f"/api/v1/services/providers/{PROVIDER_ID}/models/{MODEL_ID}",
        )
        assert resp.status_code == 404

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete(
            f"/api/v1/services/providers/{PROVIDER_ID}/models/{MODEL_ID}",
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/services/tts/languages
# ---------------------------------------------------------------------------

class TestListTtsLanguages:
    """Tests for GET /api/v1/services/tts/languages"""

    @patch(_MP_SVC)
    def test_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.list_tts_languages.return_value = [
            {"name": "English"}, {"name": "Spanish"},
        ]
        resp = client_as_member.get("/api/v1/services/tts/languages")
        assert resp.status_code == 200
        assert len(resp.json()) == 2
        mock_service_cls.return_value.list_tts_languages.assert_called_once_with()

    @patch(_MP_SVC)
    def test_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.list_tts_languages.return_value = []
        resp = client_as_member.get("/api/v1/services/tts/languages")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/services/tts/languages")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/services/tts/providers
# ---------------------------------------------------------------------------

class TestListTtsProviders:
    """Tests for GET /api/v1/services/tts/providers"""

    @patch(_MP_SVC)
    def test_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.list_tts_providers.return_value = [
            {"id": "p1", "name": "elevenlabs"},
        ]
        resp = client_as_member.get(
            "/api/v1/services/tts/providers", params={"language": "English"},
        )
        assert resp.status_code == 200
        mock_service_cls.return_value.list_tts_providers.assert_called_once_with("English")

    def test_missing_language(self, client_as_member):
        resp = client_as_member.get("/api/v1/services/tts/providers")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/services/tts/providers", params={"language": "English"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/services/tts/voices
# ---------------------------------------------------------------------------

class TestListTtsVoices:
    """Tests for GET /api/v1/services/tts/voices"""

    @patch(_MP_SVC)
    def test_success_with_model_id(self, mock_service_cls, client_as_member):
        """``model_id`` is an optional core-only query param; the EE router
        accepts but does not forward it. Either way the call must reach the
        service with the provider_id + language pair."""
        mock_service_cls.return_value.list_tts_voices.return_value = [
            {"id": "v1", "name": "Rachel"},
        ]
        resp = client_as_member.get(
            "/api/v1/services/tts/voices",
            params={
                "provider_id": PROVIDER_ID,
                "language": "English",
                "model_id": MODEL_ID,
            },
        )
        assert resp.status_code == 200
        assert resp.json()[0]["name"] == "Rachel"
        args, _ = mock_service_cls.return_value.list_tts_voices.call_args
        assert args[0] == PROVIDER_ID
        assert args[1] == "English"

    @patch(_MP_SVC)
    def test_success_without_model_id(self, mock_service_cls, client_as_member):
        """``model_id`` is optional in core (and absent in EE)."""
        mock_service_cls.return_value.list_tts_voices.return_value = []
        resp = client_as_member.get(
            "/api/v1/services/tts/voices",
            params={"provider_id": PROVIDER_ID, "language": "English"},
        )
        assert resp.status_code == 200
        args, _ = mock_service_cls.return_value.list_tts_voices.call_args
        assert args[0] == PROVIDER_ID
        assert args[1] == "English"

    def test_missing_provider_id(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/services/tts/voices", params={"language": "English"},
        )
        assert resp.status_code == 422

    def test_missing_language(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/services/tts/voices", params={"provider_id": PROVIDER_ID},
        )
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/services/tts/voices",
            params={"provider_id": PROVIDER_ID, "language": "English"},
        )
        assert resp.status_code in (401, 403)
