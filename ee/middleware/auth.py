from fastapi import HTTPException, status, Depends, Header, Request
from typing import Optional
from uuid import UUID

from core.database.session import get_db
from core.middleware.auth import (
    JWTClaims,
    _enforce_active_session,
    get_bearer_or_cookie_token,
    jwt_manager,
)
from core.context import set_tenant_context


def _validate_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except (ValueError, TypeError):
        return False

EEJWTClaims = JWTClaims
ee_jwt_manager = jwt_manager


def get_ee_jwt_claims(
    request: Request,
    db=Depends(get_db),
) -> JWTClaims:
    token = get_bearer_or_cookie_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    claims = jwt_manager.decode_token(token)
    if claims.org_id:
        set_tenant_context(org_id=claims.org_id, user_id=claims.user_id, role=claims.role)
    _enforce_active_session(claims, db)
    return claims


def get_optional_ee_jwt_claims(
    request: Request,
    db=Depends(get_db),
) -> Optional[JWTClaims]:
    token = get_bearer_or_cookie_token(request)
    if not token:
        return None
    claims = jwt_manager.decode_token(token)
    _enforce_active_session(claims, db)
    return claims


def get_ee_current_user(
    claims: JWTClaims = Depends(get_ee_jwt_claims),
    tenant_id: Optional[str] = Header(None, alias="tenant_id"),
    db=Depends(get_db),
) -> JWTClaims:
    # The active org is authoritative in the (httpOnly-cookie) access token,
    # which is minted with a membership-verified org on login / org-switch.
    # The ``tenant_id`` header is a transitional client hint: honor it only
    # when it differs from the token's org AND the caller is genuinely a
    # member of that org — otherwise a forged header would expose another
    # tenant's data (IDOR). Membership lookup also yields the correct per-org
    # role so downstream role guards evaluate against the switched org.
    if (
        tenant_id
        and _validate_uuid(tenant_id)
        and str(tenant_id) != str(claims.org_id or "")
    ):
        from core.models.member import Member  # local import avoids import cycle

        member = (
            db.query(Member)
            .filter(
                Member.user_id == claims.user_uuid,
                Member.organization_id == UUID(tenant_id),
            )
            .first()
        )
        if member:
            claims.org_id = tenant_id
            claims.role = member.role
            set_tenant_context(
                org_id=tenant_id, user_id=claims.user_id, role=member.role
            )
    return claims


def require_ee_org_member(claims: JWTClaims = Depends(get_ee_current_user)) -> JWTClaims:
    if not claims.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID is required"
        )
    if not claims.org_id or not _validate_uuid(str(claims.org_id)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid Organization ID is required. Use tenant_id header or switch organization."
        )
    return claims


def require_ee_admin_or_owner(claims: JWTClaims = Depends(get_ee_current_user)) -> JWTClaims:
    if not claims.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication required"
        )
    if not claims.org_id or not _validate_uuid(str(claims.org_id)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid Organization ID is required"
        )
    if claims.role not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Owner role required"
        )
    return claims


def require_ee_owner(claims: JWTClaims = Depends(get_ee_current_user)) -> JWTClaims:
    if not claims.role or claims.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner role required"
        )
    return claims
