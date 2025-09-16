from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from typing import Optional, Dict, Any
import time
from pydantic import BaseModel
from src.settings import settings
from loguru import logger


# JWT Bearer token extractor
security = HTTPBearer()

class JWTClaims(BaseModel):
    """JWT Claims similar to ClerkClaims pattern"""
    user_id: int
    org_id: Optional[int] = None
    role: Optional[str] = None
    email: str
    exp: int
    iat: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for easy access"""
        return {
            "user_id": self.user_id,
            "org_id": self.org_id,
            "role": self.role,
            "email": self.email,
            "exp": self.exp,
            "iat": self.iat
        }

class JWTManager:
    """JWT Token Management"""
    
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire_hours = 24  # 24 hours
    
    def create_access_token(self, user_id: int, email: str, org_id: Optional[int] = None, 
                          role: Optional[str] = None) -> str:
        """Create JWT access token"""
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
        """Decode and verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token is expired
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
        """Verify JWT token from Authorization header"""
        token = credentials.credentials
        return self.decode_token(token)

# Initialize JWT Manager
jwt_manager = JWTManager()

def get_jwt_claims(credentials: HTTPAuthorizationCredentials = Depends(security)) -> JWTClaims:
    """
    Dependency injection function to get JWT claims
    Similar to get_clerk_claims but for JWT
    """
    return jwt_manager.verify_token(credentials)

def get_optional_jwt_claims(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[JWTClaims]:
    """
    Optional JWT claims - returns None if no token provided
    """
    if not credentials:
        return None
    return jwt_manager.verify_token(credentials)

def require_org_member(claims: JWTClaims = Depends(get_jwt_claims)) -> JWTClaims:
    """
    Dependency that ensures user has organization access
    """
  
    if not claims.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID is required for this operation"
        )
    return claims

def require_admin_or_owner(claims: JWTClaims = Depends(get_jwt_claims)) -> JWTClaims:
    """
    Dependency that ensures user has admin or owner role
    """
    if not claims.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Owner role required"
        )
    return claims

def require_owner(claims: JWTClaims = Depends(get_jwt_claims)) -> JWTClaims:
    """
    Dependency that ensures user has owner role
    """
    if not claims.role or claims.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner role required"
        )
    return claims