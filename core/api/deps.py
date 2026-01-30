from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTManager, JWTClaims, security

jwt_manager = JWTManager()


def get_jwt_claims(credentials: HTTPAuthorizationCredentials = Depends(security)) -> JWTClaims:
    return jwt_manager.verify_token(credentials)


def get_current_user(claims: JWTClaims = Depends(get_jwt_claims)) -> JWTClaims:
    return claims


def require_authenticated(claims: JWTClaims = Depends(get_current_user)) -> JWTClaims:
    if not claims.user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return claims


def require_admin_or_owner(claims: JWTClaims = Depends(get_current_user)) -> JWTClaims:
    if not claims.user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    if claims.role not in ["admin", "owner"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or owner role required")
    return claims
