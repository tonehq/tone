from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, Any

from core.database.session import get_db
from core.services.auth_service import AuthService
from core.middleware.auth import get_jwt_claims, require_org_member, require_admin_or_owner, JWTClaims

router = APIRouter()


@router.post("/invite_user_to_organization")
def invite_user_to_organization(
    invite_data: Dict[str, str] = Body(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    name = invite_data.get("name")
    email = invite_data.get("email")
    role = invite_data.get("role")

    if not all([name, email, role]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name, email, and role are required"
        )

    return AuthService(db, user_id=claims.user_id).invite_user_to_organization(name, email, role, claims.user_id)


@router.get("/accept_invitation")
def accept_invitation(
    email: str = Query(...),
    code: str = Query(...),
    db: Session = Depends(get_db)
):
    return AuthService(db).accept_invitation(email, code)


@router.delete("/remove_user_from_organization")
def remove_user_from_organization(
    user_id: int = Query(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    return AuthService(db, user_id=claims.user_id).remove_user_from_organization(user_id)


@router.post("/update_member_role")
def update_member_role(
    member_id: int = Query(...),
    role: str = Query(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    return AuthService(db, user_id=claims.user_id).update_member_role(member_id, role)


@router.get("/settings")
def get_organization_settings(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db)
):
    return AuthService(db).get_organization_settings()


@router.put("/settings")
def update_organization_settings(
    settings_data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    return AuthService(db).update_organization_settings(settings_data)


@router.get("/access_requests")
def get_access_requests(
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    return AuthService(db).get_access_requests()


@router.post("/handle_access_request")
def handle_access_request(
    request_data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    request_id = request_data.get("request_id")
    action = request_data.get("action")

    if not request_id or not action:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request ID and action are required"
        )

    return AuthService(db, user_id=claims.user_id).handle_access_request(request_id, action, claims.user_id)


@router.get("/roles")
def get_roles(
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db)
):
    return AuthService(db).get_roles_by_scope()
