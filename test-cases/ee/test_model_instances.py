"""Tests for Model Instance API endpoints (EE edition).

Source: ee/api/v1/model_instances.py
Integration tests — real DB, real endpoints, no mocks.
"""

import pytest
import uuid


# --- Helpers ---

def _unique_name(prefix="instance"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _get_first_model_menu_id(client):
    """Fetch a valid model_menu_id from the DB via the model-menu endpoint."""
    # Try to get models from the first provider
    providers = client.post("/api/v1/model-providers-menu/list", json={}).json()
    data = providers.get("data", providers) if isinstance(providers, dict) else providers
    if data:
        models_resp = client.post("/api/v1/model-menu/get_models_by_provider", json={
            "model_provider_menu_id": data[0]["id"],
        })
        if models_resp.status_code == 200:
            models_data = models_resp.json()
            items = models_data.get("data", models_data) if isinstance(models_data, dict) else models_data
            if items:
                return items[0]["id"]
    return 1  # fallback


def _get_first_account_id(client):
    """Fetch a valid account_id from the DB."""
    resp = client.post("/api/v1/accounts/list", json={})
    if resp.status_code == 200:
        accounts = resp.json()
        if accounts:
            return accounts[0]["id"]
    return 1  # fallback


def _create_model_instance(client, **overrides):
    """Create a model instance and return the response JSON."""
    defaults = {
        "model_menu_id": _get_first_model_menu_id(client),
        "account_id": _get_first_account_id(client),
        "host_region": "us-east-1",
        "status": "active",
    }
    defaults.update(overrides)
    resp = client.post("/api/v1/model-instances/upsert", json=defaults)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- POST /api/v1/model-instances/upsert ---

class TestUpsertModelInstance:
    """Tests for POST /api/v1/model-instances/upsert"""

    def test_create_minimal(self, client_as_admin):
        mi = _create_model_instance(client_as_admin)
        assert "id" in mi

    def test_create_with_host_region(self, client_as_admin):
        mi = _create_model_instance(client_as_admin, host_region="eu-west-1")
        assert mi.get("host_region") == "eu-west-1"

    def test_update_existing(self, client_as_admin):
        mi = _create_model_instance(client_as_admin)
        resp = client_as_admin.post("/api/v1/model-instances/upsert", json={
            "id": mi["id"],
            "model_menu_id": mi["model_menu_id"],
            "host_region": "ap-southeast-1",
        })
        assert resp.status_code == 200

    def test_missing_model_menu_id(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/model-instances/upsert", json={
            "account_id": 1,
        })
        assert resp.status_code == 400
        assert "model_menu_id" in resp.json()["detail"]

    def test_empty_body(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/model-instances/upsert", json={})
        assert resp.status_code == 400

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/model-instances/upsert", json={
            "model_menu_id": 1,
        })
        assert resp.status_code in (401, 403)

    def test_member_cannot_upsert(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-instances/upsert", json={
            "model_menu_id": 1,
        })
        assert resp.status_code in (401, 403)


# --- POST /api/v1/model-instances/list ---

class TestListModelInstances:
    """Tests for POST /api/v1/model-instances/list"""

    def test_returns_paginated_list(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-instances/list", json={})
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "pagination" in body
        assert isinstance(body["data"], list)

    def test_filter_by_status(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-instances/list", json={
            "status": "active",
        })
        assert resp.status_code == 200

    def test_pagination(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-instances/list", json={
            "page": 1,
            "page_size": 5,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["pagination"]["page"] == 1

    def test_sort_descending(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-instances/list", json={
            "sort": "-created_at",
        })
        assert resp.status_code == 200

    def test_invalid_sort_field(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-instances/list", json={
            "sort": "invalid_field",
        })
        assert resp.status_code == 400

    def test_invalid_page(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-instances/list", json={
            "page": 0,
        })
        # page=0 is coerced to 1 by `int(... or 1)` in _parse_page, so API returns 200
        assert resp.status_code == 200

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/model-instances/list", json={})
        assert resp.status_code in (401, 403)


# --- POST /api/v1/model-instances/get ---

class TestGetModelInstance:
    """Tests for POST /api/v1/model-instances/get"""

    def test_get_existing(self, client_as_admin):
        mi = _create_model_instance(client_as_admin)
        resp = client_as_admin.post("/api/v1/model-instances/get", json={
            "instance_id": mi["id"],
        })
        assert resp.status_code == 200
        assert resp.json()["id"] == mi["id"]

    def test_missing_instance_id(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-instances/get", json={})
        assert resp.status_code == 400
        assert "instance_id is required" in resp.json()["detail"]

    def test_not_found(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-instances/get", json={
            "instance_id": 999999,
        })
        assert resp.status_code == 404

    def test_invalid_instance_id_type(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-instances/get", json={
            "instance_id": "abc",
        })
        assert resp.status_code == 400
        assert "integer" in resp.json()["detail"].lower()

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/model-instances/get", json={
            "instance_id": 1,
        })
        assert resp.status_code in (401, 403)


# --- DELETE /api/v1/model-instances/delete ---

class TestDeleteModelInstance:
    """Tests for DELETE /api/v1/model-instances/delete"""

    def test_delete_existing(self, client_as_admin):
        mi = _create_model_instance(client_as_admin)
        resp = client_as_admin.delete(f"/api/v1/model-instances/delete?instance_id={mi['id']}")
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()

    def test_delete_not_found(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/model-instances/delete?instance_id=999999")
        assert resp.status_code == 404

    def test_delete_missing_instance_id(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/model-instances/delete")
        assert resp.status_code == 422

    def test_delete_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete("/api/v1/model-instances/delete?instance_id=1")
        assert resp.status_code in (401, 403)

    def test_member_cannot_delete(self, client_as_member):
        resp = client_as_member.delete("/api/v1/model-instances/delete?instance_id=1")
        assert resp.status_code in (401, 403)


# --- Full CRUD Flow ---

class TestModelInstanceCRUDFlow:
    """End-to-end Create -> Read -> Update -> Delete flow."""

    def test_full_lifecycle(self, client_as_admin):
        # Create
        mi = _create_model_instance(client_as_admin)

        # Read
        resp = client_as_admin.post("/api/v1/model-instances/get", json={
            "instance_id": mi["id"],
        })
        assert resp.status_code == 200

        # List
        resp = client_as_admin.post("/api/v1/model-instances/list", json={})
        assert resp.status_code == 200

        # Update
        resp = client_as_admin.post("/api/v1/model-instances/upsert", json={
            "id": mi["id"],
            "model_menu_id": mi["model_menu_id"],
            "host_region": "eu-central-1",
        })
        assert resp.status_code == 200

        # Delete
        resp = client_as_admin.delete(f"/api/v1/model-instances/delete?instance_id={mi['id']}")
        assert resp.status_code == 200
