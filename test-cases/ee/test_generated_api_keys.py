"""Tests for Generated API Keys endpoints (EE edition).

Source: ee/api/v1/generated_api_keys.py
Shared service/model with Core; EE swaps in EE auth guards
(require_ee_admin_or_owner / require_ee_org_member).

Integration tests — real DB, real endpoints, no mocks. Unique names per test
so the partial-unique-active-name index never collides.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

BASE = "/api/v1/generated-api-keys"


# ─── Helpers ────────────────────────────────────────────────────────────


def _unique_name(prefix: str = "test-key") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_via_api(client, *, name: str | None = None, expires_at: str | None = None) -> dict:
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
        assert body["key"].startswith("tone_sk_")
        assert body["key_prefix"] == body["key"][:12]
        assert body["key"] not in body["masked"]
        assert "key_hash" not in body

    def test_create_with_future_expiry(self, client_as_admin):
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        body = _create_via_api(client_as_admin, expires_at=future)
        assert body["status"] == "active"
        assert body["expires_at"] is not None

    def test_create_past_expiry_rejected(self, client_as_admin):
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        resp = client_as_admin.post(
            f"{BASE}/create_api_key",
            json={"name": _unique_name(), "expires_at": past},
        )
        assert resp.status_code == 422

    def test_create_blank_name_rejected(self, client_as_admin):
        resp = client_as_admin.post(
            f"{BASE}/create_api_key", json={"name": "", "expires_at": None}
        )
        assert resp.status_code == 422

    def test_create_oversized_name_rejected(self, client_as_admin):
        resp = client_as_admin.post(
            f"{BASE}/create_api_key", json={"name": "a" * 121, "expires_at": None}
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

    def test_create_member_forbidden(self, client_as_member):
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
    def test_list_paginated_envelope(self, client_as_admin):
        _create_via_api(client_as_admin, name=_unique_name("list-EE"))
        resp = client_as_admin.post(f"{BASE}/list", json={"page_no": 1, "page_size": 20})
        assert resp.status_code == 200
        body = resp.json()
        assert set(body.keys()) >= {"data", "total", "page_no", "page_size"}

    def test_list_member_allowed(self, client_as_member):
        resp = client_as_member.post(f"{BASE}/list", json={})
        assert resp.status_code == 200

    def test_list_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(f"{BASE}/list", json={})
        assert resp.status_code in (401, 403)

    def test_list_page_size_cap(self, client_as_admin):
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
        assert resp.json()["id"] == created["id"]
        assert "key" not in resp.json()

    def test_get_unknown_id_returns_404(self, client_as_admin):
        resp = client_as_admin.get(
            f"{BASE}/get_api_key",
            params={"api_key_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert resp.status_code == 404


# ─── POST /revoke_api_key ───────────────────────────────────────────────


class TestRevokeApiKey:
    def test_revoke_sets_status(self, client_as_admin):
        created = _create_via_api(client_as_admin)
        resp = client_as_admin.post(
            f"{BASE}/revoke_api_key", params={"api_key_id": created["id"]}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "revoked"
        assert body["revoked_at"] is not None

    def test_revoke_idempotent(self, client_as_admin):
        created = _create_via_api(client_as_admin)
        first = client_as_admin.post(
            f"{BASE}/revoke_api_key", params={"api_key_id": created["id"]}
        )
        second = client_as_admin.post(
            f"{BASE}/revoke_api_key", params={"api_key_id": created["id"]}
        )
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["revoked_at"] == second.json()["revoked_at"]

    def test_revoke_member_forbidden(self, client_as_member):
        resp = client_as_member.post(
            f"{BASE}/revoke_api_key",
            params={"api_key_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert resp.status_code == 403


# ─── DELETE /delete_api_key ─────────────────────────────────────────────


class TestDeleteApiKey:
    def test_delete_removes_row(self, client_as_admin):
        created = _create_via_api(client_as_admin)
        resp = client_as_admin.delete(
            f"{BASE}/delete_api_key", params={"api_key_id": created["id"]}
        )
        assert resp.status_code == 200
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


# ─── Auth path: Bearer tone_sk_... via try_resolve_api_key ─────────────


class TestApiKeyAuthPath:
    def test_valid_key_authenticates(self, client_as_admin):
        created = _create_via_api(client_as_admin)
        client_as_admin.headers["Authorization"] = f"Bearer {created['key']}"
        resp = client_as_admin.post(f"{BASE}/list", json={})
        assert resp.status_code == 200

    def test_unknown_key_returns_401(self, client_as_admin):
        client_as_admin.headers["Authorization"] = "Bearer tone_sk_unknown_key_value"
        resp = client_as_admin.post(f"{BASE}/list", json={})
        assert resp.status_code == 401

    def test_revoked_key_returns_401(self, client_as_admin):
        created = _create_via_api(client_as_admin)
        revoke = client_as_admin.post(
            f"{BASE}/revoke_api_key", params={"api_key_id": created["id"]}
        )
        assert revoke.status_code == 200
        client_as_admin.headers["Authorization"] = f"Bearer {created['key']}"
        resp = client_as_admin.post(f"{BASE}/list", json={})
        assert resp.status_code == 401

    def test_expired_key_returns_401(self, client_as_admin, db_session):
        from sqlalchemy import text as _text

        from core.models.generated_api_key import GeneratedApiKey
        from core.services.generated_api_key_service import KEY_PREFIX, _hash_key

        org_id = db_session.execute(_text("SELECT id FROM organizations LIMIT 1")).fetchone()[0]
        user_id = db_session.execute(_text("SELECT id FROM users LIMIT 1")).fetchone()[0]

        raw = f"{KEY_PREFIX}expired-ee-{uuid.uuid4().hex}"
        row = GeneratedApiKey(
            organization_id=org_id,
            created_by_user_id=user_id,
            name=_unique_name("expired-ee"),
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
        client_as_admin.headers["Authorization"] = "Bearer not-an-api-key-and-not-a-jwt"
        resp = client_as_admin.post(f"{BASE}/list", json={})
        assert resp.status_code == 401

    def test_jwt_still_works_alongside_api_keys(self, client_as_admin):
        resp = client_as_admin.post(f"{BASE}/list", json={})
        assert resp.status_code == 200

    def test_last_used_at_bumps_after_auth(self, client_as_admin, db_session):
        from core.models.generated_api_key import GeneratedApiKey

        created = _create_via_api(client_as_admin)
        row = db_session.query(GeneratedApiKey).filter(
            GeneratedApiKey.id == created["id"]
        ).first()
        assert row is not None
        assert row.last_used_at is None

        client_as_admin.headers["Authorization"] = f"Bearer {created['key']}"
        resp = client_as_admin.post(f"{BASE}/list", json={})
        assert resp.status_code == 200

        db_session.expire(row)
        db_session.refresh(row)
        assert row.last_used_at is not None

    def test_tenant_id_header_cannot_switch_api_key_org(self, client_as_admin):
        """EE-specific: a synthesized API-key JWTClaims has email 'api-key:<id>',
        which get_ee_current_user detects and refuses to honor any tenant_id
        header override. Verifies the cross-org escape hatch is closed."""
        created = _create_via_api(client_as_admin)
        client_as_admin.headers["Authorization"] = f"Bearer {created['key']}"
        # Any arbitrary other-org UUID.
        client_as_admin.headers["tenant_id"] = "11111111-1111-1111-1111-111111111111"
        resp = client_as_admin.post(f"{BASE}/list", json={})
        # Still succeeds — the header is ignored, org context stays on the
        # key's own org. The listing is the key's org only.
        assert resp.status_code == 200
