"""Tests for AuthService.complete_onboarding — the /auth/onboarding endpoint."""
import uuid

import pytest
from fastapi import HTTPException

from core.models.member import Member
from core.models.organization import Organization
from core.models.user import User
from core.services.auth_service import AuthService


def _mk_org(db, *, onboarded=False, slug_prefix="wksp"):
    org = Organization(
        name="Placeholder Workspace",
        slug=f"{slug_prefix}-{uuid.uuid4().hex[:8]}",
        subscription_tier="free",
        status="active",
        onboarding_completed=onboarded,
    )
    db.add(org)
    db.flush()
    return org


def _mk_user(db, org, *, role="owner"):
    user = User(
        organization_id=org.id,
        email=f"user-{uuid.uuid4().hex[:8]}@test.com",
        password_hash="x",
        first_name="Test",
        last_name="User",
        role=role,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()
    member = Member(
        user_id=user.id,
        organization_id=org.id,
        role=role,
        is_default=True,
    )
    db.add(member)
    db.flush()
    return user


class TestCompleteOnboarding:
    def test_renames_org_and_sets_use_case_industry(self, db_session):
        org = _mk_org(db_session)
        user = _mk_user(db_session, org)
        original_slug = org.slug

        svc = AuthService(db_session)
        updated_org, sent, failed = svc.complete_onboarding(
            user_id=user.id,
            workspace_name="Acme AI",
            use_case="customer_support",
            industry="software",
            invites=[],
        )
        response = svc.onboarding_response(updated_org, sent, failed)

        assert updated_org.name == "Acme AI"
        assert updated_org.onboarding_completed is True
        assert updated_org.use_case == "customer_support"
        assert updated_org.industry == "software"
        # slug regenerated from the new name
        assert updated_org.slug != original_slug
        assert "acme" in updated_org.slug
        assert sent == []
        assert failed == []
        # Formatter matches the shape the router returns.
        assert response == {
            "organization": updated_org.to_dict(),
            "invites_sent": [],
            "invites_failed": [],
        }

    def test_industry_null_when_omitted(self, db_session):
        org = _mk_org(db_session)
        user = _mk_user(db_session, org)

        updated_org, _sent, _failed = AuthService(db_session).complete_onboarding(
            user_id=user.id,
            workspace_name="Solo",
            use_case="sales",
            industry=None,
            invites=[],
        )

        assert updated_org.industry is None

    def test_bad_email_does_not_rollback_org(self, db_session):
        org = _mk_org(db_session)
        user = _mk_user(db_session, org)

        updated_org, sent, failed = AuthService(db_session).complete_onboarding(
            user_id=user.id,
            workspace_name="Team Ship",
            use_case="sales",
            industry=None,
            invites=[{"email": "  ", "role": "developer"}],
        )

        assert updated_org.name == "Team Ship"
        assert updated_org.onboarding_completed is True
        # blank invite skipped, not sent, not failed
        assert sent == []
        assert failed == []

    def test_rejects_non_owner_or_admin(self, db_session):
        org = _mk_org(db_session)
        user = _mk_user(db_session, org, role="developer")

        with pytest.raises(HTTPException) as exc_info:
            AuthService(db_session).complete_onboarding(
                user_id=user.id,
                workspace_name="Nope",
                use_case="sales",
                industry=None,
                invites=[],
            )
        assert exc_info.value.status_code == 403

    def test_requires_workspace_name(self, db_session):
        org = _mk_org(db_session)
        user = _mk_user(db_session, org)

        with pytest.raises(HTTPException) as exc_info:
            AuthService(db_session).complete_onboarding(
                user_id=user.id,
                workspace_name="   ",
                use_case="sales",
                industry=None,
                invites=[],
            )
        assert exc_info.value.status_code == 400

    def test_requires_use_case(self, db_session):
        org = _mk_org(db_session)
        user = _mk_user(db_session, org)

        with pytest.raises(HTTPException) as exc_info:
            AuthService(db_session).complete_onboarding(
                user_id=user.id,
                workspace_name="Fine",
                use_case="",
                industry=None,
                invites=[],
            )
        assert exc_info.value.status_code == 400

    def test_idempotent_second_call_ok(self, db_session):
        org = _mk_org(db_session)
        user = _mk_user(db_session, org)

        svc = AuthService(db_session)
        svc.complete_onboarding(
            user_id=user.id,
            workspace_name="First",
            use_case="sales",
            industry="software",
            invites=[],
        )
        # Second call renames again — no dupes, no crash.
        updated_org, _sent, _failed = svc.complete_onboarding(
            user_id=user.id,
            workspace_name="Second",
            use_case="customer_support",
            industry="ecommerce",
            invites=[],
        )
        assert updated_org.name == "Second"
        assert updated_org.use_case == "customer_support"
        assert updated_org.industry == "ecommerce"
        assert updated_org.onboarding_completed is True
