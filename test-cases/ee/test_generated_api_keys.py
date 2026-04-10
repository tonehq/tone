"""Tests for Generated API Keys endpoints (EE edition).

Source: ee/api/v1/generated_api_keys.py
Integration tests — real DB, real endpoints, no mocks.
"""

import pytest
import uuid


# ─── Helpers ───

def _unique_key_value():
    return f"tone_test_key_{uuid.uuid4().hex[:12]}"


def _create_basic_key(client, name=None, key_value=None):
    """Create a basic key and return the response JSON."""
    name = name or f"test-key-{uuid.uuid4().hex[:8]}"
    key_value = key_value or _unique_key_value()
    resp = client.post("/api/v1/generated-api-keys/upsert", json={
        "name": name, "key_value": key_value,
    })
    assert resp.status_code == 200
    return resp.json()


def _create_full_key(client, name=None, key_value=None, **kwargs):
    """Create a full key with optional security fields and return the response JSON."""
    name = name or f"test-full-key-{uuid.uuid4().hex[:8]}"
    key_value = key_value or _unique_key_value()
    body = {"name": name, "key_value": key_value, **kwargs}
    resp = client.post("/api/v1/generated-api-keys/upsert-full", json=body)
    assert resp.status_code == 200
    return resp.json()


# ─── POST /api/v1/generated-api-keys/upsert ───

class TestUpsertBasicKey:
    """Tests for POST /api/v1/generated-api-keys/upsert"""

    def test_upsert_basic_key_missing_name(self, client_as_admin):
        response = client_as_admin.post("/api/v1/generated-api-keys/upsert", json={
            "key_value": "tk_test"
        })
        assert response.status_code == 400

    def test_upsert_basic_key_missing_key_value(self, client_as_admin):
        response = client_as_admin.post("/api/v1/generated-api-keys/upsert", json={
            "name": "Test Key"
        })
        assert response.status_code == 400

    def test_upsert_basic_key_empty_body(self, client_as_admin):
        response = client_as_admin.post("/api/v1/generated-api-keys/upsert", json={})
        assert response.status_code == 400

    def test_upsert_basic_key_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/generated-api-keys/upsert", json={
            "name": "Key", "key_value": "tk_test"
        })
        assert response.status_code in (401, 403)

    def test_create_basic_key_success(self, client_as_admin):
        """Create a basic key and verify all response fields."""
        data = _create_basic_key(client_as_admin)
        assert "id" in data
        assert "uuid" in data
        assert "name" in data
        assert "key_value" in data

    def test_update_basic_key(self, client_as_admin):
        """Create a key, then update it via ?id= query param."""
        data = _create_basic_key(client_as_admin)
        key_id = data["id"]
        resp = client_as_admin.post(f"/api/v1/generated-api-keys/upsert?id={key_id}", json={
            "name": "Updated Key Name",
            "key_value": _unique_key_value(),
        })
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["name"] == "Updated Key Name"

    def test_update_basic_key_not_found(self, client_as_admin):
        """Update with nonexistent id returns 404."""
        resp = client_as_admin.post("/api/v1/generated-api-keys/upsert?id=9999", json={
            "name": "test", "key_value": "test",
        })
        assert resp.status_code == 404


# ─── POST /api/v1/generated-api-keys/upsert-full ───

class TestUpsertFullKey:
    """Tests for POST /api/v1/generated-api-keys/upsert-full"""

    def test_upsert_full_key_missing_name(self, client_as_admin):
        response = client_as_admin.post("/api/v1/generated-api-keys/upsert-full", json={
            "key_value": "tk_test"
        })
        assert response.status_code == 400

    def test_upsert_full_key_missing_key_value(self, client_as_admin):
        response = client_as_admin.post("/api/v1/generated-api-keys/upsert-full", json={
            "name": "Key"
        })
        assert response.status_code == 400

    def test_upsert_full_key_empty_body(self, client_as_admin):
        response = client_as_admin.post("/api/v1/generated-api-keys/upsert-full", json={})
        assert response.status_code == 400

    def test_upsert_full_key_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/generated-api-keys/upsert-full", json={
            "name": "Key", "key_value": "tk_test"
        })
        assert response.status_code in (401, 403)

    def test_create_full_key_all_security_fields(self, client_as_admin):
        """Create full key with domains, abuse_prevention, fraud_protection."""
        data = _create_full_key(
            client_as_admin,
            domains=["example.com", "api.example.com"],
            abuse_prevention={"is_toggled": True, "recaptcha_secret_key": "secret", "threshold": 0.5},
            fraud_protection=True,
        )
        assert data["domains"] == ["example.com", "api.example.com"]
        assert data["abuse_prevention"]["is_toggled"] is True
        assert data["fraud_protection"] is True

    def test_update_full_key(self, client_as_admin):
        """Create a full key, then update all fields via ?id=."""
        data = _create_full_key(
            client_as_admin,
            domains=["old.com"],
            abuse_prevention={"is_toggled": True},
            fraud_protection=True,
        )
        key_id = data["id"]
        resp = client_as_admin.post(f"/api/v1/generated-api-keys/upsert-full?id={key_id}", json={
            "name": "Updated Full Key",
            "key_value": _unique_key_value(),
            "domains": ["new.com"],
            "abuse_prevention": {"is_toggled": False},
            "fraud_protection": False,
        })
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["name"] == "Updated Full Key"
        assert updated["domains"] == ["new.com"]

    def test_create_with_domains_only(self, client_as_admin):
        """Create full key with only domains (no abuse_prevention/fraud_protection)."""
        data = _create_full_key(client_as_admin, domains=["myapp.com"])
        assert data["domains"] == ["myapp.com"]

    def test_create_with_empty_domains_array(self, client_as_admin):
        """Create full key with empty domains array and fraud_protection."""
        data = _create_full_key(client_as_admin, domains=[], fraud_protection=True)
        assert data["domains"] == []

    def test_upsert_full_key_not_found(self, client_as_admin):
        """Update with nonexistent id returns 404."""
        resp = client_as_admin.post("/api/v1/generated-api-keys/upsert-full?id=9999", json={
            "name": "test", "key_value": "test",
        })
        assert resp.status_code == 404


