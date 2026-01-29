from fastapi import HTTPException, status, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from typing import Optional, Dict, Any
import time
from pydantic import BaseModel
from uuid import UUID

from ee.config import ee_settings


security = HTTPBearer()


class EEJWTClaims(BaseModel):
    user_id: int
    org_id: Optional[str] = None
    role: Optional[str] = None
    email: str
    exp: int
    iat: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "org_id": self.org_id,
            "role": self.role,
            "email": self.email,
            "exp": self.exp,
            "iat": self.iat
        }


class EEJWTManager:
    def __init__(self):
        self.secret_key = ee_settings.JWT_SECRET_KEY
        self.algorithm = ee_settings.JWT_ALGORITHM
        self.access_token_expire_hours = ee_settings.ACCESS_TOKEN_EXPIRE_HOURS

    def create_access_token(
        self,
        user_id: int,
        email: str,
        org_id: Optional[str] = None,
        role: Optional[str] = None
    ) -> str:
        current_time = int(time.time())
        payload = {
            "user_id": user_id,
            "email": email,
            "org_id": org_id,
            "role": role,
            "iat": current_time,
            "exp": current_time + (self.access_token_expire_hours * 3600)
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    def decode_token(self, token: str) -> EEJWTClaims:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            current_time = int(time.time())
            if payload.get("exp", 0) < current_time:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired"
                )

            return EEJWTClaims(**payload)

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

    def verify_token(self, credentials: HTTPAuthorizationCredentials) -> EEJWTClaims:
        token = credentials.credentials
        return self.decode_token(token)


ee_jwt_manager = EEJWTManager()


def get_ee_jwt_claims(credentials: HTTPAuthorizationCredentials = Depends(security)) -> EEJWTClaims:
    return ee_jwt_manager.verify_token(credentials)


def get_optional_ee_jwt_claims(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[EEJWTClaims]:
    if not credentials:
        return None
    return ee_jwt_manager.verify_token(credentials)


def get_ee_current_user(
    claims: EEJWTClaims = Depends(get_ee_jwt_claims),
    tenant_id: Optional[str] = Header(None, alias="tenant_id")
) -> EEJWTClaims:
    if tenant_id:
        claims.org_id = tenant_id
    return claims


def require_ee_org_member(claims: EEJWTClaims = Depends(get_ee_current_user)) -> EEJWTClaims:
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


def require_ee_admin_or_owner(claims: EEJWTClaims = Depends(get_ee_current_user)) -> EEJWTClaims:
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


def require_ee_owner(claims: EEJWTClaims = Depends(get_ee_current_user)) -> EEJWTClaims:
    if not claims.role or claims.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner role required"
        )
    return claims
