"""Tests for Model API endpoints (EE edition).

Source: ee/api/v1/models.py
Postman: postman_collection/models.postman_collection.json
Integration tests -- real DB, real endpoints, no mocks.
"""

import pytest
import uuid


# --- Helpers ---

def _unique_name(prefix="Model"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_service_provider(client, provider_type="llm"):
    """Create a service provider and return JSON."""
    data = {
        "name": f"test-provider-{uuid.uuid4().hex[:8]}",
        "display_name": f"Test Provider {uuid.uuid4().hex[:6]}",
        "provider_type": provider_type,
        "auth_type": "api_key",
    }
    resp = client.post("/api/v1/service-providers/upsert", json=data)
    assert resp.status_code == 200
    return resp.json()


def _create_model(client, service_provider_id, name=None, service_type="llm", **extra):
    """Create a model via upsert and return JSON."""
    data = {
        "service_provider_id": service_provider_id,
        "name": name or _unique_name(),
        "service_type": service_type,
        "status": "active",
        **extra,
    }
    resp = client.post("/api/v1/model/upsert_model", json=data)
    assert resp.status_code == 200
    return resp.json()


# --- POST /api/v1/model/get_models_by_provider ---

class TestGetModelsByProvider:
    """Tests for POST /api/v1/model/get_models_by_provider"""

    def test_success_with_pagination(self, client_as_admin):
        """Postman: Get Models By Provider - Success (200)."""
        provider = _create_service_provider(client_as_admin, provider_type="llm")
        _create_model(client_as_admin, provider["id"], name="gpt-4o", service_type="llm")
        response = client_as_admin.post("/api/v1/model/get_models_by_provider", json={
            "service_provider_id": provider["id"],
            "name": "gpt",
            "status": "active",
            "service_type": "llm",
            "sort": "-created_at",
            "page": 1,
            "page_size": 10,
        })
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 10

    def test_missing_provider_id(self, client_as_member):
        """Postman: Get Models By Provider - Missing ID (400)."""
        response = client_as_member.post("/api/v1/model/get_models_by_provider", json={})
        assert response.status_code == 400
        assert "service_provider_id is required" in response.json()["detail"]

    def test_invalid_provider_id(self, client_as_member):
        """service_provider_id must be an integer."""
        response = client_as_member.post("/api/v1/model/get_models_by_provider", json={
            "service_provider_id": "abc",
        })
        assert response.status_code == 400
        assert "integer" in response.json()["detail"].lower()

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/model/get_models_by_provider", json={
            "service_provider_id": 1,
        })
        assert response.status_code in (401, 403)

    def test_filter_by_service_type(self, client_as_admin):
        provider = _create_service_provider(client_as_admin, provider_type="llm")
        _create_model(client_as_admin, provider["id"], name="gpt-4", service_type="llm")
        response = client_as_admin.post("/api/v1/model/get_models_by_provider", json={
            "service_provider_id": provider["id"],
            "service_type": "llm",
        })
        assert response.status_code == 200

    def test_filter_by_name(self, client_as_admin):
        provider = _create_service_provider(client_as_admin, provider_type="stt")
        _create_model(client_as_admin, provider["id"], name="nova-2", service_type="stt")
        response = client_as_admin.post("/api/v1/model/get_models_by_provider", json={
            "service_provider_id": provider["id"],
            "name": "nova",
        })
        assert response.status_code == 200

    def test_sort_ascending(self, client_as_admin):
        provider = _create_service_provider(client_as_admin, provider_type="llm")
        _create_model(client_as_admin, provider["id"])
        response = client_as_admin.post("/api/v1/model/get_models_by_provider", json={
            "service_provider_id": provider["id"],
            "sort": "created_at",
        })
        assert response.status_code == 200

    def test_sort_descending(self, client_as_admin):
        provider = _create_service_provider(client_as_admin, provider_type="llm")
        _create_model(client_as_admin, provider["id"])
        response = client_as_admin.post("/api/v1/model/get_models_by_provider", json={
            "service_provider_id": provider["id"],
            "sort": "-created_at",
        })
        assert response.status_code == 200

    def test_invalid_sort_field(self, client_as_member):
        response = client_as_member.post("/api/v1/model/get_models_by_provider", json={
            "service_provider_id": 1,
            "sort": "invalid_field",
        })
        assert response.status_code == 400
        assert "Invalid sort field" in response.json()["detail"]

    def test_empty_results(self, client_as_admin):
        provider = _create_service_provider(client_as_admin, provider_type="llm")
        response = client_as_admin.post("/api/v1/model/get_models_by_provider", json={
            "service_provider_id": provider["id"],
        })
        assert response.status_code in (200, 404)

    def test_page_params(self, client_as_admin):
        provider = _create_service_provider(client_as_admin, provider_type="llm")
        response = client_as_admin.post("/api/v1/model/get_models_by_provider", json={
            "service_provider_id": provider["id"],
            "page": 1,
            "page_size": 5,
        })
        assert response.status_code in (200, 404)

    def test_invalid_page_zero(self, client_as_member):
        response = client_as_member.post("/api/v1/model/get_models_by_provider", json={
            "service_provider_id": 1,
            "page": 0,
        })
        # page=0 is coerced to 1 by `int(... or 1)` in _parse_page; provider 1 may
        # not exist so accept either 200 (data found) or 404 (provider not found)
        assert response.status_code in (200, 404)

    def test_invalid_page_size_exceeds_max(self, client_as_member):
        response = client_as_member.post("/api/v1/model/get_models_by_provider", json={
            "service_provider_id": 1,
            "page_size": 101,
        })
        assert response.status_code == 400


