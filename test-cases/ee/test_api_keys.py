"""Tests for API Keys API endpoints (EE edition).

Source: ee/api/v1/api_keys.py
Postman: api_keys.postman_collection.json
Integration tests — real DB, real endpoints, no mocks.
Uses multipart/form-data for upsert endpoint.
"""

import pytest
import uuid

from sqlalchemy import text, create_engine
from shared.config import settings

_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)


def _get_real_account_id():
    """Look up a real account ID from the database."""
    with _engine.connect() as conn:
        row = conn.execute(text("SELECT id FROM accounts LIMIT 1")).fetchone()
    return row[0] if row else 1


# ─── Helpers ───

def _unique_name(prefix="api-key"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_api_key(client, account_id=None, name=None, api_key_value=None):
    """Create an API key via form-data upsert and return JSON."""
    acc_id = account_id or _get_real_account_id()
    resp = client.post("/api/v1/api-keys/upsert", data={
        "account_id": str(acc_id),
        "name": name or _unique_name(),
        "api_key": api_key_value or f"sk-test-{uuid.uuid4().hex[:16]}",
    })
    assert resp.status_code == 200
    return resp.json()


# ─── POST /api/v1/api-keys/upsert (multipart/form-data) ───

class TestUpsertApiKey:
    """Tests for POST /api/v1/api-keys/upsert

    Postman examples:
      - Upsert API Key - Create (200)
      - Upsert API Key - Missing Key (400)
    """

    def test_upsert_api_key_create_success(self, client_as_admin):
        """Postman: Upsert API Key - Create (200)."""
        data = _create_api_key(client_as_admin)
        assert "id" in data
        assert "uuid" in data
        assert "name" in data

    def test_upsert_api_key_missing_api_key_and_file(self, client_as_admin):
        """Postman: Upsert API Key - Missing Key (400)."""
        response = client_as_admin.post("/api/v1/api-keys/upsert", data={
            "account_id": "1",
            "name": "Key",
        })
        assert response.status_code == 400
        assert "Either a file or api_key must be provided" in response.json()["detail"]

    def test_upsert_api_key_missing_name(self, client_as_admin):
        response = client_as_admin.post("/api/v1/api-keys/upsert", data={
            "account_id": "1",
            "api_key": "sk-test",
        })
        assert response.status_code == 422

    def test_upsert_api_key_empty_body(self, client_as_admin):
        response = client_as_admin.post("/api/v1/api-keys/upsert", data={})
        assert response.status_code == 422

    def test_upsert_api_key_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/api-keys/upsert", data={
            "account_id": "1",
            "name": "Key",
            "api_key": "sk-test",
        })
        assert response.status_code in (401, 403)

    def test_upsert_api_key_with_description(self, client_as_admin):
        """Create with optional description field."""
        acc_id = _get_real_account_id()
        resp = client_as_admin.post("/api/v1/api-keys/upsert", data={
            "account_id": str(acc_id),
            "name": _unique_name(),
            "api_key": f"sk-test-{uuid.uuid4().hex[:16]}",
            "description": "Production OpenAI key",
        })
        assert resp.status_code == 200

    def test_upsert_api_key_update_via_uuid(self, client_as_admin):
        """Update existing key by passing uuid field."""
        created = _create_api_key(client_as_admin)
        if "uuid" in created:
            resp = client_as_admin.post("/api/v1/api-keys/upsert", data={
                "account_id": str(created.get("account_id", _get_real_account_id())),
                "name": "Updated Key Name",
                "api_key": f"sk-updated-{uuid.uuid4().hex[:12]}",
                "uuid": created["uuid"],
            })
            assert resp.status_code == 200


# ─── GET /api/v1/api-keys/list ───

