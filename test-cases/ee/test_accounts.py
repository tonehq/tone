"""Tests for Account API endpoints (EE edition).

Source: ee/api/v1/accounts.py
Integration tests — real DB, real endpoints, no mocks.
"""

import pytest
import uuid


# --- Helpers ---

def _unique_name(prefix="Account"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_account(client, **overrides):
    """Create an account and return the response JSON.

    Requires a valid model_provider_menu_id in the DB.  We fetch the first one
    from the list endpoint so the test stays self-contained.
    """
    defaults = {
        "name": _unique_name(),
        "service_type": "llm",
        "config": {},
    }
    # If caller didn't supply model_provider_menu_id, look one up
    if "model_provider_menu_id" not in overrides:
        providers = client.post("/api/v1/model-providers-menu/list", json={}).json()
        data = providers.get("data", providers) if isinstance(providers, dict) else providers
        if data:
            defaults["model_provider_menu_id"] = data[0]["id"]
        else:
            defaults["model_provider_menu_id"] = 1
    defaults.update(overrides)
    resp = client.post("/api/v1/accounts/upsert", json=defaults)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- POST /api/v1/accounts/upsert ---

class TestUpsertAccount:
    """Tests for POST /api/v1/accounts/upsert"""

    def test_create_minimal(self, client_as_admin):
        account = _create_account(client_as_admin)
        assert "id" in account
        assert "uuid" in account
        assert account["service_type"] == "llm"

    def test_create_with_description(self, client_as_admin):
        account = _create_account(client_as_admin, description="Test LLM account")
        assert account["description"] == "Test LLM account"

    def test_create_with_is_default(self, client_as_admin):
        account = _create_account(client_as_admin, is_default=True)
        assert account["is_default"] is True

    def test_create_with_tags(self, client_as_admin):
        account = _create_account(client_as_admin, tags=["production"])
        assert account["tags"] == ["production"]

    def test_update_existing(self, client_as_admin):
        account = _create_account(client_as_admin)
        new_name = _unique_name("Updated")
        resp = client_as_admin.post("/api/v1/accounts/upsert", json={
            "uuid": account["uuid"],
            "model_provider_menu_id": account["model_provider_menu_id"],
            "name": new_name,
            "service_type": account["service_type"],
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == new_name

    def test_missing_name_and_service_type(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/accounts/upsert", json={
            "model_provider_menu_id": 1,
            "name": "Test",
        })
        assert resp.status_code == 400
        assert "service_type" in resp.json()["detail"]

    def test_missing_model_provider_menu_id(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/accounts/upsert", json={
            "name": "Test Account",
            "service_type": "llm",
            "config": {},
        })
        assert resp.status_code == 400
        assert "model_provider_menu_id" in resp.json()["detail"]

    def test_model_provider_menu_not_found(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/accounts/upsert", json={
            "model_provider_menu_id": 999999,
            "name": _unique_name(),
            "service_type": "llm",
            "config": {},
        })
        assert resp.status_code == 404

    def test_empty_body(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/accounts/upsert", json={})
        assert resp.status_code == 400

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/accounts/upsert", json={
            "model_provider_menu_id": 1,
            "name": "Test",
            "service_type": "llm",
        })
        assert resp.status_code in (401, 403)

    def test_member_cannot_upsert(self, client_as_member):
        resp = client_as_member.post("/api/v1/accounts/upsert", json={
            "model_provider_menu_id": 1,
            "name": _unique_name(),
            "service_type": "llm",
        })
        assert resp.status_code in (401, 403)


# --- POST /api/v1/accounts/list ---

