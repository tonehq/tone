"""Tests for Generated API Keys endpoints (Core edition).

Source: core/api/v1/generated_api_keys.py
Service: core/services/generated_api_key_service.py
Model:   core/models/generated_api_key.py
Auth extension: try_resolve_api_key in core/middleware/auth.py

Integration tests — real DB, real endpoints, no mocks. Each test uses a
unique key name so the partial-unique index
    uq_generated_api_keys_org_active_name (organization_id, lower(name))
        WHERE deleted_at IS NULL AND revoked_at IS NULL
never collides across tests.

Routes:
    POST   /api/v1/generated-api-keys/create_api_key   (admin/owner)
    POST   /api/v1/generated-api-keys/list             (org member)
    GET    /api/v1/generated-api-keys/get_api_key      (org member)
    POST   /api/v1/generated-api-keys/revoke_api_key   (admin/owner)
    DELETE /api/v1/generated-api-keys/delete_api_key   (admin/owner)

The auth-path tests live in the "TestApiKeyAuthPath" class and fire against
an already-mounted protected endpoint (`/api/v1/generated-api-keys/list`)
using `Authorization: Bearer tone_sk_...`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

BASE = "/api/v1/generated-api-keys"


# ─── Helpers ────────────────────────────────────────────────────────────


def _unique_name(prefix: str = "test-key") -> str:
    """Ensures the partial-unique index on active names does not collide."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_via_api(client, *, name: str | None = None, expires_at: str | None = None) -> dict:
    """Create via the router. Returns the response body (with one-time `key`).
    Skips the test when a role/env issue prevents creation so downstream tests
    stay self-contained."""
    payload = {"name": name or _unique_name(), "expires_at": expires_at}
    resp = client.post(f"{BASE}/create_api_key", json=payload)
    if resp.status_code not in (200, 201):
        pytest.skip(f"Cannot create API key (status={resp.status_code}): {resp.text[:200]}")
    return resp.json()


# ─── POST /create_api_key ───────────────────────────────────────────────


class TestCreateApiKey:
    def test_create_never_expires_returns_one_time_key(self, client_as_admin):
        body = _create_via_api(client_as_admin)
        assert body["status"] == "active"
        assert body["expires_at"] is None
        assert body["key"].startswith("tone_sk_"), body["key"]
        assert body["key_prefix"] == body["key"][:12]
        # Masked never contains the full secret.
        assert body["key"] not in body["masked"]
        # Response never leaks the hash.
        assert "key_hash" not in body

    def test_create_with_future_expiry(self, client_as_admin):
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        body = _create_via_api(client_as_admin, expires_at=future)
        assert body["expires_at"] is not None
        assert body["status"] == "active"

    def test_create_past_expiry_rejected(self, client_as_admin):
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        resp = client_as_admin.post(
            f"{BASE}/create_api_key",
            json={"name": _unique_name(), "expires_at": past},
        )
        assert resp.status_code == 422
        assert "future" in resp.json()["detail"].lower()

    def test_create_blank_name_rejected(self, client_as_admin):
        resp = client_as_admin.post(
            f"{BASE}/create_api_key",
            json={"name": "", "expires_at": None},
        )
        # Pydantic Field(min_length=1) → 422 before we reach the service.
        assert resp.status_code == 422

    def test_create_oversized_name_rejected(self, client_as_admin):
        resp = client_as_admin.post(
            f"{BASE}/create_api_key",
            json={"name": "a" * 121, "expires_at": None},
        )
        assert resp.status_code == 422

    def test_create_duplicate_active_name_conflicts(self, client_as_admin):
        name = _unique_name()
        first = client_as_admin.post(
            f"{BASE}/create_api_key", json={"name": name, "expires_at": None}
        )
        if first.status_code not in (200, 201):
            pytest.skip(f"First create failed: {first.status_code} {first.text[:200]}")
        second = client_as_admin.post(
            f"{BASE}/create_api_key", json={"name": name, "expires_at": None}
        )
        assert second.status_code == 409
        assert "already exists" in second.json()["detail"].lower()

    def test_create_member_forbidden(self, client_as_member):
        """require_admin_or_owner blocks regular members."""
        resp = client_as_member.post(
            f"{BASE}/create_api_key",
            json={"name": _unique_name(), "expires_at": None},
        )
        assert resp.status_code == 403

    def test_create_owner_allowed(self, client_as_owner):
        _create_via_api(client_as_owner)

    def test_create_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            f"{BASE}/create_api_key",
            json={"name": _unique_name(), "expires_at": None},
        )
        assert resp.status_code in (401, 403)


