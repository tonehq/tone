"""Tests for Services API endpoints (EE edition).

Source: ee/api/v1/services.py
Integration tests — real DB, real endpoints, no mocks.

The legacy ServiceConfig endpoints (/upsert, /list, /get, /default, /delete)
have been removed and replaced by /api/v1/accounts/. Tests for those endpoints
are class-level skipped below. The ModelProviderService-backed endpoints
further down (/facets, /filter-values, /providers/{id}/keys, /models, /tts/*)
are the current live surface and are covered.
"""

import pytest
import uuid

_OBSOLETE = pytest.mark.skip(
    reason="legacy ServiceConfig endpoints removed, replaced by accounts",
)


# ─── Helpers ───

def _unique_name(prefix="Service"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_service_provider(client, provider_type="llm"):
    """Create a service provider via the API and return the response JSON."""
    data = {
        "name": f"test-provider-{uuid.uuid4().hex[:8]}",
        "display_name": f"Test Provider {uuid.uuid4().hex[:6]}",
        "provider_type": provider_type,
        "auth_type": "api_key",
    }
    resp = client.post("/api/v1/service-providers/upsert", json=data)
    assert resp.status_code == 200
    return resp.json()


def _create_service(client, service_type="llm", is_default=False, **extra):
    """Create a service via the API and return the response JSON."""
    if "service_provider_id" not in extra:
        provider = _create_service_provider(client, provider_type=service_type)
        extra["service_provider_id"] = provider["id"]
    data = {
        "name": extra.pop("name", _unique_name()),
        "service_type": service_type,
        "config": extra.pop("config", {"model": "test-model"}),
        "is_default": is_default,
        "status": "active",
        **extra,
    }
    resp = client.post("/api/v1/services/upsert", json=data)
    assert resp.status_code == 200
    return resp.json()


# ─── POST /api/v1/services/upsert ───

@_OBSOLETE
class TestUpsertService:
    """Tests for POST /api/v1/services/upsert"""

    def test_upsert_service_missing_service_provider_id(self, client_as_admin):
        response = client_as_admin.post("/api/v1/services/upsert", json={
            "name": "Test", "service_type": "llm", "config": {}
        })
        assert response.status_code == 400

    def test_upsert_service_missing_name(self, client_as_admin):
        response = client_as_admin.post("/api/v1/services/upsert", json={
            "service_provider_id": 1, "service_type": "llm", "config": {}
        })
        assert response.status_code == 400

    def test_upsert_service_missing_service_type(self, client_as_admin):
        response = client_as_admin.post("/api/v1/services/upsert", json={
            "service_provider_id": 1, "name": "Test", "config": {}
        })
        assert response.status_code == 400

    def test_upsert_service_without_config_uses_default(self, client_as_admin):
        """config is optional — defaults to {} when omitted."""
        provider = _create_service_provider(client_as_admin, provider_type="llm")
        response = client_as_admin.post("/api/v1/services/upsert", json={
            "service_provider_id": provider["id"], "name": _unique_name(), "service_type": "llm"
        })
        assert response.status_code == 200

    def test_upsert_service_empty_body(self, client_as_admin):
        response = client_as_admin.post("/api/v1/services/upsert", json={})
        assert response.status_code == 400

    def test_upsert_service_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/services/upsert", json={
            "service_provider_id": 1, "name": "T", "service_type": "llm", "config": {}
        })
        assert response.status_code in (401, 403)

    def test_create_llm_service_anthropic(self, client_as_admin):
        """Postman: Create LLM Service (Anthropic)."""
        provider = _create_service_provider(client_as_admin, provider_type="llm")
        response = client_as_admin.post("/api/v1/services/upsert", json={
            "service_provider_id": provider["id"],
            "name": _unique_name("Anthropic-LLM"),
            "service_type": "llm",
            "config": {"model": "claude-3-opus", "max_tokens": 4096},
            "status": "active",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["service_type"] == "llm"

    def test_create_stt_service_google(self, client_as_admin):
        """Postman: Create STT Service (Google)."""
        provider = _create_service_provider(client_as_admin, provider_type="stt")
        response = client_as_admin.post("/api/v1/services/upsert", json={
            "service_provider_id": provider["id"],
            "name": _unique_name("Google-STT"),
            "service_type": "stt",
            "config": {"model": "latest_long", "language_code": "en-US"},
            "status": "active",
        })
        assert response.status_code == 200

    def test_create_tts_service_openai(self, client_as_admin):
        """Postman: Create TTS Service (OpenAI)."""
        provider = _create_service_provider(client_as_admin, provider_type="tts")
        response = client_as_admin.post("/api/v1/services/upsert", json={
            "service_provider_id": provider["id"],
            "name": _unique_name("OpenAI-TTS"),
            "service_type": "tts",
            "config": {"voice": "alloy", "model": "tts-1"},
            "status": "active",
        })
        assert response.status_code == 200

    def test_create_tts_service_cartesia(self, client_as_admin):
        """Postman: Create TTS Service (Cartesia)."""
        provider = _create_service_provider(client_as_admin, provider_type="tts")
        response = client_as_admin.post("/api/v1/services/upsert", json={
            "service_provider_id": provider["id"],
            "name": _unique_name("Cartesia-TTS"),
            "service_type": "tts",
            "config": {"voice_id": "voice_abc", "model_id": "sonic-english"},
            "status": "active",
        })
        assert response.status_code == 200

    def test_update_service_via_uuid(self, client_as_admin):
        """Postman: Update Service via uuid."""
        svc = _create_service(client_as_admin, service_type="llm")
        response = client_as_admin.post("/api/v1/services/upsert", json={
            "uuid": svc["uuid"],
            "service_provider_id": svc["service_provider_id"],
            "name": "Updated LLM Service",
            "service_type": "llm",
            "config": {"model": "gpt-4-turbo", "temperature": 0.5},
            "status": "active",
        })
        assert response.status_code == 200
        assert response.json()["name"] == "Updated LLM Service"

    def test_upsert_service_provider_not_found(self, client_as_admin):
        """Postman: Service Provider Not Found (404)."""
        response = client_as_admin.post("/api/v1/services/upsert", json={
            "service_provider_id": 999999,
            "name": "Test",
            "service_type": "llm",
            "config": {"model": "test"},
        })
        assert response.status_code in (400, 404)


# ─── POST /api/v1/services/list ───

@_OBSOLETE
class TestGetAllServices:
    """Tests for POST /api/v1/services/list"""

    def test_get_all_services_returns_200(self, client_as_member):
        response = client_as_member.post("/api/v1/services/list", json={})
        assert response.status_code == 200

    def test_get_all_services_filter_by_type(self, client_as_member):
        response = client_as_member.post("/api/v1/services/list", json={"service_type": "llm"})
        assert response.status_code == 200

    def test_get_all_services_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/services/list", json={})
        assert response.status_code in (401, 403)

    def test_get_all_services_filter_by_stt(self, client_as_admin):
        """Postman: Filter by STT — only STT services returned."""
        _create_service(client_as_admin, service_type="stt")
        response = client_as_admin.post("/api/v1/services/list", json={"service_type": "stt"})
        assert response.status_code == 200
        for svc in response.json():
            assert svc["service_type"] == "stt"

    def test_get_all_services_filter_by_tts(self, client_as_admin):
        """Postman: Filter by TTS — only TTS services returned."""
        _create_service(client_as_admin, service_type="tts")
        response = client_as_admin.post("/api/v1/services/list", json={"service_type": "tts"})
        assert response.status_code == 200
        for svc in response.json():
            assert svc["service_type"] == "tts"

    def test_get_all_services_pagination(self, client_as_admin):
        """Test page/page_size body params."""
        response = client_as_admin.post("/api/v1/services/list", json={"page": 1, "page_size": 5})
        assert response.status_code == 200

    def test_get_all_services_invalid_page(self, client_as_admin):
        response = client_as_admin.post("/api/v1/services/list", json={"page": 0})
        assert response.status_code == 400


# ─── GET /api/v1/services/get ───

@_OBSOLETE
class TestGetService:
    """Tests for GET /api/v1/services/get"""

    def test_get_service_missing_id(self, client_as_member):
        response = client_as_member.get("/api/v1/services/get")
        assert response.status_code == 422

    def test_get_service_invalid_id(self, client_as_member):
        response = client_as_member.get("/api/v1/services/get?service_id=abc")
        assert response.status_code == 422

    def test_get_service_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/services/get?service_id=1")
        assert response.status_code in (401, 403)

    def test_get_service_not_found(self, client_as_member):
        response = client_as_member.get("/api/v1/services/get?service_id=999999")
        assert response.status_code == 404

    def test_get_service_success(self, client_as_admin):
        svc = _create_service(client_as_admin, service_type="llm")
        response = client_as_admin.get(f"/api/v1/services/get?service_id={svc['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == svc["id"]


# ─── GET /api/v1/services/default ───

@_OBSOLETE
class TestGetDefaultService:
    """Tests for GET /api/v1/services/default"""

    def test_get_default_service_missing_type(self, client_as_member):
        response = client_as_member.get("/api/v1/services/default")
        assert response.status_code == 422

    def test_get_default_service_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/services/default?service_type=llm")
        assert response.status_code in (401, 403)

    def test_get_default_stt_service(self, client_as_admin):
        _create_service(client_as_admin, service_type="stt", is_default=True)
        response = client_as_admin.get("/api/v1/services/default?service_type=stt")
        assert response.status_code == 200

    def test_get_default_tts_service(self, client_as_admin):
        _create_service(client_as_admin, service_type="tts", is_default=True)
        response = client_as_admin.get("/api/v1/services/default?service_type=tts")
        assert response.status_code == 200

    def test_no_default_found(self, client_as_admin):
        response = client_as_admin.get("/api/v1/services/default?service_type=nonexistent_type")
        assert response.status_code == 404


# ─── DELETE /api/v1/services/delete ───

@_OBSOLETE
class TestDeleteService:
    """Tests for DELETE /api/v1/services/delete

    Accepts either `uuid` or `service_id` query param. Returns 400 if neither provided.
    """

    def test_delete_service_no_params(self, client_as_admin):
        """Neither uuid nor service_id — returns 400."""
        response = client_as_admin.delete("/api/v1/services/delete")
        assert response.status_code == 400
        assert "uuid or service_id is required" in response.json()["detail"]

    def test_delete_service_by_id_success(self, client_as_admin):
        svc = _create_service(client_as_admin, service_type="llm")
        response = client_as_admin.delete(f"/api/v1/services/delete?service_id={svc['id']}")
        assert response.status_code == 200
        get_resp = client_as_admin.get(f"/api/v1/services/get?service_id={svc['id']}")
        assert get_resp.status_code == 404

    def test_delete_service_by_uuid_success(self, client_as_admin):
        svc = _create_service(client_as_admin, service_type="llm")
        response = client_as_admin.delete(f"/api/v1/services/delete?uuid={svc['uuid']}")
        assert response.status_code == 200

    def test_delete_service_by_id_not_found(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/services/delete?service_id=999999")
        assert response.status_code == 404

    def test_delete_service_by_uuid_not_found(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/services/delete?uuid=00000000-0000-0000-0000-000000000000")
        assert response.status_code in (404, 400)

    def test_delete_service_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/services/delete?service_id=1")
        assert response.status_code in (401, 403)


# ===========================================================================
# Endpoints backed by ModelProviderService (Model Providers page)
# ===========================================================================
#
# Integration coverage for the new Model Providers page endpoints in
# ``ee/api/v1/services.py``. The handlers delegate to ``ModelProviderService``;
# these tests confirm the wiring (auth, validation, path/query parameters,
# response shape) against the real DB.


import uuid as _uuid

# A UUID that almost certainly does not match any provider/model row — used
# wherever we want to confirm 404/empty handling without seeding new rows.
_MISSING_UUID = "00000000-0000-0000-0000-000000000000"


def _random_uuid() -> str:
    return str(_uuid.uuid4())


# ---------------------------------------------------------------------------
# POST /api/v1/services/facets
# ---------------------------------------------------------------------------

class TestGetServiceFacets:
    """Tests for POST /api/v1/services/facets"""

    def test_facets_no_filters(self, client_as_member):
        resp = client_as_member.post("/api/v1/services/facets", json={})
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)

    def test_facets_with_filters(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/services/facets",
            json={"filters": [{"field": "service_type", "operator": "eq", "value": "llm"}]},
        )
        assert resp.status_code == 200

    def test_facets_invalid_filter_shape(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/services/facets",
            json={"filters": [{"value": "llm"}]},
        )
        assert resp.status_code == 422

    def test_facets_as_admin(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/services/facets", json={})
        assert resp.status_code == 200

    def test_facets_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/services/facets", json={})
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/services/filter-values
# ---------------------------------------------------------------------------

class TestGetServiceFilterValues:
    """Tests for GET /api/v1/services/filter-values"""

    def test_filter_values_service_type(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/services/filter-values", params={"column_name": "service_type"},
        )
        assert resp.status_code == 200

    def test_filter_values_missing_column_name(self, client_as_member):
        resp = client_as_member.get("/api/v1/services/filter-values")
        assert resp.status_code == 422

    def test_filter_values_unknown_column(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/services/filter-values",
            params={"column_name": "definitely_not_a_real_column"},
        )
        # Whitelisted helper must either reject or return empty — never 500.
        assert resp.status_code in (200, 400)

    def test_filter_values_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/services/filter-values", params={"column_name": "service_type"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/services/providers/{provider_id}/keys
# ---------------------------------------------------------------------------

class TestListProviderKeys:
    """Tests for POST /api/v1/services/providers/{provider_id}/keys"""

    def test_list_provider_keys_default_body(self, client_as_member):
        resp = client_as_member.post(
            f"/api/v1/services/providers/{_MISSING_UUID}/keys",
        )
        # Service may return an empty payload or 404 for unknown provider.
        assert resp.status_code in (200, 404, 400)

    def test_list_provider_keys_with_body(self, client_as_member):
        resp = client_as_member.post(
            f"/api/v1/services/providers/{_MISSING_UUID}/keys",
            json={"search": "primary"},
        )
        assert resp.status_code in (200, 404, 400)

    def test_list_provider_keys_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            f"/api/v1/services/providers/{_MISSING_UUID}/keys", json={},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/services/providers/{provider_id}/keys/filter-values
# ---------------------------------------------------------------------------

class TestGetProviderKeyFilterValues:
    """Tests for GET /api/v1/services/providers/{provider_id}/keys/filter-values"""

    def test_success_minimal(self, client_as_member):
        resp = client_as_member.get(
            f"/api/v1/services/providers/{_MISSING_UUID}/keys/filter-values",
            params={"column_name": "name"},
        )
        assert resp.status_code in (200, 404, 400)

    def test_success_with_service_type(self, client_as_member):
        resp = client_as_member.get(
            f"/api/v1/services/providers/{_MISSING_UUID}/keys/filter-values",
            params={"column_name": "name", "service_type": "llm"},
        )
        assert resp.status_code in (200, 404, 400)

    def test_missing_column_name(self, client_as_member):
        resp = client_as_member.get(
            f"/api/v1/services/providers/{_MISSING_UUID}/keys/filter-values",
        )
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            f"/api/v1/services/providers/{_MISSING_UUID}/keys/filter-values",
            params={"column_name": "name"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/services/providers/{provider_id}/models
# ---------------------------------------------------------------------------

class TestListProviderModels:
    """Tests for POST /api/v1/services/providers/{provider_id}/models"""

    def test_list_provider_models_default(self, client_as_member):
        resp = client_as_member.post(
            f"/api/v1/services/providers/{_MISSING_UUID}/models",
        )
        assert resp.status_code in (200, 404, 400)

    def test_list_provider_models_with_body(self, client_as_member):
        resp = client_as_member.post(
            f"/api/v1/services/providers/{_MISSING_UUID}/models",
            json={"search": "gpt"},
        )
        assert resp.status_code in (200, 404, 400)

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            f"/api/v1/services/providers/{_MISSING_UUID}/models", json={},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/services/providers/{provider_id}/models/filter-values
# ---------------------------------------------------------------------------

class TestGetProviderModelFilterValues:
    """Tests for GET /api/v1/services/providers/{provider_id}/models/filter-values"""

    def test_success_minimal(self, client_as_member):
        resp = client_as_member.get(
            f"/api/v1/services/providers/{_MISSING_UUID}/models/filter-values",
            params={"column_name": "name"},
        )
        assert resp.status_code in (200, 404, 400)

    def test_success_with_service_type(self, client_as_member):
        resp = client_as_member.get(
            f"/api/v1/services/providers/{_MISSING_UUID}/models/filter-values",
            params={"column_name": "name", "service_type": "llm"},
        )
        assert resp.status_code in (200, 404, 400)

    def test_missing_column_name(self, client_as_member):
        resp = client_as_member.get(
            f"/api/v1/services/providers/{_MISSING_UUID}/models/filter-values",
        )
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            f"/api/v1/services/providers/{_MISSING_UUID}/models/filter-values",
            params={"column_name": "name"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/services/providers/{provider_id}/models/create  (admin-gated)
# ---------------------------------------------------------------------------

class TestCreateProviderModel:
    """Tests for POST /api/v1/services/providers/{provider_id}/models/create"""

    def test_member_cannot_create_admin_endpoint(self, client_as_member):
        """Writes to the global models catalog are admin-gated so a single
        org member can't rename/delete a row other orgs depend on."""
        resp = client_as_member.post(
            f"/api/v1/services/providers/{_MISSING_UUID}/models/create",
            json={"name": _random_uuid()},
        )
        # Either 403 (auth) or 404/400 (unknown provider) — never 201 for a member.
        assert resp.status_code != 201

    def test_create_with_unknown_provider_as_admin(self, client_as_admin):
        resp = client_as_admin.post(
            f"/api/v1/services/providers/{_MISSING_UUID}/models/create",
            json={"name": _random_uuid()},
        )
        assert resp.status_code in (201, 400, 404)

    def test_missing_body_as_admin(self, client_as_admin):
        resp = client_as_admin.post(
            f"/api/v1/services/providers/{_MISSING_UUID}/models/create",
        )
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            f"/api/v1/services/providers/{_MISSING_UUID}/models/create",
            json={"name": "x"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# PATCH /api/v1/services/providers/{provider_id}/models/{model_id}
# ---------------------------------------------------------------------------

class TestUpdateProviderModel:
    """Tests for PATCH /api/v1/services/providers/{provider_id}/models/{model_id}"""

    def test_member_cannot_update(self, client_as_member):
        resp = client_as_member.patch(
            f"/api/v1/services/providers/{_MISSING_UUID}/models/{_MISSING_UUID}",
            json={"name": "x"},
        )
        assert resp.status_code != 200

    def test_update_nonexistent_as_admin(self, client_as_admin):
        resp = client_as_admin.patch(
            f"/api/v1/services/providers/{_MISSING_UUID}/models/{_MISSING_UUID}",
            json={"name": "x"},
        )
        assert resp.status_code in (400, 404)

    def test_missing_body(self, client_as_admin):
        resp = client_as_admin.patch(
            f"/api/v1/services/providers/{_MISSING_UUID}/models/{_MISSING_UUID}",
        )
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.patch(
            f"/api/v1/services/providers/{_MISSING_UUID}/models/{_MISSING_UUID}",
            json={"name": "x"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# DELETE /api/v1/services/providers/{provider_id}/models/{model_id}
# ---------------------------------------------------------------------------

class TestDeleteProviderModel:
    """Tests for DELETE /api/v1/services/providers/{provider_id}/models/{model_id}"""

    def test_member_cannot_delete(self, client_as_member):
        resp = client_as_member.delete(
            f"/api/v1/services/providers/{_MISSING_UUID}/models/{_MISSING_UUID}",
        )
        assert resp.status_code != 200

    def test_delete_nonexistent_as_admin(self, client_as_admin):
        resp = client_as_admin.delete(
            f"/api/v1/services/providers/{_MISSING_UUID}/models/{_MISSING_UUID}",
        )
        assert resp.status_code in (400, 404)

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete(
            f"/api/v1/services/providers/{_MISSING_UUID}/models/{_MISSING_UUID}",
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/services/tts/languages
# ---------------------------------------------------------------------------

class TestListTtsLanguages:
    """Tests for GET /api/v1/services/tts/languages"""

    def test_list_tts_languages_success(self, client_as_member):
        resp = client_as_member.get("/api/v1/services/tts/languages")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_as_admin(self, client_as_admin):
        resp = client_as_admin.get("/api/v1/services/tts/languages")
        assert resp.status_code == 200

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/services/tts/languages")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/services/tts/providers
# ---------------------------------------------------------------------------

class TestListTtsProviders:
    """Tests for GET /api/v1/services/tts/providers"""

    def test_list_tts_providers_with_language(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/services/tts/providers", params={"language": "English"},
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_tts_providers_unknown_language(self, client_as_member):
        """An unknown language should yield an empty list, not an error."""
        resp = client_as_member.get(
            "/api/v1/services/tts/providers", params={"language": "Klingon"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

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

    def test_list_tts_voices_minimal(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/services/tts/voices",
            params={"provider_id": _MISSING_UUID, "language": "English"},
        )
        # Unknown provider should return empty (not 500).
        assert resp.status_code in (200, 400, 404)

    def test_missing_provider_id(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/services/tts/voices", params={"language": "English"},
        )
        assert resp.status_code == 422

    def test_missing_language(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/services/tts/voices", params={"provider_id": _MISSING_UUID},
        )
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/services/tts/voices",
            params={"provider_id": _MISSING_UUID, "language": "English"},
        )
        assert resp.status_code in (401, 403)
