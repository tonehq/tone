from fastapi import HTTPException, status, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from core.middleware.auth import JWTClaims, jwt_manager, security
from core.context import set_tenant_context

EEJWTClaims = JWTClaims
ee_jwt_manager = jwt_manager


def get_ee_jwt_claims(credentials: HTTPAuthorizationCredentials = Depends(security)) -> JWTClaims:
    claims = jwt_manager.verify_token(credentials)
    if claims.org_id:
        set_tenant_context(org_id=claims.org_id, user_id=claims.user_id, role=claims.role)
    return claims


def get_optional_ee_jwt_claims(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[JWTClaims]:
    if not credentials:
        return None
    return jwt_manager.verify_token(credentials)


def get_ee_current_user(
    claims: JWTClaims = Depends(get_ee_jwt_claims),
    tenant_id: Optional[str] = Header(None, alias="tenant_id")
) -> JWTClaims:
    if tenant_id:
        claims.org_id = tenant_id
        set_tenant_context(org_id=tenant_id, user_id=claims.user_id, role=claims.role)
    return claims


def require_ee_org_member(claims: JWTClaims = Depends(get_ee_current_user)) -> JWTClaims:
    if not claims.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID is required"
        )
    if not claims.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization ID is required. Use tenant_id header or switch organization."
        )
    return claims


def require_ee_admin_or_owner(claims: JWTClaims = Depends(get_ee_current_user)) -> JWTClaims:
    if not claims.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication required"
        )
    if not claims.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization ID is required"
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
