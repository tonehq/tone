from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, Any
from uuid import UUID

from ee.database.session import get_ee_db
from ee.services.auth_service import EEAuthService
from ee.middleware.auth import get_ee_jwt_claims, get_ee_current_user, require_ee_org_member, require_ee_admin_or_owner, EEJWTClaims

router = APIRouter()


@router.get("/get_associated_tenants")
def get_associated_tenants(
    claims: EEJWTClaims = Depends(get_ee_jwt_claims),
    db: Session = Depends(get_ee_db)
):
    return EEAuthService(db).get_associated_organizations(claims.user_id)


@router.post("/create_tenants")
def create_tenants(
    name: str = Query(...),
    claims: EEJWTClaims = Depends(get_ee_jwt_claims),
    db: Session = Depends(get_ee_db)
):
    return EEAuthService(db).create_organization(name, claims.user_id)


@router.post("/invite_user_to_organization")
def invite_user_to_organization(
    invite_data: Dict[str, str] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_ee_db)
):
    name = invite_data.get("name")
    email = invite_data.get("email")
    role = invite_data.get("role")

    if not all([name, email, role]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name, email, and role are required"
        )

    return EEAuthService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).invite_user_to_organization(
        UUID(claims.org_id), name, email, role, claims.user_id
    )


@router.get("/accept_invitation")
def accept_invitation(
    email: str = Query(...),
    code: str = Query(...),
    user_tenant_id: str = Query(...),
    db: Session = Depends(get_ee_db)
):
    return EEAuthService(db).accept_invitation(email, code, UUID(user_tenant_id))


@router.delete("/remove_user_from_organization")
def remove_user_from_organization(
    user_id: int = Query(...),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_ee_db)
):
    return EEAuthService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).remove_user_from_organization(
        UUID(claims.org_id), user_id
    )


@router.post("/update_member_role")
def update_member_role(
    member_id: int = Query(...),
    role: str = Query(...),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_ee_db)
):
    return EEAuthService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).update_member_role(
        UUID(claims.org_id), member_id, role
    )


@router.get("/settings")
def get_organization_settings(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_ee_db)
):
    return EEAuthService(db, org_id=UUID(claims.org_id)).get_organization_settings(UUID(claims.org_id))


@router.put("/settings")
def update_organization_settings(
    settings_data: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_ee_db)
):
    return EEAuthService(db, org_id=UUID(claims.org_id)).update_organization_settings(UUID(claims.org_id), settings_data)


@router.post("/request_access")
def request_access(
    request_data: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(get_ee_jwt_claims),
    db: Session = Depends(get_ee_db)
):
    org_id = request_data.get("org_id")
    message = request_data.get("message")

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization ID is required"
        )

    return EEAuthService(db).request_organization_access(claims.user_id, UUID(org_id), message)


@router.get("/access_requests")
def get_access_requests(
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_ee_db)
):
    return EEAuthService(db, org_id=UUID(claims.org_id)).get_access_requests(UUID(claims.org_id))


@router.post("/handle_access_request")
def handle_access_request(
    request_data: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_ee_db)
):
    request_id = request_data.get("request_id")
    action = request_data.get("action")

    if not request_id or not action:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request ID and action are required"
        )

    return EEAuthService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).handle_access_request(
        UUID(claims.org_id), request_id, action, claims.user_id
    )


@router.get("/roles")
def get_roles(
    claims: EEJWTClaims = Depends(get_ee_jwt_claims),
    db: Session = Depends(get_ee_db)
):
    return EEAuthService(db).get_roles_by_scope()