# --- POST /api/v1/model/upsert_model ---

class TestUpsertModel:
    """Tests for POST /api/v1/model/upsert_model"""

    def test_create_model_success(self, client_as_admin):
        """Postman: Upsert Model - Create (200)."""
        provider = _create_service_provider(client_as_admin, provider_type="llm")
        data = {
            "service_provider_id": provider["id"],
            "name": "gpt-4o",
            "service_type": "llm",
            "meta_data": {},
            "status": "active",
        }
        resp = client_as_admin.post("/api/v1/model/upsert_model", json=data)
        assert resp.status_code == 200
        result = resp.json()
        assert result["name"] == "gpt-4o"
        assert result["service_type"] == "llm"
        assert "id" in result

    def test_update_model_by_id(self, client_as_admin):
        """Postman: Upsert Model - Update (pass id)."""
        provider = _create_service_provider(client_as_admin, provider_type="llm")
        created = _create_model(client_as_admin, provider["id"], name="original-model", service_type="llm")
        resp = client_as_admin.post("/api/v1/model/upsert_model", json={
            "id": created["id"],
            "service_provider_id": provider["id"],
            "name": "updated-model",
            "service_type": "llm",
            "status": "active",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "updated-model"

    def test_create_stt_model(self, client_as_admin):
        provider = _create_service_provider(client_as_admin, provider_type="stt")
        data = _create_model(client_as_admin, provider["id"], name="chirp_3", service_type="stt")
        assert data["service_type"] == "stt"

    def test_create_tts_model(self, client_as_admin):
        provider = _create_service_provider(client_as_admin, provider_type="tts")
        data = _create_model(client_as_admin, provider["id"], name="sonic-3", service_type="tts")
        assert data["service_type"] == "tts"

    def test_create_with_meta_data(self, client_as_admin):
        provider = _create_service_provider(client_as_admin, provider_type="llm")
        data = _create_model(
            client_as_admin, provider["id"], name="gpt-4-meta",
            service_type="llm", meta_data={"context_window": 128000},
        )
        assert data["name"] == "gpt-4-meta"

    def test_create_with_meta_data_schema(self, client_as_admin):
        provider = _create_service_provider(client_as_admin, provider_type="llm")
        schema = [
            {"name": "temperature", "type": "float", "min": 0.0, "max": 2.0},
            {"name": "frequency_penalty", "type": "float", "min": -2.0, "max": 2.0},
        ]
        data = _create_model(
            client_as_admin, provider["id"], name="gpt-4-schema",
            service_type="llm", meta_data_schema=schema,
        )
        assert data["name"] == "gpt-4-schema"

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/model/upsert_model", json={"name": "gpt-4"})
        assert response.status_code in (401, 403)

    def test_create_missing_service_provider_id(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/model/upsert_model", json={
            "name": "test-model", "service_type": "llm",
        })
        assert resp.status_code == 400

    def test_create_missing_name(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/model/upsert_model", json={
            "service_provider_id": 1, "service_type": "llm",
        })
        assert resp.status_code == 400

    def test_create_service_provider_not_found(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/model/upsert_model", json={
            "service_provider_id": 999999, "name": "test", "service_type": "llm",
        })
        assert resp.status_code in (400, 404)

    def test_update_model_not_found(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/model/upsert_model", json={
            "id": 999999, "service_provider_id": 1, "name": "test", "service_type": "llm",
        })
        assert resp.status_code in (400, 404)


# --- DELETE /api/v1/model/delete_model ---

class TestDeleteModel:
    """Tests for DELETE /api/v1/model/delete_model"""

    def test_delete_model_success(self, client_as_admin):
        """Postman: Delete Model - Success (200)."""
        provider = _create_service_provider(client_as_admin, provider_type="llm")
        created = _create_model(client_as_admin, provider["id"])
        resp = client_as_admin.delete(f"/api/v1/model/delete_model?model_id={created['id']}")
        assert resp.status_code == 200

    def test_delete_model_missing_id(self, client_as_member):
        response = client_as_member.delete("/api/v1/model/delete_model")
        assert response.status_code == 422

    def test_delete_model_invalid_id(self, client_as_member):
        response = client_as_member.delete("/api/v1/model/delete_model?model_id=abc")
        assert response.status_code == 422

    def test_delete_model_not_found(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/model/delete_model?model_id=999999")
        assert response.status_code == 404

    def test_delete_model_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/model/delete_model?model_id=1")
        assert response.status_code in (401, 403)
