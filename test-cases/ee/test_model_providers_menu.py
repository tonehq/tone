"""Tests for Model Providers Menu API endpoints (EE edition).

Source: ee/api/v1/model_providers_menu.py
Integration tests — real DB, real endpoints, no mocks.
"""

import pytest
import uuid


# --- Helpers ---

def _unique_name(prefix="provider"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_model_provider_menu(client, **overrides):
    """Create a model provider menu entry and return the response JSON."""
    name = _unique_name()
    defaults = {
        "name": name,
        "display_name": f"Provider {name}",
        "provider_type": "llm",
        "auth_type": "api_key",
        "description": "Test model provider",
    }
    defaults.update(overrides)
    resp = client.post("/api/v1/model-providers-menu/upsert", json=defaults)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- POST /api/v1/model-providers-menu/upsert ---

class TestUpsertModelProviderMenu:
    """Tests for POST /api/v1/model-providers-menu/upsert"""

    def test_create_minimal(self, client_as_admin):
        mpm = _create_model_provider_menu(client_as_admin)
        assert "id" in mpm
        assert mpm["status"] == "active"

    def test_create_with_all_fields(self, client_as_admin):
        mpm = _create_model_provider_menu(
            client_as_admin,
            logo_url="https://example.com/logo.png",
            website_url="https://example.com",
            documentation_url="https://docs.example.com",
            base_url="https://api.example.com/v1",
            supports_streaming=True,
            config_schema={},
            is_system=False,
        )
        assert "id" in mpm

    def test_update_existing(self, client_as_admin):
        mpm = _create_model_provider_menu(client_as_admin)
        updated_name = _unique_name("updated")
        resp = client_as_admin.post("/api/v1/model-providers-menu/upsert", json={
            "id": mpm["id"],
            "name": updated_name,
            "display_name": f"Updated {updated_name}",
            "provider_type": "llm",
            "auth_type": "api_key",
        })
        assert resp.status_code == 200

    def test_missing_required_fields(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/model-providers-menu/upsert", json={})
        assert resp.status_code == 400

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/model-providers-menu/upsert", json={
            "name": "test",
            "display_name": "Test",
            "provider_type": "llm",
            "auth_type": "api_key",
        })
        assert resp.status_code in (401, 403)

    def test_member_cannot_upsert(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-providers-menu/upsert", json={
            "name": _unique_name(),
            "display_name": "Test",
            "provider_type": "llm",
            "auth_type": "api_key",
        })
        assert resp.status_code in (401, 403)


# --- POST /api/v1/model-providers-menu/list ---

class TestListModelProviderMenus:
    """Tests for POST /api/v1/model-providers-menu/list"""

    def test_returns_paginated_list(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-providers-menu/list", json={})
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "pagination" in body
        assert isinstance(body["data"], list)

    def test_filter_by_provider_type(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-providers-menu/list", json={
            "provider_type": "llm",
        })
        # Note: provider_type may not be a supported filter in list; still should return 200
        assert resp.status_code == 200

    def test_filter_by_name(self, client_as_admin):
        mpm = _create_model_provider_menu(client_as_admin)
        resp = client_as_admin.post("/api/v1/model-providers-menu/list", json={
            "name": mpm["name"],
        })
        assert resp.status_code == 200

    def test_filter_by_status(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-providers-menu/list", json={
            "status": "active",
        })
        assert resp.status_code == 200

    def test_pagination(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-providers-menu/list", json={
            "page": 1,
            "page_size": 5,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["pagination"]["page"] == 1
        assert body["pagination"]["page_size"] == 5

    def test_sort_ascending(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-providers-menu/list", json={
            "sort": "name",
        })
        assert resp.status_code == 200

    def test_sort_descending(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-providers-menu/list", json={
            "sort": "-created_at",
        })
        assert resp.status_code == 200

    def test_invalid_sort_field(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-providers-menu/list", json={
            "sort": "invalid_field",
        })
        assert resp.status_code == 400
        assert "Invalid sort field" in resp.json()["detail"]

    def test_invalid_page(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-providers-menu/list", json={
            "page": 0,
        })
        # page=0 is coerced to 1 by `int(... or 1)` in _parse_page, so API returns 200
        assert resp.status_code == 200

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/model-providers-menu/list", json={})
        assert resp.status_code in (401, 403)


