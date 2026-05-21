"""Tests for Hosting Provider API endpoints (EE edition).

Source: ee/api/v1/hosting_providers.py
Integration tests — real DB, real endpoints, no mocks.
"""

import pytest
import uuid


# --- Helpers ---

def _unique_name(prefix="hosting"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_hosting_provider(client, **overrides):
    """Create a hosting provider and return the response JSON."""
    name = _unique_name()
    defaults = {
        "name": name,
        "display_name": f"HP {name}",
        "description": "Test hosting provider",
    }
    defaults.update(overrides)
    resp = client.post("/api/v1/hosting-providers/upsert", json=defaults)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- POST /api/v1/hosting-providers/upsert ---

class TestUpsertHostingProvider:
    """Tests for POST /api/v1/hosting-providers/upsert"""

    def test_create_minimal(self, client_as_admin):
        hp = _create_hosting_provider(client_as_admin)
        assert "id" in hp
        assert hp["status"] == "active"

    def test_create_with_all_fields(self, client_as_admin):
        hp = _create_hosting_provider(
            client_as_admin,
            logo_url="https://example.com/logo.png",
            website_url="https://example.com",
            is_system=False,
        )
        assert "id" in hp

    def test_update_existing(self, client_as_admin):
        hp = _create_hosting_provider(client_as_admin)
        updated_name = _unique_name("updated")
        resp = client_as_admin.post("/api/v1/hosting-providers/upsert", json={
            "id": hp["id"],
            "name": updated_name,
            "display_name": f"Updated {updated_name}",
        })
        assert resp.status_code == 200

    def test_missing_required_fields(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/hosting-providers/upsert", json={})
        assert resp.status_code == 400

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/hosting-providers/upsert", json={
            "name": "test",
            "display_name": "Test",
        })
        assert resp.status_code in (401, 403)

    def test_member_cannot_upsert(self, client_as_member):
        resp = client_as_member.post("/api/v1/hosting-providers/upsert", json={
            "name": _unique_name(),
            "display_name": "Test",
        })
        assert resp.status_code in (401, 403)


# --- POST /api/v1/hosting-providers/list ---

class TestListHostingProviders:
    """Tests for POST /api/v1/hosting-providers/list"""

    def test_returns_paginated_list(self, client_as_member):
        resp = client_as_member.post("/api/v1/hosting-providers/list", json={})
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "pagination" in body
        assert isinstance(body["data"], list)

    def test_filter_by_name(self, client_as_admin):
        hp = _create_hosting_provider(client_as_admin)
        resp = client_as_admin.post("/api/v1/hosting-providers/list", json={
            "name": hp["name"],
        })
        assert resp.status_code == 200

    def test_filter_by_status(self, client_as_member):
        resp = client_as_member.post("/api/v1/hosting-providers/list", json={
            "status": "active",
        })
        assert resp.status_code == 200

    def test_pagination(self, client_as_member):
        resp = client_as_member.post("/api/v1/hosting-providers/list", json={
            "page": 1,
            "page_size": 5,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["pagination"]["page"] == 1
        assert body["pagination"]["page_size"] == 5

    def test_sort_ascending(self, client_as_member):
        resp = client_as_member.post("/api/v1/hosting-providers/list", json={
            "sort": "name",
        })
        assert resp.status_code == 200

    def test_sort_descending(self, client_as_member):
        resp = client_as_member.post("/api/v1/hosting-providers/list", json={
            "sort": "-created_at",
        })
        assert resp.status_code == 200

    def test_invalid_sort_field(self, client_as_member):
        resp = client_as_member.post("/api/v1/hosting-providers/list", json={
            "sort": "invalid_field",
        })
        assert resp.status_code == 400
        assert "Invalid sort field" in resp.json()["detail"]

    def test_invalid_page(self, client_as_member):
        resp = client_as_member.post("/api/v1/hosting-providers/list", json={
            "page": 0,
        })
        # page=0 is coerced to 1 by `int(... or 1)` in _parse_page, so API returns 200
        assert resp.status_code == 200

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/hosting-providers/list", json={})
        assert resp.status_code in (401, 403)


# --- POST /api/v1/hosting-providers/get ---

class TestGetHostingProvider:
    """Tests for POST /api/v1/hosting-providers/get"""

    def test_get_existing(self, client_as_admin):
        hp = _create_hosting_provider(client_as_admin)
        resp = client_as_admin.post("/api/v1/hosting-providers/get", json={
            "provider_id": hp["id"],
        })
        assert resp.status_code == 200
        assert resp.json()["id"] == hp["id"]

    def test_missing_provider_id(self, client_as_member):
        resp = client_as_member.post("/api/v1/hosting-providers/get", json={})
        assert resp.status_code == 400
        assert "provider_id is required" in resp.json()["detail"]

    def test_not_found(self, client_as_member):
        resp = client_as_member.post("/api/v1/hosting-providers/get", json={
            "provider_id": 999999,
        })
        assert resp.status_code == 404

    def test_invalid_provider_id_type(self, client_as_member):
        resp = client_as_member.post("/api/v1/hosting-providers/get", json={
            "provider_id": "abc",
        })
        assert resp.status_code == 400
        assert "integer" in resp.json()["detail"].lower()

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/hosting-providers/get", json={
            "provider_id": 1,
        })
        assert resp.status_code in (401, 403)


# --- DELETE /api/v1/hosting-providers/delete ---

class TestDeleteHostingProvider:
    """Tests for DELETE /api/v1/hosting-providers/delete"""

    def test_delete_existing(self, client_as_admin):
        hp = _create_hosting_provider(client_as_admin)
        resp = client_as_admin.delete(f"/api/v1/hosting-providers/delete?provider_id={hp['id']}")
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()

    def test_delete_not_found(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/hosting-providers/delete?provider_id=999999")
        assert resp.status_code == 404

    def test_delete_missing_provider_id(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/hosting-providers/delete")
        assert resp.status_code == 422

    def test_delete_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete("/api/v1/hosting-providers/delete?provider_id=1")
        assert resp.status_code in (401, 403)

    def test_member_cannot_delete(self, client_as_member):
        resp = client_as_member.delete("/api/v1/hosting-providers/delete?provider_id=1")
        assert resp.status_code in (401, 403)


# --- Full CRUD Flow ---

class TestHostingProviderCRUDFlow:
    """End-to-end Create -> Read -> Update -> Delete flow."""

    def test_full_lifecycle(self, client_as_admin):
        # Create
        hp = _create_hosting_provider(client_as_admin)

        # Read
        resp = client_as_admin.post("/api/v1/hosting-providers/get", json={
            "provider_id": hp["id"],
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == hp["name"]

        # List
        resp = client_as_admin.post("/api/v1/hosting-providers/list", json={})
        assert resp.status_code == 200

        # Update
        updated_name = _unique_name("updated")
        resp = client_as_admin.post("/api/v1/hosting-providers/upsert", json={
            "id": hp["id"],
            "name": updated_name,
            "display_name": f"Updated {updated_name}",
        })
        assert resp.status_code == 200

        # Delete
        resp = client_as_admin.delete(f"/api/v1/hosting-providers/delete?provider_id={hp['id']}")
        assert resp.status_code == 200
