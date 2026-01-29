from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from typing import Optional, Dict, Any
import time
from pydantic import BaseModel

from core.config import settings


security = HTTPBearer()

class JWTClaims(BaseModel):
    user_id: int
    org_id: Optional[int] = None
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


class JWTManager:
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_hours = settings.ACCESS_TOKEN_EXPIRE_HOURS

    def create_access_token(
        self,
        user_id: int,
        email: str,
        org_id: Optional[int] = None,
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
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

    def verify_token(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JWTClaims:
        token = credentials.credentials
        return self.decode_token(token)


jwt_manager = JWTManager()


def get_jwt_claims(credentials: HTTPAuthorizationCredentials = Depends(security)) -> JWTClaims:
    return jwt_manager.verify_token(credentials)


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
