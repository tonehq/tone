from fastapi import APIRouter, Depends, HTTPException, status, Body, Query, Header
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import time
from loguru import logger

from src.database import get_db
from src.services.auth_service import AuthService
from src.common.jwt_middleware import get_jwt_claims, require_org_member, require_admin_or_owner, JWTClaims

# Create router
router = APIRouter(
    tags=["auth"]
)

# Auth endpoints (no authentication required)
auth_router = APIRouter(prefix="/auth", tags=["authentication"])

# Org endpoints (authentication required)
org_router = APIRouter(prefix="/org", tags=["organizations"])

# User endpoints (authentication required)  
user_router = APIRouter(prefix="/user", tags=["users"])

# Organization management endpoints (authentication required)
organization_router = APIRouter(prefix="/organization", tags=["organization-management"])

# Permission endpoints (authentication required)
permissions_router = APIRouter(prefix="/permissions", tags=["permissions"])

# API 1: Signup
@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(
    user_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """
    Create a new user account with email and password
    Expected payload: {email, password, username, profile, org_name}
    """
    email = user_data.get("email")
    password = user_data.get("password")
    username = user_data.get("username")
    profile = user_data.get("profile") or {}
    org_name = user_data.get("org_name")

    if org_name:
        profile["org_name"] = org_name

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )

    auth_service = AuthService(db)
    return auth_service.signup(email, password, username, profile)


@auth_router.get("/check_organization_exists")
def check_organization_exists(
    name: str = Query(..., description="Organization name to check"),
    db: Session = Depends(get_db)
):
    auth_service = AuthService(db)
    return auth_service.check_organization_exists(name)


# API 2: Firebase Signup
@auth_router.post("/signup_with_firebase", status_code=status.HTTP_201_CREATED)
def signup_with_firebase(
    user_data: Dict[str, Any] = Body(...),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """
    Create user account using Firebase authentication
    Expected payload: {email, profile}
    Expected header: Authorization: Bearer {firebase_token}
    """
    email = user_data.get("email")
    profile = user_data.get("profile")
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required"
        )
    
    # Extract Firebase token from Authorization header
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )
    
    firebase_token = authorization.split("Bearer ")[1]
    
    auth_service = AuthService(db)
    return auth_service.signup_with_firebase(firebase_token, email, profile)


# API 3: Email Verification Mail
@auth_router.get("/resend_verification_email")
def resend_verification_email(
    email: str = Query(..., description="Email address to send verification"),
    db: Session = Depends(get_db)
):
    """
    Send verification email to user
    """
    auth_service = AuthService(db)
    return auth_service.resend_verification_email(email)