# ─── GET /api/v1/generated-api-keys/list ───

class TestGetAllKeys:
    """Tests for GET /api/v1/generated-api-keys/list"""

    def test_get_all_keys_returns_200(self, client_as_member):
        response = client_as_member.get("/api/v1/generated-api-keys/list")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_all_keys_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/generated-api-keys/list")
        assert response.status_code in (401, 403)

    def test_get_all_keys_contains_created_key(self, client_as_admin):
        """Create a key, list all, verify it appears."""
        created = _create_basic_key(client_as_admin)
        resp = client_as_admin.get("/api/v1/generated-api-keys/list")
        assert resp.status_code == 200
        keys = resp.json()
        assert any(k["id"] == created["id"] for k in keys)

    def test_get_all_keys_includes_full_key_fields(self, client_as_admin):
        """Create a full key, list all, verify security fields present."""
        created = _create_full_key(
            client_as_admin,
            domains=["test.com"],
            fraud_protection=True,
        )
        resp = client_as_admin.get("/api/v1/generated-api-keys/list")
        assert resp.status_code == 200
        keys = resp.json()
        match = next((k for k in keys if k["id"] == created["id"]), None)
        assert match is not None
        assert "domains" in match


# ─── GET /api/v1/generated-api-keys/get ───

class TestGetKey:
    """Tests for GET /api/v1/generated-api-keys/get"""

    def test_get_key_missing_id(self, client_as_member):
        response = client_as_member.get("/api/v1/generated-api-keys/get")
        assert response.status_code == 422

    def test_get_key_invalid_id(self, client_as_member):
        response = client_as_member.get("/api/v1/generated-api-keys/get?key_id=abc")
        assert response.status_code == 422

    def test_get_key_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/generated-api-keys/get?key_id=1")
        assert response.status_code in (401, 403)

    def test_get_key_success(self, client_as_admin):
        """Create a key, fetch by id, verify fields match."""
        created = _create_basic_key(client_as_admin)
        resp = client_as_admin.get(f"/api/v1/generated-api-keys/get?key_id={created['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == created["name"]
        assert data["key_value"] == created["key_value"]

    def test_get_key_not_found(self, client_as_admin):
        """Fetch nonexistent key returns 404."""
        resp = client_as_admin.get("/api/v1/generated-api-keys/get?key_id=9999")
        assert resp.status_code == 404


# ─── DELETE /api/v1/generated-api-keys/delete ───

class TestDeleteKey:
    """Tests for DELETE /api/v1/generated-api-keys/delete"""

    def test_delete_key_missing_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/generated-api-keys/delete")
        assert response.status_code == 422

    def test_delete_key_invalid_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/generated-api-keys/delete?key_id=abc")
        assert response.status_code == 422

    def test_delete_key_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/generated-api-keys/delete?key_id=1")
        assert response.status_code in (401, 403)

    def test_delete_key_success(self, client_as_admin):
        """Create a key, delete it, verify it's gone."""
        created = _create_basic_key(client_as_admin)
        resp = client_as_admin.delete(f"/api/v1/generated-api-keys/delete?key_id={created['id']}")
        assert resp.status_code == 200
        # Confirm deleted
        get_resp = client_as_admin.get(f"/api/v1/generated-api-keys/get?key_id={created['id']}")
        assert get_resp.status_code == 404

    def test_delete_key_not_found(self, client_as_admin):
        """Delete nonexistent key returns 404."""
        resp = client_as_admin.delete("/api/v1/generated-api-keys/delete?key_id=9999")
        assert resp.status_code == 404