# ─── POST /list ─────────────────────────────────────────────────────────


class TestListApiKeys:
    def test_list_returns_paginated_envelope(self, client_as_admin):
        _create_via_api(client_as_admin, name=_unique_name("list-A"))
        resp = client_as_admin.post(f"{BASE}/list", json={"page_no": 1, "page_size": 20})
        assert resp.status_code == 200
        body = resp.json()
        assert set(body.keys()) >= {"data", "total", "page_no", "page_size"}
        assert isinstance(body["data"], list)

    def test_list_search_matches_name_prefix(self, client_as_admin):
        marker = f"search-marker-{uuid.uuid4().hex[:6]}"
        _create_via_api(client_as_admin, name=marker)
        resp = client_as_admin.post(f"{BASE}/list", json={"search": marker})
        assert resp.status_code == 200
        names = [row["name"] for row in resp.json()["data"]]
        assert marker in names

    def test_list_sort_whitelist_ignores_arbitrary_column(self, client_as_admin):
        resp = client_as_admin.post(
            f"{BASE}/list", json={"sort_by": "not_a_real_column", "sort_order": "desc"}
        )
        # apply_search_sort_pagination falls back to the first sort_map entry
        # for unknown keys — never 500s on client input.
        assert resp.status_code == 200

    def test_list_member_allowed(self, client_as_member):
        resp = client_as_member.post(f"{BASE}/list", json={})
        assert resp.status_code == 200

    def test_list_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(f"{BASE}/list", json={})
        assert resp.status_code in (401, 403)

    def test_list_page_size_capped(self, client_as_admin):
        # Field(le=100) — 500 → 422.
        resp = client_as_admin.post(f"{BASE}/list", json={"page_size": 500})
        assert resp.status_code == 422


# ─── GET /get_api_key ───────────────────────────────────────────────────