# API 4: Verify Signup
@auth_router.get("/verify_user_email")
def verify_user_email(
    email: str = Query(..., description="Email address"),
    code: str = Query(..., description="Verification code"),
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Verify user email with verification code
    """
    auth_service = AuthService(db)
    return auth_service.verify_user_email(email, code, user_id)


# API 5: Get List of Organization
@org_router.get("/get_associated_tenants")
def get_associated_tenants(
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db)
):
    """
    Get all organizations user is a member of
    """
    auth_service = AuthService(db, user_id=claims.user_id)
    return auth_service.get_associated_organizations(claims.user_id)


# API 6: List of Members

@user_router.get("/get_all_users_for_organization")
def get_all_users_for_organization(
    org_id: int | None = Header(None, alias="tenant_id"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """
    Get all members in organization
    """
    # Pick org_id from header first, else from claims
    if not claims.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization ID is required"
        )

    auth_service = AuthService(db, org_id=org_id)
    return auth_service.get_all_users_for_organization(org_id)
   

# API 6: List of invited Members

@user_router.get("/get_all_invited_users_for_organization")
def get_all_invited_users_for_organization(
    org_id: int | None = Header(None, alias="tenant_id"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """
    Get all members in organization
    """
    # Pick org_id from header first, else from claims
    if not claims.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization ID is required"
        )

    auth_service = AuthService(db, org_id=org_id)
    return auth_service.get_all_invited_users_for_organization(org_id)
   

# API 7: Get Roles
@permissions_router.get("/get_roles_by_scope")
def get_roles_by_scope(
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db)
):
    """
    Get available roles for organization
    """
    auth_service = AuthService(db, org_id=claims.org_id, user_id=claims.user_id)
    return auth_service.get_roles_by_scope()


# API 8: Create Organization
@org_router.post("/create_tenants")
def create_tenants(
    name: str = Query(..., description="Organization name"),
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db)
):
    """
    Create a new organization
    """
    auth_service = AuthService(db, user_id=claims.user_id)
    return auth_service.create_organization(name, claims.user_id)

# API 9: Invite Member
@organization_router.post("/invite_user_to_organization")
def invite_user_to_organization(
    invite_data: Dict[str, str] = Body(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
    org_id: int | None = Header(None, alias="tenant_id"),
):
    """
    Invite member to organization
    Expected payload: {name, email, role}
    """
    name = invite_data.get("name")
    email = invite_data.get("email")
    role = invite_data.get("role")

    from src.model.auth_model import Member
    member = db.query(Member).filter(
        Member.user_id == claims.user_id,
        Member.organization_id == org_id,
        Member.status == 'active'
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this organization"
        )

    if member.role.value not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins or owners can invite members"
        )
    
    if not all([name, email, role]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name, email, and role are required"
        )
    
    auth_service = AuthService(db, org_id=org_id, user_id=claims.user_id)
    return auth_service.invite_user_to_organization(
        org_id, name, email, role, claims.user_id
    )


@organization_router.get("/accept_invitation")
def accept_invitation(
    email: str = Query(..., description="Email of the invited user"),
    code: str = Query(..., description="Invitation token"),
    user_tenant_id: int = Query(..., description="Organization ID"),
    db: Session = Depends(get_db)
):
    auth_service = AuthService(db)
    return auth_service.accept_invitation(email, code, user_tenant_id)


# API 10: Delete Member
@organization_router.delete("/remove_user_from_organization")
def remove_user_from_organization(
    user_id: int = Query(..., description="User ID to remove"),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    """
    Remove member from organization
    """
    if not claims.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization ID is required"
        )
    
    auth_service = AuthService(db, org_id=claims.org_id, user_id=claims.user_id)
    return auth_service.remove_user_from_organization(claims.org_id, user_id)


# API 11: Update Member Role
@organization_router.post("/update_member_role")
def update_member_role(
    member_id: int = Query(..., description="Member ID to update"),
    role: str = Query(..., description="New role"),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
    org_id: int | None = Header(None, alias="tenant_id"),
):
    """
    Update member role (only role can be updated)
    """
    auth_service = AuthService(db, org_id=org_id, user_id=claims.user_id)
    return auth_service.update_member_role(member_id, role)


@organization_router.get("/settings")
def get_organization_settings(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
    org_id: int | None = Header(None, alias="tenant_id"),
):
    auth_service = AuthService(db, org_id=org_id, user_id=claims.user_id)
    return auth_service.get_organization_settings(org_id)


@organization_router.put("/settings")
def update_organization_settings(
    settings_data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
    org_id: int | None = Header(None, alias="tenant_id"),
):
    auth_service = AuthService(db, org_id=org_id, user_id=claims.user_id)
    return auth_service.update_organization_settings(org_id, settings_data)


@organization_router.post("/request_access")
def request_organization_access(
    request_data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db),
):
    org_id = request_data.get("org_id")
    message = request_data.get("message")

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization ID is required"
        )

    auth_service = AuthService(db, user_id=claims.user_id)
    return auth_service.request_organization_access(claims.user_id, org_id, message)


@organization_router.get("/access_requests")
def get_access_requests(
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
    org_id: int | None = Header(None, alias="tenant_id"),
):
    auth_service = AuthService(db, org_id=org_id, user_id=claims.user_id)
    return auth_service.get_access_requests(org_id)


@organization_router.post("/handle_access_request")
def handle_access_request(
    request_data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
    org_id: int | None = Header(None, alias="tenant_id"),
):
    request_id = request_data.get("request_id")
    action = request_data.get("action")

    if not request_id or not action:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request ID and action are required"
        )

    auth_service = AuthService(db, org_id=org_id, user_id=claims.user_id)
    return auth_service.handle_access_request(request_id, action, claims.user_id)


# API 12: Sign In
@auth_router.post("/login")
def login(
    login_data: Dict[str, str] = Body(...),
    db: Session = Depends(get_db)
):
    """
    User login with email and password
    Expected payload: {email, password}
    """
    email = login_data.get("email")
    password = login_data.get("password")
    
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )
    
    auth_service = AuthService(db)
    return auth_service.login(email, password)


# API 13: Forgot Password
@auth_router.get("/forget-password")
def forget_password(
    email: str = Query(..., description="Email address"),
    db: Session = Depends(get_db)
):
    """
    Send forgot password email
    """
    auth_service = AuthService(db)
    return auth_service.forgot_password(email)


# API 14: Reset Password
@auth_router.get("/acceptForgotPassword")
def accept_forgot_password(
    email: str = Query(..., description="Email address"),
    password: str = Query(..., description="New password"),
    token: str = Query(..., description="Reset token"),
    db: Session = Depends(get_db)
):
    """
    Reset password with token
    """
    auth_service = AuthService(db)
    return auth_service.accept_forgot_password(email, password, token)


# Additional endpoint for JWT token refresh with org context
@auth_router.post("/switch_organization")
def switch_organization(
    org_data: Dict[str, int] = Body(...),
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db)
):
    """
    Switch organization context and get new JWT token
    Expected payload: {organization_id}
    """
    org_id = org_data.get("organization_id")
    
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization ID is required"
        )
    
    auth_service = AuthService(db, user_id=claims.user_id)
    
    # Verify user is member of the organization
    from src.model.auth_model import Member
    member = db.query(Member).filter(
        Member.user_id == claims.user_id,
        Member.organization_id == org_id,
        Member.status == 'active'
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this organization"
        )
    
    # Create new JWT token with org context
    from src.common.jwt_middleware import jwt_manager
    access_token = jwt_manager.create_access_token(
        user_id=claims.user_id,
        email=claims.email,
        org_id=org_id,
        role=member.role.value
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "org_id": org_id,
        "role": member.role.value
    }


# Include all sub-routers in main router
router.include_router(auth_router)
router.include_router(org_router)
router.include_router(user_router)
router.include_router(organization_router)
router.include_router(permissions_router)