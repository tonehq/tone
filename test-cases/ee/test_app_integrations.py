"""Tests for App Integrations API endpoints (EE edition).

Source: ee/api/v1/app_integrations.py
Service: core/services/app_integration_service.py (shared with Core)
Integration tests — real DB, real endpoints, no mocks.

EE auth guard is require_ee_org_member for every route — any authenticated
EE org member can manage app integrations. The Pydantic schemas, service,
and response formatter are imported from core — no schema duplication.

Routes:
    POST   /api/v1/app-integration/create_app_integration   (ee org member)
    PUT    /api/v1/app-integration/update_app_integration   (ee org member)
    GET    /api/v1/app-integration/get_app_integration      (ee org member)
    POST   /api/v1/app-integration/list                     (ee org member)
    DELETE /api/v1/app-integration/delete_app_integration   (ee org member)
"""

import uuid

import pytest


# ─── Helpers ────────────────────────────────────────────────────────────


def _unique_slug(prefix: str = "test_int_ee") -> str:
    """Build a unique, schema-valid slug (lowercase, 2–64 chars, [a-z0-9_-])."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _minimal_create_payload(**overrides):
    payload = {
        "slug": _unique_slug(),
        "display_name": "Test Integration (EE)",
        "auth_type": "oauth",
    }
    payload.update(overrides)
    return payload


def _create_integration(client, **overrides):
    payload = _minimal_create_payload(**overrides)
    resp = client.post("/api/v1/app-integration/create_app_integration", json=payload)
    if resp.status_code not in (200, 201):
        pytest.skip(
            f"Cannot create integration (status={resp.status_code}): {resp.text[:200]}"
        )
    return resp.json()


# ─── POST /api/v1/app-integration/create_app_integration ───────────────


class TestCreateAppIntegration:
    """Tests for POST /api/v1/app-integration/create_app_integration (EE)."""

    def test_create_minimal_success(self, client_as_admin):
        payload = _minimal_create_payload()
        resp = client_as_admin.post(
            "/api/v1/app-integration/create_app_integration", json=payload
        )
        assert resp.status_code in (200, 201)
        body = resp.json()
        assert body["slug"] == payload["slug"]
        assert body["display_name"] == payload["display_name"]
        assert body["auth_type"] == payload["auth_type"]
        assert body["is_default"] is False
        assert body["is_enabled"] is True
        assert body["pkce_required"] is True
        assert body["sort_order"] == 100
        assert "client_secret" not in body

    def test_create_with_full_payload(self, client_as_admin):
        payload = _minimal_create_payload(
            display_name="Full Payload Integration (EE)",
            description="A test integration with every field set.",
            category="productivity",
            icon_url="https://example.com/icon.png",
            auth_type="oauth",
            auth_url="https://accounts.example.com/oauth2/v2/auth",
            token_url="https://oauth2.example.com/token",
            userinfo_url="https://example.com/userinfo",
            scopes=["read", "write"],
            extra_auth_params={"access_type": "offline"},
            client_id="env_client_id_value",
            client_secret="env_client_secret_value",
            pkce_required=False,
            is_enabled=True,
            sort_order=42,
        )
        resp = client_as_admin.post(
            "/api/v1/app-integration/create_app_integration", json=payload
        )
        assert resp.status_code in (200, 201)
        body = resp.json()
        assert body["scopes"] == ["read", "write"]
        assert body["extra_auth_params"] == {"access_type": "offline"}
        assert body["pkce_required"] is False
        assert body["sort_order"] == 42
        assert "client_id" not in body
        assert "client_secret" not in body
        assert body["has_credentials"] is True

    def test_create_owner_can_create(self, client_as_owner):
        resp = client_as_owner.post(
            "/api/v1/app-integration/create_app_integration",
            json=_minimal_create_payload(),
        )
        assert resp.status_code in (200, 201)

    def test_create_member_allowed(self, client_as_member):
        """Any authenticated EE org member can create — role gate has been lifted."""
        resp = client_as_member.post(
            "/api/v1/app-integration/create_app_integration",
            json=_minimal_create_payload(),
        )
        assert resp.status_code in (200, 201)

    def test_create_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/app-integration/create_app_integration",
            json=_minimal_create_payload(),
        )
        assert resp.status_code in (401, 403)

    def test_create_missing_slug(self, client_as_admin):
        payload = _minimal_create_payload()
        payload.pop("slug")
        resp = client_as_admin.post(
            "/api/v1/app-integration/create_app_integration", json=payload
        )
        assert resp.status_code == 422

    def test_create_missing_display_name(self, client_as_admin):
        payload = _minimal_create_payload()
        payload.pop("display_name")
        resp = client_as_admin.post(
            "/api/v1/app-integration/create_app_integration", json=payload
        )
        assert resp.status_code == 422

    def test_create_missing_auth_type(self, client_as_admin):
        payload = _minimal_create_payload()
        payload.pop("auth_type")
        resp = client_as_admin.post(
            "/api/v1/app-integration/create_app_integration", json=payload
        )
        assert resp.status_code == 422

    def test_create_invalid_slug_pattern(self, client_as_admin):
        payload = _minimal_create_payload(slug="bad slug!")
        resp = client_as_admin.post(
            "/api/v1/app-integration/create_app_integration", json=payload
        )
        assert resp.status_code == 400
        assert "slug" in resp.json()["detail"].lower()

    def test_create_invalid_slug_too_short(self, client_as_admin):
        payload = _minimal_create_payload(slug="a")
        resp = client_as_admin.post(
            "/api/v1/app-integration/create_app_integration", json=payload
        )
        assert resp.status_code == 422

    def test_create_invalid_slug_too_long(self, client_as_admin):
        payload = _minimal_create_payload(slug="a" * 65)
        resp = client_as_admin.post(
            "/api/v1/app-integration/create_app_integration", json=payload
        )
        assert resp.status_code == 422

    def test_create_invalid_auth_type(self, client_as_admin):
        payload = _minimal_create_payload(auth_type="totally_made_up")
        resp = client_as_admin.post(
            "/api/v1/app-integration/create_app_integration", json=payload
        )
        assert resp.status_code == 400
        assert "auth_type" in resp.json()["detail"].lower()

    def test_create_display_name_too_long(self, client_as_admin):
        payload = _minimal_create_payload(display_name="x" * 121)
        resp = client_as_admin.post(
            "/api/v1/app-integration/create_app_integration", json=payload
        )
        assert resp.status_code in (400, 422)

    def test_create_scopes_wrong_type(self, client_as_admin):
        payload = _minimal_create_payload(scopes="read write")
        resp = client_as_admin.post(
            "/api/v1/app-integration/create_app_integration", json=payload
        )
        assert resp.status_code in (400, 422)

    def test_create_extra_auth_params_wrong_type(self, client_as_admin):
        payload = _minimal_create_payload(extra_auth_params=["not", "a", "dict"])
        resp = client_as_admin.post(
            "/api/v1/app-integration/create_app_integration", json=payload
        )
        assert resp.status_code in (400, 422)

    def test_create_duplicate_slug_conflict(self, client_as_admin):
        slug = _unique_slug("dup")
        first = client_as_admin.post(
            "/api/v1/app-integration/create_app_integration",
            json=_minimal_create_payload(slug=slug),
        )
        assert first.status_code in (200, 201)
        second = client_as_admin.post(
            "/api/v1/app-integration/create_app_integration",
            json=_minimal_create_payload(slug=slug, display_name="Other Name"),
        )
        assert second.status_code == 409
        assert slug in second.json()["detail"]

    def test_create_cannot_force_is_default(self, client_as_admin):
        payload = _minimal_create_payload()
        payload["is_default"] = True
        resp = client_as_admin.post(
            "/api/v1/app-integration/create_app_integration", json=payload
        )
        assert resp.status_code in (200, 201)
        assert resp.json()["is_default"] is False

    def test_create_auth_type_api_key(self, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/app-integration/create_app_integration",
            json=_minimal_create_payload(auth_type="api_key"),
        )
        assert resp.status_code in (200, 201)
        assert resp.json()["auth_type"] == "api_key"

    def test_create_auth_type_bearer_token(self, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/app-integration/create_app_integration",
            json=_minimal_create_payload(auth_type="bearer_token"),
        )
        assert resp.status_code in (200, 201)
        assert resp.json()["auth_type"] == "bearer_token"

    def test_create_auth_type_none(self, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/app-integration/create_app_integration",
            json=_minimal_create_payload(auth_type="none"),
        )
        assert resp.status_code in (200, 201)
        assert resp.json()["auth_type"] == "none"


# ─── GET /api/v1/app-integration/get_app_integration ────────────────────


class TestGetAppIntegration:
    """Tests for GET /api/v1/app-integration/get_app_integration (EE)."""

    def test_get_success(self, client_as_admin):
        created = _create_integration(client_as_admin)
        resp = client_as_admin.get(
            "/api/v1/app-integration/get_app_integration",
            params={"id": created["id"]},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]
        assert resp.json()["slug"] == created["slug"]

    def test_get_as_member(self, client_as_admin, client_as_member):
        """Member can read — endpoint is gated by require_ee_org_member."""
        created = _create_integration(client_as_admin)
        resp = client_as_member.get(
            "/api/v1/app-integration/get_app_integration",
            params={"id": created["id"]},
        )
        assert resp.status_code in (200, 404)

    def test_get_not_found(self, client_as_admin):
        resp = client_as_admin.get(
            "/api/v1/app-integration/get_app_integration",
            params={"id": str(uuid.uuid4())},
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_get_invalid_uuid(self, client_as_admin):
        resp = client_as_admin.get(
            "/api/v1/app-integration/get_app_integration",
            params={"id": "not-a-uuid"},
        )
        assert resp.status_code == 422

    def test_get_missing_id(self, client_as_admin):
        resp = client_as_admin.get("/api/v1/app-integration/get_app_integration")
        assert resp.status_code == 422

    def test_get_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/app-integration/get_app_integration",
            params={"id": str(uuid.uuid4())},
        )
        assert resp.status_code in (401, 403)

    def test_get_response_has_no_secrets(self, client_as_admin):
        created = _create_integration(client_as_admin, client_secret="super_secret_value")
        resp = client_as_admin.get(
            "/api/v1/app-integration/get_app_integration",
            params={"id": created["id"]},
        )
        assert resp.status_code == 200
        body = resp.json()
        for forbidden in ("client_id", "client_secret", "encrypted_credentials"):
            assert forbidden not in body


# ─── POST /api/v1/app-integration/list ──────────────────────────────────


class TestListAppIntegrations:
    """Tests for POST /api/v1/app-integration/list (EE)."""

    def test_list_empty_body(self, client_as_member):
        resp = client_as_member.post("/api/v1/app-integration/list", json={})
        assert resp.status_code == 200
        body = resp.json()
        assert set(body.keys()) >= {"items", "total", "page", "page_size"}
        assert isinstance(body["items"], list)
        assert isinstance(body["total"], int)

    def test_list_with_search(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/app-integration/list", json={"search": "google"}
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            haystack = " ".join(
                str(item.get(k) or "") for k in ("slug", "display_name", "description")
            ).lower()
            assert "google" in haystack

    def test_list_with_category_filter(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/app-integration/list", json={"category": "google"}
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["category"] == "google"

    def test_list_with_auth_type_filter(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/app-integration/list", json={"auth_type": "oauth"}
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["auth_type"] == "oauth"

    def test_list_with_is_enabled_true(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/app-integration/list", json={"is_enabled": True}
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["is_enabled"] is True

    def test_list_with_is_enabled_string_true(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/app-integration/list", json={"is_enabled": "true"}
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["is_enabled"] is True

    def test_list_with_is_default_filter(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/app-integration/list", json={"is_default": True}
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["is_default"] is True

    def test_list_with_pagination(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/app-integration/list", json={"page": 1, "page_size": 1}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 1
        assert body["page_size"] == 1
        assert len(body["items"]) <= 1

    def test_list_with_explicit_sort(self, client_as_member):
        """Compares case-insensitively because Postgres collation handling can
        diverge from Python's lexicographic ``sorted()`` on mixed-case names."""
        resp = client_as_member.post(
            "/api/v1/app-integration/list",
            json={"sort_by": "display_name", "sort_order": "desc"},
        )
        assert resp.status_code == 200
        names_lower = [i["display_name"].lower() for i in resp.json()["items"]]
        assert names_lower == sorted(names_lower, reverse=True)

    def test_list_with_legacy_sort_string(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/app-integration/list", json={"sort": "-display_name"}
        )
        assert resp.status_code == 200

    def test_list_invalid_sort_by_falls_back(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/app-integration/list",
            json={"sort_by": "evil_column; DROP TABLE", "sort_order": "asc"},
        )
        assert resp.status_code == 200

    def test_list_combined_filters_and_search(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/app-integration/list",
            json={"search": "g", "auth_type": "oauth", "is_enabled": True},
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["auth_type"] == "oauth"
            assert item["is_enabled"] is True

    def test_list_no_match_returns_empty(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/app-integration/list",
            json={"search": f"zzz_no_such_integration_{uuid.uuid4().hex[:6]}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_list_as_admin(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/app-integration/list", json={})
        assert resp.status_code == 200

    def test_list_as_owner(self, client_as_owner):
        resp = client_as_owner.post("/api/v1/app-integration/list", json={})
        assert resp.status_code == 200

    def test_list_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/app-integration/list", json={})
        assert resp.status_code in (401, 403)


# ─── PUT /api/v1/app-integration/update_app_integration ─────────────────


class TestUpdateAppIntegration:
    """Tests for PUT /api/v1/app-integration/update_app_integration (EE)."""

    def test_update_display_name(self, client_as_admin):
        created = _create_integration(client_as_admin)
        resp = client_as_admin.put(
            "/api/v1/app-integration/update_app_integration",
            params={"id": created["id"]},
            json={"display_name": "Renamed Integration (EE)"},
        )
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Renamed Integration (EE)"
        assert resp.json()["slug"] == created["slug"]

    def test_update_multiple_fields(self, client_as_admin):
        created = _create_integration(client_as_admin)
        resp = client_as_admin.put(
            "/api/v1/app-integration/update_app_integration",
            params={"id": created["id"]},
            json={
                "description": "Updated description",
                "category": "crm",
                "scopes": ["scope.a", "scope.b"],
                "extra_auth_params": {"prompt": "consent"},
                "sort_order": 99,
                "is_enabled": False,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["description"] == "Updated description"
        assert body["category"] == "crm"
        assert body["scopes"] == ["scope.a", "scope.b"]
        assert body["extra_auth_params"] == {"prompt": "consent"}
        assert body["sort_order"] == 99
        assert body["is_enabled"] is False

    def test_update_credentials_merges_into_blob(self, client_as_admin):
        created = _create_integration(client_as_admin)
        assert created["has_credentials"] is False
        resp = client_as_admin.put(
            "/api/v1/app-integration/update_app_integration",
            params={"id": created["id"]},
            json={"client_id": "ci_value", "client_secret": "cs_value"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["has_credentials"] is True
        assert "client_secret" not in body
        assert "client_id" not in body

    def test_update_slug_to_new_unique(self, client_as_admin):
        created = _create_integration(client_as_admin)
        new_slug = _unique_slug("renamed")
        resp = client_as_admin.put(
            "/api/v1/app-integration/update_app_integration",
            params={"id": created["id"]},
            json={"slug": new_slug},
        )
        assert resp.status_code == 200
        assert resp.json()["slug"] == new_slug

    def test_update_slug_conflict(self, client_as_admin):
        a = _create_integration(client_as_admin)
        b = _create_integration(client_as_admin)
        resp = client_as_admin.put(
            "/api/v1/app-integration/update_app_integration",
            params={"id": b["id"]},
            json={"slug": a["slug"]},
        )
        assert resp.status_code == 409
        assert a["slug"] in resp.json()["detail"]

    def test_update_invalid_auth_type(self, client_as_admin):
        created = _create_integration(client_as_admin)
        resp = client_as_admin.put(
            "/api/v1/app-integration/update_app_integration",
            params={"id": created["id"]},
            json={"auth_type": "bogus"},
        )
        assert resp.status_code == 400
        assert "auth_type" in resp.json()["detail"].lower()

    def test_update_invalid_slug_pattern(self, client_as_admin):
        created = _create_integration(client_as_admin)
        resp = client_as_admin.put(
            "/api/v1/app-integration/update_app_integration",
            params={"id": created["id"]},
            json={"slug": "BAD SLUG!!!"},
        )
        assert resp.status_code == 400
        assert "slug" in resp.json()["detail"].lower()

    def test_update_empty_display_name(self, client_as_admin):
        created = _create_integration(client_as_admin)
        resp = client_as_admin.put(
            "/api/v1/app-integration/update_app_integration",
            params={"id": created["id"]},
            json={"display_name": "   "},
        )
        assert resp.status_code == 400
        assert "display_name" in resp.json()["detail"].lower()

    def test_update_not_found(self, client_as_admin):
        resp = client_as_admin.put(
            "/api/v1/app-integration/update_app_integration",
            params={"id": str(uuid.uuid4())},
            json={"display_name": "Whatever"},
        )
        assert resp.status_code == 404

    def test_update_missing_id(self, client_as_admin):
        resp = client_as_admin.put(
            "/api/v1/app-integration/update_app_integration",
            json={"display_name": "X"},
        )
        assert resp.status_code == 422

    def test_update_invalid_uuid(self, client_as_admin):
        resp = client_as_admin.put(
            "/api/v1/app-integration/update_app_integration",
            params={"id": "not-a-uuid"},
            json={"display_name": "X"},
        )
        assert resp.status_code == 422

    def test_update_empty_body_is_noop_success(self, client_as_admin):
        created = _create_integration(client_as_admin)
        resp = client_as_admin.put(
            "/api/v1/app-integration/update_app_integration",
            params={"id": created["id"]},
            json={},
        )
        assert resp.status_code == 200
        assert resp.json()["slug"] == created["slug"]

    def test_update_member_allowed(self, client_as_admin, client_as_member):
        """Any authenticated EE org member can update — role gate has been lifted."""
        created = _create_integration(client_as_admin)
        resp = client_as_member.put(
            "/api/v1/app-integration/update_app_integration",
            params={"id": created["id"]},
            json={"display_name": "Member Updated"},
        )
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Member Updated"

    def test_update_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.put(
            "/api/v1/app-integration/update_app_integration",
            params={"id": str(uuid.uuid4())},
            json={"display_name": "X"},
        )
        assert resp.status_code in (401, 403)


# ─── DELETE /api/v1/app-integration/delete_app_integration ─────────────


class TestDeleteAppIntegration:
    """Tests for DELETE /api/v1/app-integration/delete_app_integration (EE)."""

    def test_delete_success(self, client_as_admin):
        created = _create_integration(client_as_admin)
        resp = client_as_admin.delete(
            "/api/v1/app-integration/delete_app_integration",
            params={"id": created["id"]},
        )
        assert resp.status_code == 200
        assert "deleted" in resp.json()["detail"].lower()

        follow_up = client_as_admin.get(
            "/api/v1/app-integration/get_app_integration",
            params={"id": created["id"]},
        )
        assert follow_up.status_code == 404

    def test_delete_default_integration_forbidden(self, client_as_admin):
        listing = client_as_admin.post(
            "/api/v1/app-integration/list",
            json={"is_default": True, "page_size": 1},
        )
        assert listing.status_code == 200
        items = listing.json()["items"]
        if not items:
            pytest.skip("No default integrations seeded in this DB.")
        default_id = items[0]["id"]
        resp = client_as_admin.delete(
            "/api/v1/app-integration/delete_app_integration",
            params={"id": default_id},
        )
        assert resp.status_code == 400
        assert "default" in resp.json()["detail"].lower()

    def test_delete_not_found(self, client_as_admin):
        resp = client_as_admin.delete(
            "/api/v1/app-integration/delete_app_integration",
            params={"id": str(uuid.uuid4())},
        )
        assert resp.status_code == 404

    def test_delete_missing_id(self, client_as_admin):
        resp = client_as_admin.delete(
            "/api/v1/app-integration/delete_app_integration"
        )
        assert resp.status_code == 422

    def test_delete_invalid_uuid(self, client_as_admin):
        resp = client_as_admin.delete(
            "/api/v1/app-integration/delete_app_integration",
            params={"id": "not-a-uuid"},
        )
        assert resp.status_code == 422

    def test_delete_member_allowed(self, client_as_admin, client_as_member):
        """Any authenticated EE org member can delete — role gate has been lifted."""
        created = _create_integration(client_as_admin)
        resp = client_as_member.delete(
            "/api/v1/app-integration/delete_app_integration",
            params={"id": created["id"]},
        )
        assert resp.status_code == 200

    def test_delete_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete(
            "/api/v1/app-integration/delete_app_integration",
            params={"id": str(uuid.uuid4())},
        )
        assert resp.status_code in (401, 403)

    def test_delete_owner_can_delete(self, client_as_owner):
        created = _create_integration(client_as_owner)
        resp = client_as_owner.delete(
            "/api/v1/app-integration/delete_app_integration",
            params={"id": created["id"]},
        )
        assert resp.status_code == 200