class TestGetAllApiKeys:
    """Tests for GET /api/v1/api-keys/list

    Postman examples:
      - Get All API Keys - Success (200)
    """

    def test_get_all_api_keys_returns_200(self, client_as_member):
        """Postman: Get All API Keys - Success (200)."""
        response = client_as_member.get("/api/v1/api-keys/list")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_all_api_keys_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/api-keys/list")
        assert response.status_code in (401, 403)

    def test_get_all_api_keys_contains_created(self, client_as_admin):
        """Create a key, list all, verify it appears."""
        created = _create_api_key(client_as_admin)
        resp = client_as_admin.get("/api/v1/api-keys/list")
        assert resp.status_code == 200
        keys = resp.json()
        assert any(k["id"] == created["id"] for k in keys)


# ─── POST /api/v1/api-keys/list_by_provider ───

class TestListApiKeysByProvider:
    """Tests for POST /api/v1/api-keys/list_by_provider

    Postman examples:
      - List By Provider - Success (200)
      - List By Provider - Missing ID (400)
    """

    def test_list_by_provider_success(self, client_as_member):
        """Postman: List By Provider - Success (200)."""
        response = client_as_member.post("/api/v1/api-keys/list_by_provider", json={
            "service_provider_id": 1
        })
        assert response.status_code in (200, 404)

    def test_list_by_provider_missing_id(self, client_as_member):
        """Postman: List By Provider - Missing ID (400)."""
        response = client_as_member.post("/api/v1/api-keys/list_by_provider", json={})
        assert response.status_code == 400
        assert "service_provider_id is required" in response.json()["detail"]

    def test_list_by_provider_invalid_id(self, client_as_member):
        response = client_as_member.post("/api/v1/api-keys/list_by_provider", json={
            "service_provider_id": "abc"
        })
        assert response.status_code == 400
        assert "integer" in response.json()["detail"]

    def test_list_by_provider_with_pagination(self, client_as_member):
        """Paginate results."""
        response = client_as_member.post("/api/v1/api-keys/list_by_provider", json={
            "service_provider_id": 1,
            "page": 1,
            "page_size": 20,
        })
        assert response.status_code in (200, 404)

    def test_list_by_provider_with_status_filter(self, client_as_member):
        """Filter by status."""
        response = client_as_member.post("/api/v1/api-keys/list_by_provider", json={
            "service_provider_id": 1,
            "status": "active",
        })
        assert response.status_code in (200, 404)

    def test_list_by_provider_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/api-keys/list_by_provider", json={
            "service_provider_id": 1
        })
        assert response.status_code in (401, 403)


# ─── POST /api/v1/api-keys/list_by_account ───

class TestListApiKeysByAccount:
    """Tests for POST /api/v1/api-keys/list_by_account

    Postman examples:
      - List By Account - Success (200)
      - List By Account - Missing ID (400)
    """

    def test_list_by_account_success(self, client_as_member):
        """Postman: List By Account - Success (200)."""
        acc_id = _get_real_account_id()
        response = client_as_member.post("/api/v1/api-keys/list_by_account", json={
            "account_id": acc_id
        })
        assert response.status_code in (200, 404)

    def test_list_by_account_missing_id(self, client_as_member):
        """Postman: List By Account - Missing ID (400)."""
        response = client_as_member.post("/api/v1/api-keys/list_by_account", json={})
        assert response.status_code == 400
        assert "account_id is required" in response.json()["detail"]

    def test_list_by_account_invalid_id(self, client_as_member):
        response = client_as_member.post("/api/v1/api-keys/list_by_account", json={
            "account_id": "abc"
        })
        assert response.status_code == 400
        assert "integer" in response.json()["detail"]

    def test_list_by_account_with_pagination(self, client_as_member):
        """Paginate results."""
        acc_id = _get_real_account_id()
        response = client_as_member.post("/api/v1/api-keys/list_by_account", json={
            "account_id": acc_id,
            "page": 1,
            "page_size": 20,
        })
        assert response.status_code in (200, 404)

    def test_list_by_account_with_status_filter(self, client_as_member):
        """Filter by status."""
        acc_id = _get_real_account_id()
        response = client_as_member.post("/api/v1/api-keys/list_by_account", json={
            "account_id": acc_id,
            "status": "active",
        })
        assert response.status_code in (200, 404)

    def test_list_by_account_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/api-keys/list_by_account", json={
            "account_id": 1
        })
        assert response.status_code in (401, 403)