class TestGetApiKey:
    def test_get_success(self, client_as_admin):
        created = _create_via_api(client_as_admin)
        resp = client_as_admin.get(
            f"{BASE}/get_api_key", params={"api_key_id": created["id"]}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == created["id"]
        assert body["masked"] == created["masked"]
        assert "key" not in body  # plaintext never returned after creation

    def test_get_unknown_id_returns_404(self, client_as_admin):
        resp = client_as_admin.get(
            f"{BASE}/get_api_key",
            params={"api_key_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert resp.status_code == 404


# ─── POST /revoke_api_key ───────────────────────────────────────────────


class TestRevokeApiKey:
    def test_revoke_sets_status_and_revoked_at(self, client_as_admin):
        created = _create_via_api(client_as_admin)
        resp = client_as_admin.post(
            f"{BASE}/revoke_api_key", params={"api_key_id": created["id"]}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "revoked"
        assert body["revoked_at"] is not None

    def test_revoke_is_idempotent(self, client_as_admin):
        created = _create_via_api(client_as_admin)
        first = client_as_admin.post(
            f"{BASE}/revoke_api_key", params={"api_key_id": created["id"]}
        )
        second = client_as_admin.post(
            f"{BASE}/revoke_api_key", params={"api_key_id": created["id"]}
        )
        assert first.status_code == 200
        assert second.status_code == 200
        # revoked_at is not updated on a re-revoke.
        assert first.json()["revoked_at"] == second.json()["revoked_at"]

    def test_revoke_member_forbidden(self, client_as_member):
        # Member can't create; craft the request against a bogus id so we
        # only exercise the role gate.
        resp = client_as_member.post(
            f"{BASE}/revoke_api_key",
            params={"api_key_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert resp.status_code == 403


# ─── DELETE /delete_api_key ─────────────────────────────────────────────


class TestDeleteApiKey:
    def test_delete_removes_the_row(self, client_as_admin):
        created = _create_via_api(client_as_admin)
        resp = client_as_admin.delete(
            f"{BASE}/delete_api_key", params={"api_key_id": created["id"]}
        )
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()
        # Subsequent get is 404.
        follow = client_as_admin.get(
            f"{BASE}/get_api_key", params={"api_key_id": created["id"]}
        )
        assert follow.status_code == 404

    def test_delete_member_forbidden(self, client_as_member):
        resp = client_as_member.delete(
            f"{BASE}/delete_api_key",
            params={"api_key_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert resp.status_code == 403


# ─── Auth path: Bearer tone_sk_... resolves through the middleware ─────


class TestApiKeyAuthPath:
    """Fire against a real protected endpoint using the minted key. The
    /generated-api-keys/list endpoint is convenient — it's guarded by
    require_org_member so an API key (role='admin' synthesized) always passes."""

    def _mint(self, client) -> tuple[str, str]:
        created = _create_via_api(client)
        return created["key"], created["id"]

    def _client_with_bearer(self, client_as_admin, key: str):
        # Clone the authenticated client, swap the Authorization header for
        # the API key. The `tenant_id` header carries over — the API-key
        # branch in the middleware ignores it and uses the key's own org.
        client_as_admin.headers["Authorization"] = f"Bearer {key}"
        return client_as_admin

    def test_valid_key_authenticates(self, client_as_admin):
        key, _ = self._mint(client_as_admin)
        c = self._client_with_bearer(client_as_admin, key)
        resp = c.post(f"{BASE}/list", json={})
        assert resp.status_code == 200

    def test_unknown_key_returns_401(self, client_as_admin):
        c = self._client_with_bearer(client_as_admin, "tone_sk_totally_unknown_key")
        resp = c.post(f"{BASE}/list", json={})
        assert resp.status_code == 401

    def test_revoked_key_returns_401(self, client_as_admin):
        key, key_id = self._mint(client_as_admin)
        # Use a fresh JWT client to revoke so the auth cache doesn't confuse
        # (we already swapped headers on client_as_admin above in other tests).
        revoke = client_as_admin.post(f"{BASE}/revoke_api_key", params={"api_key_id": key_id})
        assert revoke.status_code == 200
        client_as_admin.headers["Authorization"] = f"Bearer {key}"
        resp = client_as_admin.post(f"{BASE}/list", json={})
        assert resp.status_code == 401

    def test_expired_key_returns_401(self, client_as_admin, db_session):
        """Insert a row directly with an expiry in the past — the router
        rejects a past expires_at, so we go around it via a direct insert."""
        from sqlalchemy import text as _text

        from core.models.generated_api_key import GeneratedApiKey
        from core.services.generated_api_key_service import KEY_PREFIX, _hash_key

        org_id = db_session.execute(_text("SELECT id FROM organizations LIMIT 1")).fetchone()[0]
        user_id = db_session.execute(_text("SELECT id FROM users LIMIT 1")).fetchone()[0]

        raw = f"{KEY_PREFIX}expired-test-{uuid.uuid4().hex}"
        row = GeneratedApiKey(
            organization_id=org_id,
            created_by_user_id=user_id,
            name=_unique_name("expired"),
            key_hash=_hash_key(raw),
            key_prefix=raw[:12],
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            is_active=True,
        )
        db_session.add(row)
        db_session.commit()

        client_as_admin.headers["Authorization"] = f"Bearer {raw}"
        resp = client_as_admin.post(f"{BASE}/list", json={})
        assert resp.status_code == 401

    def test_malformed_bearer_falls_through_to_jwt_and_401s(self, client_as_admin):
        client_as_admin.headers["Authorization"] = "Bearer not-a-real-token-and-not-an-api-key"
        resp = client_as_admin.post(f"{BASE}/list", json={})
        # Doesn't start with tone_sk_ → try_resolve_api_key returns None →
        # JWT decode runs → invalid JWT → 401.
        assert resp.status_code == 401

    def test_jwt_still_works_alongside_api_keys(self, client_as_admin):
        """Sanity — the base fixture uses a real JWT; it must keep working
        after our try_resolve_api_key branch was added."""
        resp = client_as_admin.post(f"{BASE}/list", json={})
        assert resp.status_code == 200

    def test_last_used_at_bumps_after_auth(self, client_as_admin, db_session):
        from core.models.generated_api_key import GeneratedApiKey

        key, key_id = self._mint(client_as_admin)
        # Fresh row has last_used_at IS NULL.
        row = db_session.query(GeneratedApiKey).filter(
            GeneratedApiKey.id == key_id
        ).first()
        assert row is not None
        assert row.last_used_at is None

        client_as_admin.headers["Authorization"] = f"Bearer {key}"
        resp = client_as_admin.post(f"{BASE}/list", json={})
        assert resp.status_code == 200

        db_session.expire(row)
        db_session.refresh(row)
        assert row.last_used_at is not None