# --- POST /api/v1/model-providers-menu/get ---

class TestGetModelProviderMenu:
    """Tests for POST /api/v1/model-providers-menu/get"""

    def test_get_existing(self, client_as_admin):
        mpm = _create_model_provider_menu(client_as_admin)
        resp = client_as_admin.post("/api/v1/model-providers-menu/get", json={
            "provider_id": mpm["id"],
        })
        assert resp.status_code == 200
        assert resp.json()["id"] == mpm["id"]

    def test_missing_provider_id(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-providers-menu/get", json={})
        assert resp.status_code == 400
        assert "provider_id is required" in resp.json()["detail"]

    def test_not_found(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-providers-menu/get", json={
            "provider_id": 999999,
        })
        assert resp.status_code == 404

    def test_invalid_provider_id_type(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-providers-menu/get", json={
            "provider_id": "abc",
        })
        assert resp.status_code == 400
        assert "integer" in resp.json()["detail"].lower()

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/model-providers-menu/get", json={
            "provider_id": 1,
        })
        assert resp.status_code in (401, 403)


# --- POST /api/v1/model-providers-menu/list-with-accounts ---

class TestListProvidersWithAccounts:
    """Tests for POST /api/v1/model-providers-menu/list-with-accounts"""

    def test_returns_list(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-providers-menu/list-with-accounts", json={})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_filter_by_provider_type(self, client_as_member):
        resp = client_as_member.post("/api/v1/model-providers-menu/list-with-accounts", json={
            "provider_type": "llm",
        })
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/model-providers-menu/list-with-accounts", json={})
        assert resp.status_code in (401, 403)


# --- DELETE /api/v1/model-providers-menu/delete ---

class TestDeleteModelProviderMenu:
    """Tests for DELETE /api/v1/model-providers-menu/delete"""

    def test_delete_existing(self, client_as_admin):
        mpm = _create_model_provider_menu(client_as_admin)
        resp = client_as_admin.delete(f"/api/v1/model-providers-menu/delete?provider_id={mpm['id']}")
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()

    def test_delete_not_found(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/model-providers-menu/delete?provider_id=999999")
        assert resp.status_code == 404

    def test_delete_missing_provider_id(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/model-providers-menu/delete")
        assert resp.status_code == 422

    def test_delete_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete("/api/v1/model-providers-menu/delete?provider_id=1")
        assert resp.status_code in (401, 403)

    def test_member_cannot_delete(self, client_as_member):
        resp = client_as_member.delete("/api/v1/model-providers-menu/delete?provider_id=1")
        assert resp.status_code in (401, 403)


# --- Full CRUD Flow ---

class TestModelProviderMenuCRUDFlow:
    """End-to-end Create -> Read -> List -> Delete flow."""

    def test_full_lifecycle(self, client_as_admin):
        # Create
        mpm = _create_model_provider_menu(client_as_admin)

        # Read
        resp = client_as_admin.post("/api/v1/model-providers-menu/get", json={
            "provider_id": mpm["id"],
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == mpm["name"]

        # List
        resp = client_as_admin.post("/api/v1/model-providers-menu/list", json={})
        assert resp.status_code == 200

        # List with accounts
        resp = client_as_admin.post("/api/v1/model-providers-menu/list-with-accounts", json={})
        assert resp.status_code == 200

        # Update
        updated_name = _unique_name("updated")
        resp = client_as_admin.post("/api/v1/model-providers-menu/upsert", json={
            "id": mpm["id"],
            "name": updated_name,
            "display_name": f"Updated {updated_name}",
            "provider_type": "llm",
            "auth_type": "api_key",
        })
        assert resp.status_code == 200

        # Delete
        resp = client_as_admin.delete(f"/api/v1/model-providers-menu/delete?provider_id={mpm['id']}")
        assert resp.status_code == 200