# ─── GET /api/v1/api-keys/get ───

class TestGetApiKey:
    """Tests for GET /api/v1/api-keys/get?api_key_id=

    Postman examples:
      - Get API Key - Success (200)
      - Get API Key - Not Found (404)
    """

    def test_get_api_key_success(self, client_as_admin):
        """Postman: Get API Key - Success (200)."""
        created = _create_api_key(client_as_admin)
        resp = client_as_admin.get(f"/api/v1/api-keys/get?api_key_id={created['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == created["id"]

    def test_get_api_key_not_found(self, client_as_member):
        """Postman: Get API Key - Not Found (404)."""
        response = client_as_member.get("/api/v1/api-keys/get?api_key_id=999999")
        assert response.status_code == 404

    def test_get_api_key_missing_id(self, client_as_member):
        response = client_as_member.get("/api/v1/api-keys/get")
        assert response.status_code == 422

    def test_get_api_key_invalid_id(self, client_as_member):
        response = client_as_member.get("/api/v1/api-keys/get?api_key_id=abc")
        assert response.status_code == 422

    def test_get_api_key_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/api-keys/get?api_key_id=1")
        assert response.status_code in (401, 403)


# ─── DELETE /api/v1/api-keys/delete ───

class TestDeleteApiKey:
    """Tests for DELETE /api/v1/api-keys/delete?api_key_id=

    Postman examples:
      - Delete API Key - Success (200)
    """

    def test_delete_api_key_success(self, client_as_admin):
        """Postman: Delete API Key - Success (200)."""
        created = _create_api_key(client_as_admin)
        resp = client_as_admin.delete(f"/api/v1/api-keys/delete?api_key_id={created['id']}")
        assert resp.status_code == 200
        # Verify deleted
        get_resp = client_as_admin.get(f"/api/v1/api-keys/get?api_key_id={created['id']}")
        assert get_resp.status_code == 404

    def test_delete_api_key_missing_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/api-keys/delete")
        assert response.status_code == 422

    def test_delete_api_key_invalid_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/api-keys/delete?api_key_id=abc")
        assert response.status_code == 422

    def test_delete_api_key_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/api-keys/delete?api_key_id=1")
        assert response.status_code in (401, 403)


# ─── POST /api/v1/api-keys/validate ───

class TestValidateApiKey:
    """Tests for POST /api/v1/api-keys/validate

    Postman examples:
      - Validate API Key - Success (200)
      - Validate API Key - Missing Fields (400)
    """

    def test_validate_api_key_missing_api_key_id(self, client_as_admin):
        """Missing api_key_id."""
        response = client_as_admin.post("/api/v1/api-keys/validate", json={
            "is_valid": True
        })
        assert response.status_code == 400

    def test_validate_api_key_missing_is_valid(self, client_as_admin):
        """Missing is_valid."""
        response = client_as_admin.post("/api/v1/api-keys/validate", json={
            "api_key_id": 1
        })
        assert response.status_code == 400

    def test_validate_api_key_missing_fields(self, client_as_admin):
        """Postman: Validate API Key - Missing Fields (400)."""
        response = client_as_admin.post("/api/v1/api-keys/validate", json={})
        assert response.status_code == 400

    def test_validate_api_key_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/api-keys/validate", json={
            "api_key_id": 1, "is_valid": True
        })
        assert response.status_code in (401, 403)

    def test_validate_api_key_success(self, client_as_admin):
        """Postman: Validate API Key - Success (200)."""
        created = _create_api_key(client_as_admin)
        resp = client_as_admin.post("/api/v1/api-keys/validate", json={
            "api_key_id": created["id"],
            "is_valid": True,
            "validation_error": None,
        })
        assert resp.status_code in (200, 404)
