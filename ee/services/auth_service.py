"""EE auth service — implemented against the v2 (tone-test-aligned) schema.

Extends ``core.services.auth_service.AuthService`` with multi-tenant
helpers (associated organizations, organization details, create/switch
org). Pre-v2 methods that depend on dropped tables (firebase signup,
organization access requests, etc.) remain 501 stubs.
"""

import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.middleware.auth import jwt_manager
from core.models.invite import Invite
from core.models.member import Member
from core.models.organization import Organization
from core.models.user import User
from core.services.auth_service import AuthService, _user_uuid, _slugify


class EEAuthService(AuthService):
    def __init__(
        self,
        db: Session,
        org_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
    ):
        super().__init__(db, user_id=user_id, org_id=org_id)

    # ── Multi-tenant: list orgs the user belongs to ─────────────────

    def get_associated_organizations(self, user_id: Union[str, UUID]) -> List[Dict[str, Any]]:
        uid = _user_uuid(user_id)
        if not uid:
            return []
        rows = (
            self.db.query(Member, Organization)
            .join(Organization, Member.organization_id == Organization.id)
            .filter(Member.user_id == uid)
            .all()
        )
        return [
            {
                "id": str(org.id),
                "name": org.name,
                "slug": org.slug,
                "description": org.description,
                "logo_url": org.logo_url,
                "subscription_tier": org.subscription_tier,
                "status": org.status,
                "role": member.role,
                "is_default": member.is_default,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
            }
            for member, org in rows
        ]

    # ── Create a new organization for the current user ──────────────

    def create_organization(self, name: str, user_id: Union[str, UUID]) -> Dict[str, Any]:
        uid = _user_uuid(user_id)
        if not uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user id"
            )
        slug = _slugify(name)
        if self.db.query(Organization).filter(Organization.slug == slug).first():
            slug = f"{slug}-{secrets.token_hex(3)}"

        org = Organization(
            name=name,
            slug=slug,
            subscription_tier="free",
            status="active",
        )
        self.db.add(org)
        self.db.flush()

        member = Member(
            user_id=uid,
            organization_id=org.id,
            role="owner",
            is_default=False,
        )
        self.db.add(member)
        self.db.commit()
        self.db.refresh(org)

        return {
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "role": "owner",
        }

    # ── Switch current tenant + return a fresh access token ─────────

    def switch_organization(self, user_id: Union[str, UUID], org_id: Union[str, UUID]) -> Dict[str, Any]:
        uid = _user_uuid(user_id)
        oid = _user_uuid(org_id)
        member = (
            self.db.query(Member)
            .filter(Member.user_id == uid, Member.organization_id == oid)
            .first()
            if uid and oid
            else None
        )
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this organization",
            )
        org = self.db.query(Organization).filter(Organization.id == oid).first()
        user = self.db.query(User).filter(User.id == uid).first()
        if not org or not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization or user not found",
            )
        access_token = jwt_manager.create_access_token(
            user_id=str(user.id), email=user.email, org_id=str(org.id), role=member.role
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "organization": org.to_dict(),
            "role": member.role,
        }

    # ── Organization details ─────────────────────────────────────────

    def get_organization_details(self, org_id: Union[str, UUID]) -> Dict[str, Any]:
        oid = _user_uuid(org_id)
        org = self.db.query(Organization).filter(Organization.id == oid).first() if oid else None
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
            )
        member_count = self.db.query(Member).filter(Member.organization_id == oid).count()
        payload = org.to_dict()
        payload["member_count"] = member_count
        return payload

    def update_organization_details(
        self,
        org_id: Union[str, UUID],
        update_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        oid = _user_uuid(org_id)
        org = self.db.query(Organization).filter(Organization.id == oid).first() if oid else None
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
            )
        allowed = {"name", "description", "logo_url", "website"}
        for key, value in update_data.items():
            if key in allowed:
                setattr(org, key, value)
        new_name = update_data.get("name")
        if new_name and new_name != org.name:
            new_slug = _slugify(new_name)
            if new_slug != org.slug:
                duplicate = (
                    self.db.query(Organization)
                    .filter(Organization.slug == new_slug, Organization.id != oid)
                    .first()
                )
                if duplicate:
                    new_slug = f"{new_slug}-{secrets.token_hex(3)}"
                org.slug = new_slug
        self.db.commit()
        self.db.refresh(org)
        payload = org.to_dict()
        payload["message"] = "Organization updated successfully"
        return payload

    def delete_organization(
        self,
        org_id: Union[str, UUID],
        user_id: Union[str, UUID],
    ) -> Dict[str, str]:
        oid = _user_uuid(org_id)
        uid = _user_uuid(user_id)
        org = self.db.query(Organization).filter(Organization.id == oid).first() if oid else None
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
            )
        owner_member = (
            self.db.query(Member)
            .filter(
                Member.organization_id == oid,
                Member.user_id == uid,
                Member.role == "owner",
            )
            .first()
        )
        if not owner_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only an owner can delete this organization",
            )

        self.db.query(Invite).filter(Invite.organization_id == oid).delete(synchronize_session=False)
        self.db.query(Member).filter(Member.organization_id == oid).delete(synchronize_session=False)
        self.db.delete(org)
        self.db.commit()
        return {"message": "Organization deleted successfully"}

    # ── Convenience checks ───────────────────────────────────────────

    def check_organization_exists(self, name: str) -> Dict[str, Any]:
        slug = _slugify(name)
        org = self.db.query(Organization).filter(Organization.slug == slug).first()
        if org:
            return {
                "exists": True,
                "organization": {
                    "id": str(org.id),
                    "name": org.name,
                    "slug": org.slug,
                },
            }
        return {"exists": False, "organization": None}

    # ── Org access requests — still unsupported in v2 ───────────────

    def request_organization_access(self, *args, **kwargs):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Organization access requests are not supported on the v2 auth schema",
        )
