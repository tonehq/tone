"""Unit tests for the EE tenant-header (org-switch) authorization guard.

Source: ee/middleware/auth.py :: get_ee_current_user

The ``tenant_id`` request header lets a client hint which org to act as. It is
honored ONLY when the caller is a verified member of that org — otherwise a
forged header would let one tenant act on another's data (IDOR). The membership
lookup also supplies the correct per-org role so downstream role guards evaluate
against the switched org. These tests pin that guard so it can't be silently
weakened back to the old unconditional ``claims.org_id = tenant_id``.

Pure/fast — the DB is mocked (shared ``mock_db`` fixture), no TestClient.
"""

import os
import sys
import time
from types import SimpleNamespace
from uuid import uuid4

# The ``test-cases/ee`` test package shadows the real repo-root ``ee`` package
# on ``sys.path`` under pytest, so ``import ee`` would otherwise resolve to the
# test package (which has no ``middleware`` submodule). Prepend the repo root and
# drop any shadowed ``ee`` entry so the real EE package wins. (The root conftest
# already does the same ``sys.path.insert`` for its own imports.)
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if sys.path and sys.path[0] != _REPO_ROOT:
    sys.path.insert(0, _REPO_ROOT)
if getattr(sys.modules.get("ee"), "__file__", "").startswith(
    os.path.join(_REPO_ROOT, "test-cases")
):
    sys.modules.pop("ee", None)

from core.middleware.auth import JWTClaims
from ee.middleware.auth import get_ee_current_user


ORG_TOKEN = str(uuid4())  # org baked into the access token
ORG_OTHER = str(uuid4())  # different org requested via the tenant_id header


def _claims(org_id: str, role: str = "member") -> JWTClaims:
    now = int(time.time())
    return JWTClaims(
        user_id=str(uuid4()),
        org_id=org_id,
        role=role,
        email="user@example.com",
        iat=now,
        exp=now + 3600,
    )


class TestTenantHeaderGuard:
    def test_forged_tenant_id_ignored_when_not_a_member(self, mock_db):
        # mock_db.first() returns None → caller is NOT a member of ORG_OTHER.
        claims = _claims(ORG_TOKEN, role="member")
        result = get_ee_current_user(claims=claims, tenant_id=ORG_OTHER, db=mock_db)
        # Org/role stay pinned to the token — the forged header is not trusted.
        assert result.org_id == ORG_TOKEN
        assert result.role == "member"

    def test_valid_switch_adopts_target_org_and_role(self, mock_db):
        # Caller IS a member of ORG_OTHER, with a different (per-org) role.
        mock_db.first.return_value = SimpleNamespace(role="admin")
        claims = _claims(ORG_TOKEN, role="member")
        result = get_ee_current_user(claims=claims, tenant_id=ORG_OTHER, db=mock_db)
        assert result.org_id == ORG_OTHER
        assert result.role == "admin"

    def test_no_membership_lookup_when_header_matches_token_org(self, mock_db):
        # tenant_id == token org → no query, claims returned unchanged.
        claims = _claims(ORG_TOKEN, role="owner")
        result = get_ee_current_user(claims=claims, tenant_id=ORG_TOKEN, db=mock_db)
        assert result.org_id == ORG_TOKEN
        assert result.role == "owner"
        mock_db.query.assert_not_called()

    def test_invalid_tenant_id_ignored(self, mock_db):
        claims = _claims(ORG_TOKEN, role="member")
        result = get_ee_current_user(claims=claims, tenant_id="not-a-uuid", db=mock_db)
        assert result.org_id == ORG_TOKEN
        mock_db.query.assert_not_called()

    def test_no_tenant_header_returns_token_claims(self, mock_db):
        claims = _claims(ORG_TOKEN, role="member")
        result = get_ee_current_user(claims=claims, tenant_id=None, db=mock_db)
        assert result.org_id == ORG_TOKEN
        mock_db.query.assert_not_called()
