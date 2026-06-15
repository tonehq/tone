from datetime import timedelta
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any, Union
from uuid import UUID
import time
from pydantic import BaseModel
from jose import JWTError, jwt

from core.config import settings
from core.context import set_tenant_context
from core.internal.capabilities import is_ee_enabled


security = HTTPBearer()

class JWTClaims(BaseModel):
    user_id: str
    org_id: Optional[str] = None
    role: Optional[str] = None
    email: str
    exp: int
    iat: int
    type: Optional[str] = "access"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "org_id": self.org_id,
            "role": self.role,
            "email": self.email,
            "exp": self.exp,
            "iat": self.iat
        }

    @property
    def user_uuid(self) -> Optional[UUID]:
        try:
            return UUID(self.user_id) if self.user_id else None
        except (ValueError, TypeError):
            return None


class JWTManager:
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_hours = settings.ACCESS_TOKEN_EXPIRE_HOURS
        self.refresh_token_expire_days = getattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 30)

    def access_token_expire_seconds(self) -> int:
        return self.access_token_expire_hours * 3600

    def refresh_token_ttl(self) -> timedelta:
        return timedelta(days=self.refresh_token_expire_days)

    def create_access_token(
        self,
        user_id: Union[str, UUID],
        email: str,
        org_id: Optional[Union[str, UUID]] = None,
        role: Optional[str] = None
    ) -> str:
        current_time = int(time.time())
        payload = {
            "user_id": str(user_id),
            "email": email,
            "org_id": str(org_id) if org_id else None,
            "role": role,
            "type": "access",
            "iat": current_time,
            "exp": current_time + (self.access_token_expire_hours * 3600)
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    def create_refresh_token(
        self,
        user_id: Union[str, UUID],
        email: str,
        session_id: Union[str, UUID],
        family: Union[str, UUID],
        org_id: Optional[Union[str, UUID]] = None,
    ) -> str:
        current_time = int(time.time())
        payload = {
            "user_id": str(user_id),
            "email": email,
            "org_id": str(org_id) if org_id else None,
            "type": "refresh",
            "jti": str(session_id),
            "family": str(family),
            "iat": current_time,
            "exp": current_time + (self.refresh_token_expire_days * 86400),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_refresh_token(self, token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not a refresh token",
                )
            if payload.get("exp", 0) < int(time.time()):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token expired",
                )
            # Refresh tokens must carry a session reference (jti). Tokens
            # minted before sessions existed do not — they are rejected so
            # the user re-logs in and gets a tracked session.
            if not payload.get("jti"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token is missing a session reference. Please log in again.",
                )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired",
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

    def decode_token(self, token: str) -> JWTClaims:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            current_time = int(time.time())
            if payload.get("exp", 0) < current_time:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired"
                )

            return JWTClaims(**payload)

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

    def verify_token(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JWTClaims:
        token = credentials.credentials
        return self.decode_token(token)


jwt_manager = JWTManager()


def get_jwt_claims(credentials: HTTPAuthorizationCredentials = Depends(security)) -> JWTClaims:
    claims = jwt_manager.verify_token(credentials)
    if is_ee_enabled() and claims.org_id:
        org_id = claims.org_id
    else:
        org_id = settings.DEFAULT_ORG_ID
    set_tenant_context(org_id=org_id, user_id=claims.user_id, role=claims.role)
    return claims


def get_optional_jwt_claims(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[JWTClaims]:
    if not credentials:
        return None
    return jwt_manager.verify_token(credentials)


def require_org_member(claims: JWTClaims = Depends(get_jwt_claims)) -> JWTClaims:
    if not claims.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID is required for this operation"
        )
    return claims


def require_admin_or_owner(claims: JWTClaims = Depends(get_jwt_claims)) -> JWTClaims:
    if not claims.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Owner role required"
        )
    return claims


def require_owner(claims: JWTClaims = Depends(get_jwt_claims)) -> JWTClaims:
    if not claims.role or claims.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner role required"
        )
    return claims
