from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.schemas.list_request import ListRequest, apply_list_request
from ee.middleware.auth import (
    EEJWTClaims,
    get_ee_jwt_claims,
    require_ee_admin_or_owner,
    require_ee_org_member,
)
from ee.services.auth_service import EEAuthService

router = APIRouter()


# ── /me — current org for the signed-in user ──────────────────────────


@router.get("/me")
def get_organization_me(
    claims: EEJWTClaims = Depends(get_ee_jwt_claims),
    db: Session = Depends(get_db),
):
    return EEAuthService(db).get_organization_me(claims.user_id)


# ── List orgs the user belongs to ────────────────────────────────────


ORG_SEARCH_FIELDS = ["name", "slug", "role"]


@router.post("/get_associated_tenants")
def get_associated_tenants(
    list_req: ListRequest = Body(default_factory=ListRequest),
    claims: EEJWTClaims = Depends(get_ee_jwt_claims),
    db: Session = Depends(get_db),
):
    rows = EEAuthService(db).get_associated_organizations(claims.user_id)
    return apply_list_request(rows, list_req, searchable_fields=ORG_SEARCH_FIELDS)


# ── Invitations ──────────────────────────────────────────────────────


@router.post("/invite_user_to_organization")
def invite_user_to_organization(
    invite_data: Dict[str, str] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db),
):
    email = invite_data.get("email")
    role = invite_data.get("role")
    name = invite_data.get("name")
    if not email or not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="email and role are required",
        )
    return EEAuthService(db, user_id=claims.user_id).invite_user_to_organization(
        email=email,
        role=role,
        invited_by=claims.user_id,
        organization_id=claims.org_id,
        name=name,
    )


@router.delete("/cancel_invitation")
def cancel_invitation(
    invite_id: str = Query(...),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db),
):
    return EEAuthService(db, user_id=claims.user_id).cancel_invitation(invite_id)


@router.post("/resend_invitation")
def resend_invitation(
    invite_id: str = Query(...),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db),
):
    return EEAuthService(db, user_id=claims.user_id).resend_invitation(invite_id)


@router.get("/validate_invitation")
def validate_invitation(
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    return EEAuthService(db).validate_invitation_by_token(token)


@router.get("/accept_invitation")
def accept_invitation(
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    return EEAuthService(db).accept_invitation_by_token(token=token)


@router.post("/accept_invitation_with_password")
def accept_invitation_with_password(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    token = payload.get("token") or payload.get("code")
    password = payload.get("password")
    if not token or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="token and password are required",
        )
    return EEAuthService(db).accept_invitation_by_token(
        token=token,
        password=password,
        first_name=payload.get("first_name"),
        last_name=payload.get("last_name"),
    )


# ── Tenant CRUD ──────────────────────────────────────────────────────


@router.post("/create_tenants")
def create_tenants(
    name: str = Query(...),
    claims: EEJWTClaims = Depends(get_ee_jwt_claims),
    db: Session = Depends(get_db),
):
    return EEAuthService(db, user_id=claims.user_id).create_organization(name, claims.user_id)


# ── Membership management ────────────────────────────────────────────


@router.delete("/remove_user_from_organization")
def remove_user_from_organization(
    user_id: str = Query(...),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db),
):
    return EEAuthService(db, org_id=claims.org_id, user_id=claims.user_id).remove_user_from_organization(
        user_id=user_id, org_id=claims.org_id,
    )


@router.post("/update_member_role")
def update_member_role(
    member_id: str = Query(...),
    role: str = Query(...),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db),
):
    return EEAuthService(db, org_id=claims.org_id, user_id=claims.user_id).update_member_role(
        member_id=member_id, new_role=role,
    )


# ── Organization settings ────────────────────────────────────────────


@router.get("/settings")
def get_organization_settings(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return EEAuthService(db, org_id=claims.org_id).get_organization_settings()


@router.put("/settings")
def update_organization_settings(
    settings_data: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db),
):
    return EEAuthService(db, org_id=claims.org_id).update_organization_settings(settings_data)


# ── Org access requests — not supported on v2 schema ────────────────


@router.post("/request_access")
def request_access(
    request_data: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(get_ee_jwt_claims),
    db: Session = Depends(get_db),
):
    return EEAuthService(db).request_organization_access(claims.user_id)


@router.get("/access_requests")
def get_access_requests(
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db),
):
    return EEAuthService(db, org_id=claims.org_id).get_access_requests()


@router.post("/handle_access_request")
def handle_access_request(
    request_data: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db),
):
    return EEAuthService(db, org_id=claims.org_id, user_id=claims.user_id).handle_access_request()


@router.get("/roles")
def get_roles(
    claims: EEJWTClaims = Depends(get_ee_jwt_claims),
    db: Session = Depends(get_db),
):
    return EEAuthService(db).get_roles_by_scope()


# ── Members list (legacy GET shapes — also exposed via /user/...) ───


@router.get("/members")
def get_members(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return EEAuthService(db, org_id=claims.org_id).get_all_users_for_organization(claims.org_id)


@router.get("/invited_users")
def get_invited_users(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return EEAuthService(db, org_id=claims.org_id).get_all_invited_users_for_organization(claims.org_id)


# ── Organization details ─────────────────────────────────────────────


@router.get("/details")
def get_organization_details(
    org_id: str = Query(...),
    claims: EEJWTClaims = Depends(get_ee_jwt_claims),
    db: Session = Depends(get_db),
):
    return EEAuthService(db, user_id=claims.user_id).get_organization_details(org_id)


@router.put("/details")
def update_organization_details(
    update_data: Dict[str, Any] = Body(...),
    org_id: str = Query(...),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db),
):
    return EEAuthService(db, org_id=org_id, user_id=claims.user_id).update_organization_details(
        org_id, update_data,
    )


@router.delete("/delete")
def delete_organization(
    org_id: str = Query(...),
    claims: EEJWTClaims = Depends(get_ee_jwt_claims),
    db: Session = Depends(get_db),
):
    return EEAuthService(db, org_id=org_id, user_id=claims.user_id).delete_organization(
        org_id, claims.user_id,
    )