class TestGetAllAccounts:
    """Tests for POST /api/v1/accounts/list"""

    def test_returns_200_list(self, client_as_member):
        resp = client_as_member.post("/api/v1/accounts/list", json={})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_filter_by_service_type(self, client_as_member):
        resp = client_as_member.post("/api/v1/accounts/list", json={"service_type": "llm"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for item in data:
            assert item["service_type"] == "llm"

    def test_empty_result(self, client_as_member):
        resp = client_as_member.post("/api/v1/accounts/list", json={"service_type": "nonexistent_type"})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/accounts/list", json={})
        assert resp.status_code in (401, 403)


# --- GET /api/v1/accounts/get ---

class TestGetAccount:
    """Tests for GET /api/v1/accounts/get"""

    def test_get_existing(self, client_as_admin):
        account = _create_account(client_as_admin)
        resp = client_as_admin.get(f"/api/v1/accounts/get?account_id={account['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == account["id"]

    def test_not_found(self, client_as_member):
        resp = client_as_member.get("/api/v1/accounts/get?account_id=999999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_missing_account_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/accounts/get")
        assert resp.status_code == 422

    def test_invalid_account_id_type(self, client_as_member):
        resp = client_as_member.get("/api/v1/accounts/get?account_id=abc")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/accounts/get?account_id=1")
        assert resp.status_code in (401, 403)


# --- GET /api/v1/accounts/default ---

class TestGetDefaultAccount:
    """Tests for GET /api/v1/accounts/default"""

    def test_get_default_llm(self, client_as_member):
        resp = client_as_member.get("/api/v1/accounts/default?service_type=llm")
        # May be 200 or 404 depending on DB state
        assert resp.status_code in (200, 404)

    def test_get_default_stt(self, client_as_member):
        resp = client_as_member.get("/api/v1/accounts/default?service_type=stt")
        assert resp.status_code in (200, 404)

    def test_get_default_tts(self, client_as_member):
        resp = client_as_member.get("/api/v1/accounts/default?service_type=tts")
        assert resp.status_code in (200, 404)

    def test_missing_service_type(self, client_as_member):
        resp = client_as_member.get("/api/v1/accounts/default")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/accounts/default?service_type=llm")
        assert resp.status_code in (401, 403)


# --- DELETE /api/v1/accounts/delete ---

class TestDeleteAccount:
    """Tests for DELETE /api/v1/accounts/delete"""

    def test_delete_by_id(self, client_as_admin):
        account = _create_account(client_as_admin)
        resp = client_as_admin.delete(f"/api/v1/accounts/delete?account_id={account['id']}")
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()

    def test_delete_by_uuid(self, client_as_admin):
        account = _create_account(client_as_admin)
        resp = client_as_admin.delete(f"/api/v1/accounts/delete?uuid={account['uuid']}")
        assert resp.status_code == 200

    def test_delete_not_found(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/accounts/delete?account_id=999999")
        assert resp.status_code == 404

    def test_delete_missing_params(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/accounts/delete")
        assert resp.status_code == 400
        assert "required" in resp.json()["detail"].lower()

    def test_delete_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete("/api/v1/accounts/delete?account_id=1")
        assert resp.status_code in (401, 403)

    def test_member_cannot_delete(self, client_as_member):
        resp = client_as_member.delete("/api/v1/accounts/delete?account_id=1")
        assert resp.status_code in (401, 403)


# --- Full CRUD Flow ---

class TestAccountCRUDFlow:
    """End-to-end Create -> Read -> Update -> Delete flow."""

    def test_full_lifecycle(self, client_as_admin):
        # Create
        account = _create_account(client_as_admin, description="Lifecycle test")

        # Read
        resp = client_as_admin.get(f"/api/v1/accounts/get?account_id={account['id']}")
        assert resp.status_code == 200
        assert resp.json()["name"] == account["name"]

        # Update
        new_name = _unique_name("Updated-Lifecycle")
        resp = client_as_admin.post("/api/v1/accounts/upsert", json={
            "uuid": account["uuid"],
            "model_provider_menu_id": account["model_provider_menu_id"],
            "name": new_name,
            "service_type": account["service_type"],
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == new_name

        # Delete
        resp = client_as_admin.delete(f"/api/v1/accounts/delete?account_id={account['id']}")
        assert resp.status_code == 200

        # Verify deleted
        resp = client_as_admin.get(f"/api/v1/accounts/get?account_id={account['id']}")
        assert resp.status_code == 404
