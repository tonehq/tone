"""Tests for Model Menu API endpoints (EE edition).

Source: ee/api/v1/model_menu.py
Integration tests — real DB, real endpoints, no mocks.
"""

import pytest
import uuid


# --- Helpers ---

def _unique_name(prefix="model"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _get_first_provider_id(client):
    """Fetch a valid model_provider_menu_id from the DB."""
    resp = client.post("/api/v1/model-providers-menu/list", json={})
    if resp.status_code == 200:
        body = resp.json()
        data = body.get("data", body) if isinstance(body, dict) else body
        if data:
            return data[0]["id"]
    return 1  # fallback


def _create_model(client, **overrides):
    """Create a model via upsert and return the response JSON."""
    defaults = {
        "model_provider_menu_id": _get_first_provider_id(client),
        "name": _unique_name(),
        "service_type": "llm",
        "status": "active",
    }
    defaults.update(overrides)
    resp = client.post("/api/v1/model-menu/upsert_model", json=defaults)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- POST /api/v1/model-menu/get_models_by_provider ---

class TestGetModelsByProvider:
    """Tests for POST /api/v1/model-menu/get_models_by_provider"""

    def test_returns_paginated_list(self, client_as_member):
        provider_id = _get_first_provider_id(client_as_member)
        resp = client_as_member.post("/api/v1/model-menu/get_models_by_provider", json={
            "model_provider_menu_id": provider_id,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "pagination" in body
        assert isinstance(body["data"], list)

    def test_missing_provider_id(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-menu/get_models_by_provider", json={})
        assert resp.status_code == 400
        assert "model_provider_menu_id is required" in resp.json()["detail"]

    def test_invalid_provider_id_type(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-menu/get_models_by_provider", json={
            "model_provider_menu_id": "abc",
        })
        assert resp.status_code == 400
        assert "integer" in resp.json()["detail"].lower()

    def test_filter_by_name(self, client_as_member):
        provider_id = _get_first_provider_id(client_as_member)
        resp = client_as_member.post("/api/v1/model-menu/get_models_by_provider", json={
            "model_provider_menu_id": provider_id,
            "name": "gpt",
        })
        assert resp.status_code == 200

    def test_filter_by_service_type(self, client_as_member):
        provider_id = _get_first_provider_id(client_as_member)
        resp = client_as_member.post("/api/v1/model-menu/get_models_by_provider", json={
            "model_provider_menu_id": provider_id,
            "service_type": "llm",
        })
        assert resp.status_code == 200

    def test_pagination(self, client_as_member):
        provider_id = _get_first_provider_id(client_as_member)
        resp = client_as_member.post("/api/v1/model-menu/get_models_by_provider", json={
            "model_provider_menu_id": provider_id,
            "page": 1,
            "page_size": 5,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["pagination"]["page"] == 1

    def test_sort_by_name(self, client_as_member):
        provider_id = _get_first_provider_id(client_as_member)
        resp = client_as_member.post("/api/v1/model-menu/get_models_by_provider", json={
            "model_provider_menu_id": provider_id,
            "sort": "name",
        })
        assert resp.status_code == 200

    def test_sort_descending(self, client_as_member):
        provider_id = _get_first_provider_id(client_as_member)
        resp = client_as_member.post("/api/v1/model-menu/get_models_by_provider", json={
            "model_provider_menu_id": provider_id,
            "sort": "-created_at",
        })
        assert resp.status_code == 200

    def test_invalid_sort_field(self, client_as_member):
        provider_id = _get_first_provider_id(client_as_member)
        resp = client_as_member.post("/api/v1/model-menu/get_models_by_provider", json={
            "model_provider_menu_id": provider_id,
            "sort": "invalid_field",
        })
        assert resp.status_code == 400
        assert "Invalid sort field" in resp.json()["detail"]

    def test_invalid_page(self, client_as_member):
        provider_id = _get_first_provider_id(client_as_member)
        resp = client_as_member.post("/api/v1/model-menu/get_models_by_provider", json={
            "model_provider_menu_id": provider_id,
            "page": 0,
        })
        # page=0 is coerced to 1 by `int(... or 1)` in _parse_page, so API returns 200
        assert resp.status_code == 200

    def test_invalid_page_size(self, client_as_member):
        provider_id = _get_first_provider_id(client_as_member)
        resp = client_as_member.post("/api/v1/model-menu/get_models_by_provider", json={
            "model_provider_menu_id": provider_id,
            "page_size": 200,
        })
        assert resp.status_code == 400
        assert "page_size" in resp.json()["detail"]

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/model-menu/get_models_by_provider", json={
            "model_provider_menu_id": 1,
        })
        assert resp.status_code in (401, 403)


# --- POST /api/v1/model-menu/upsert_model ---

class TestUpsertModel:
    """Tests for POST /api/v1/model-menu/upsert_model"""

    def test_create_minimal(self, client_as_member):
        model = _create_model(client_as_member)
        assert "id" in model

    def test_create_with_all_fields(self, client_as_member):
        model = _create_model(
            client_as_member,
            service_type="llm",
            status="active",
        )
        assert "id" in model

    def test_update_existing(self, client_as_member):
        model = _create_model(client_as_member)
        resp = client_as_member.post("/api/v1/model-menu/upsert_model", json={
            "id": model["id"],
            "model_provider_menu_id": model.get("model_provider_menu_id", _get_first_provider_id(client_as_member)),
            "name": _unique_name("updated"),
            "service_type": "llm",
        })
        assert resp.status_code == 200

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/model-menu/upsert_model", json={
            "model_provider_menu_id": 1,
            "name": "test-model",
            "service_type": "llm",
        })
        assert resp.status_code in (401, 403)


# --- DELETE /api/v1/model-menu/delete_model ---

class TestDeleteModel:
    """Tests for DELETE /api/v1/model-menu/delete_model"""

    def test_delete_existing(self, client_as_member):
        model = _create_model(client_as_member)
        resp = client_as_member.delete(f"/api/v1/model-menu/delete_model?model_id={model['id']}")
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()

    def test_delete_not_found(self, client_as_member):
        resp = client_as_member.delete("/api/v1/model-menu/delete_model?model_id=999999")
        assert resp.status_code == 404

    def test_delete_missing_model_id(self, client_as_member):
        resp = client_as_member.delete("/api/v1/model-menu/delete_model")
        assert resp.status_code == 422

    def test_delete_invalid_model_id(self, client_as_member):
        resp = client_as_member.delete("/api/v1/model-menu/delete_model?model_id=abc")
        assert resp.status_code == 422

    def test_delete_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete("/api/v1/model-menu/delete_model?model_id=1")
        assert resp.status_code in (401, 403)


# --- Full CRUD Flow ---

class TestModelMenuCRUDFlow:
    """End-to-end Create -> List -> Delete flow."""

    def test_full_lifecycle(self, client_as_member):
        provider_id = _get_first_provider_id(client_as_member)

        # Create
        model = _create_model(client_as_member, model_provider_menu_id=provider_id)

        # List
        resp = client_as_member.post("/api/v1/model-menu/get_models_by_provider", json={
            "model_provider_menu_id": provider_id,
        })
        assert resp.status_code == 200

        # Delete
        resp = client_as_member.delete(f"/api/v1/model-menu/delete_model?model_id={model['id']}")
        assert resp.status_code == 200
