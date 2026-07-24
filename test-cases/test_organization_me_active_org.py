"""Regression tests for `/organization/me` + `/auth/me` honoring the ACTIVE org.

Bug: after switching to a non-default workspace, the dashboard/switcher would
load correctly at first, then a few seconds later flip to the user's *default*
org's data. Root cause: `AuthService.get_organization_me` resolved the org via
`_membership_for`, which always returned the `is_default` membership and ignored
the active tenant. The fix threads the active org id (from the JWT tenant
context) through so the currently-active workspace is returned.
"""

from unittest.mock import MagicMock

from core.services.auth_service import AuthService

USER_ID = "11111111-1111-1111-1111-111111111111"
ACTIVE_ORG = "22222222-2222-2222-2222-222222222222"
DEFAULT_ORG = "33333333-3333-3333-3333-333333333333"


def _svc():
    db = MagicMock()
    db.query.return_value = db
    db.filter.return_value = db
    db.first.return_value = None
    return AuthService(db), db


def test_membership_for_prefers_active_org():
    """When an active org is supplied and the user is a member, that membership
    is returned by the first (org-scoped) lookup — before the default lookup."""
    svc, db = _svc()
    active_member = MagicMock(organization_id=ACTIVE_ORG)
    db.first.side_effect = [active_member]  # org-scoped query hits immediately

    result = svc._membership_for(USER_ID, org_id=ACTIVE_ORG)

    assert result is active_member


def test_membership_for_falls_back_to_default_when_not_member():
    """Active org supplied but user is not a member of it → fall back to the
    default membership rather than returning None."""
    svc, db = _svc()
    default_member = MagicMock(organization_id=DEFAULT_ORG)
    # 1st .first() = org-scoped lookup (miss), 2nd = is_default lookup (hit)
    db.first.side_effect = [None, default_member]

    result = svc._membership_for(USER_ID, org_id=ACTIVE_ORG)

    assert result is default_member


def test_membership_for_uses_default_when_no_active_org():
    """No active org → straight to the default membership (single query)."""
    svc, db = _svc()
    default_member = MagicMock(organization_id=DEFAULT_ORG)
    db.first.side_effect = [default_member]

    result = svc._membership_for(USER_ID)

    assert result is default_member


def test_get_organization_me_threads_active_org():
    """The route-facing method must pass the active org id down to the
    membership resolver (the actual regression: org_id was dropped)."""
    svc, _ = _svc()
    captured = {}

    def fake_membership(user_id, org_id=None):
        captured["user_id"] = user_id
        captured["org_id"] = org_id
        return None

    svc._membership_for = fake_membership

    svc.get_organization_me(USER_ID, org_id=ACTIVE_ORG)

    assert captured["org_id"] == ACTIVE_ORG


def test_get_organization_me_returns_active_org_record():
    """End-to-end within the service: active org membership → that org's dict."""
    svc, db = _svc()
    active_member = MagicMock(organization_id=ACTIVE_ORG)
    org_obj = MagicMock()
    org_obj.to_dict.return_value = {"id": ACTIVE_ORG, "name": "Active Workspace"}
    # 1st .first() = org-scoped membership, 2nd = Organization lookup
    db.first.side_effect = [active_member, org_obj]

    result = svc.get_organization_me(USER_ID, org_id=ACTIVE_ORG)

    assert result == {"id": ACTIVE_ORG, "name": "Active Workspace"}
