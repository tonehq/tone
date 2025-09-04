from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from typing import List, Optional, Dict, Any, Union
import time
import uuid
import secrets
import string
import hashlib
import bcrypt
from fastapi import HTTPException, status
import requests
from src.model.auth_model import (
    User, Organization, Member, OrganizationInvite, 
    EmailVerification, PasswordReset, 
    UserStatus, OrganizationStatus, Role, InviteStatus, AuthProvider
)
from src.common.jwt_middleware import jwt_manager, JWTClaims
from src.utils.orm_utils import model_to_dict
from src.services.email_service import MailService

class AuthService:
    """Service class for handling authentication and user management operations"""
    
    def __init__(self, db: Session, org_id: Optional[str] = None, user_id: Optional[str] = None):
        """
        Initialize the auth service with database session and optional organization ID and user ID.
        
        Args:
            db (Session): Database session
            org_id (Optional[str]): The organization ID
            user_id (Optional[str]): The user ID from JWT claims
        """
        self.db = db
        self.org_id = org_id
        self.user_id = user_id
    
    # Auth Methods
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def generate_verification_code(self) -> str:
        """Generate 6-digit verification code"""
        return ''.join(secrets.choice(string.digits) for _ in range(6))
    
    def generate_token(self, length: int = 32) -> str:
        """Generate secure random token"""
        return secrets.token_urlsafe(length)
    
    def create_slug_from_name(self, name: str) -> str:
        """Create URL-friendly slug from organization name"""
        slug = name.lower().replace(' ', '-').replace('_', '-')
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')
        return slug[:50]  # Limit length
    
    # API 1: Signup
    def signup(self, email: str, password: str, username: Optional[str] = None, 
               profile: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create a new user account with email and password
        """
        current_time = int(time.time())
        
        # Check if user already exists
        existing_user = self.db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Check username uniqueness if provided
        if username:
            existing_username = self.db.query(User).filter(User.username == username).first()
            if existing_username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        # Hash password
        password_hash = self.hash_password(password)
        
        # Create user
        user = User(
            email=email,
            username=username,
            password_hash=password_hash,
            profile=profile or {},
            auth_provider=AuthProvider.EMAIL,
            status=UserStatus.PENDING,
            created_at=current_time,
            updated_at=current_time
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        verification_code = self.create_email_verification(user.id, email)
        verification_url = f"http://localhost:3000/auth/verify_signup?email={email}&code={verification_code.code}"


        mail_service = MailService()
        mail_service.send_signup_email(email, verification_url)
        
        return {
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "status": user.status.value,
            "message": "User created successfully. Please verify your email."
        }
    
    # API 2: Firebase Signup
    def signup_with_firebase(self, firebase_token: str, email: str, 
                           profile: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create user account using Firebase authentication
        """
        current_time = int(time.time())
        
        # Verify Firebase token (you'll need Firebase Admin SDK)
        firebase_uid = self.verify_firebase_token(firebase_token)
        
        # Check if user already exists
        existing_user = self.db.query(User).filter(
            or_(User.email == email, User.firebase_uid == firebase_uid)
        ).first()
        
        if existing_user:
            # Update existing user
            existing_user.firebase_uid = firebase_uid
            existing_user.email_verified = True
            existing_user.email_verified_at = current_time
            existing_user.status = UserStatus.ACTIVE
            existing_user.updated_at = current_time
            self.db.commit()
            user = existing_user
        else:
            # Create new user
            user = User(
                email=email,
                firebase_uid=firebase_uid,
                profile=profile or {},
                auth_provider=AuthProvider.FIREBASE,
                status=UserStatus.ACTIVE,
                email_verified=True,
                email_verified_at=current_time,
                created_at=current_time,
                updated_at=current_time
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        
        return {
            "user_id": user.id,
            "email": user.email,
            "status": user.status.value,
            "message": "User authenticated with Firebase successfully"
        }
    
    def verify_firebase_token(self, token: str) -> str:
        """
        Verify Firebase ID token and return user ID
        You'll need to implement this using Firebase Admin SDK
        """
        try:
            # This is a placeholder - implement with Firebase Admin SDK
            # from firebase_admin import auth
            # decoded_token = auth.verify_id_token(token)
            # return decoded_token['uid']
            
            # For now, return a mock UID (replace with actual implementation)
            return f"firebase_uid_{int(time.time())}"
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Firebase token"
            )
    
    # API 3: Resend Verification Email
    def resend_verification_email(self, email: str) -> Dict[str, str]:
        """
        Resend email verification code
        """
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified"
            )
        
        # Create new verification
        self.create_email_verification(user.id, email)
        
        return {"message": "Verification email sent successfully"}
    
    def create_email_verification(self, user_id: int, email: str):
        """Create email verification record and send email"""
        current_time = int(time.time())
        expires_at = current_time + (24 * 3600)  # 24 hours
        
        # Delete existing verifications for this email
        self.db.query(EmailVerification).filter(EmailVerification.email == email).delete()
        
        verification = EmailVerification(
            user_id=user_id,
            email=email,
            code=self.generate_verification_code(),
            token=self.generate_token(),
            expires_at=expires_at,
            created_at=current_time,
            updated_at=current_time
        )
        
        self.db.add(verification)
        self.db.commit()

        return verification
        
        # Send email (implement with your email service)
        # self.send_verification_email(email, verification.code)
    
    # API 4: Verify User Email
    def verify_user_email(self, email: str, code: str, user_id: int) -> Dict[str, str]:
        """
        Verify user email with code
        """
        current_time = int(time.time())
        
        verification = self.db.query(EmailVerification).filter(
            EmailVerification.email == email,
            EmailVerification.code == code,
            EmailVerification.user_id == user_id,
            EmailVerification.verified == False,
            EmailVerification.expires_at > current_time
        ).first()
        
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification code"
            )
        
        if verification.attempts >= verification.max_attempts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum verification attempts exceeded"
            )
        
        # Update verification
        verification.verified = True
        verification.verified_at = current_time
        verification.updated_at = current_time
        
        # Update user
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.email_verified = True
            user.email_verified_at = current_time
            user.status = UserStatus.ACTIVE
            user.updated_at = current_time
        
        self.db.commit()
        
        return {"message": "Email verified successfully"}
    
    # API 5: Get Associated Organizations
    def get_associated_organizations(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all organizations user is a member of
        """
        members = self.db.query(Member).filter(
            Member.user_id == user_id,
            Member.status == 'active'
        ).all()
        
        organizations = []
        for member in members:
            org = self.db.query(Organization).filter(Organization.id == member.organization_id).first()
            if org and org.status == OrganizationStatus.ACTIVE:
                organizations.append({
                    "id": org.id,
                    "name": org.name,
                    "slug": org.slug,
                    "role": member.role.value,
                    "joined_at": member.joined_at
                })
        
        return organizations
    
    # API 6: Get All Users for Organization
    def get_all_users_for_organization(self, org_id: int) -> List[Dict[str, Any]]:
        """
        Get all members of an organization
        """
        members = self.db.query(Member, User).join(
            User, Member.user_id == User.id
        ).filter(
            Member.organization_id == org_id,
            Member.status == 'active'
        ).all()
        
        result = []
        for member, user in members:
            result.append({
                "member_id": member.id,
                "user_id": user.id,
                "email": user.email,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": member.role.value,
                "status": member.status,
                "joined_at": member.joined_at,
                "last_activity_at": member.last_activity_at
            })
        
        return result
    
    # API 7: Get Roles by Scope
    def get_roles_by_scope(self) -> List[Dict[str, str]]:
        """
        Get available roles (since we're using enums)
        """
        return [
            {"role": "owner", "description": "Full access to organization"},
            {"role": "admin", "description": "Administrative access"},
            {"role": "member", "description": "Standard member access"},
            {"role": "viewer", "description": "Read-only access"}
        ]
    
    # API 8: Create Organization
    def create_organization(self, name: str, user_id: int) -> Dict[str, Any]:
        """
        Create a new organization
        """
        current_time = int(time.time())
        
        # Generate unique slug
        base_slug = self.create_slug_from_name(name)
        slug = base_slug
        counter = 1
        
        while self.db.query(Organization).filter(Organization.slug == slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Create organization
        organization = Organization(
            name=name,
            slug=slug,
            status=OrganizationStatus.ACTIVE,
            created_by=user_id,
            created_at=current_time,
            updated_at=current_time
        )
        
        self.db.add(organization)
        self.db.commit()
        self.db.refresh(organization)
        
        # Add creator as owner
        member = Member(
            user_id=user_id,
            organization_id=organization.id,
            role=Role.OWNER,
            status='active',
            created_by=user_id,
            created_at=current_time,
            updated_at=current_time,
            joined_at=current_time
        )
        
        self.db.add(member)
        self.db.commit()
        
        return {
            "id": organization.id,
            "name": organization.name,
            "slug": organization.slug,
            "role": "owner"
        }
    
    # API 9: Invite User to Organization
    def invite_user_to_organization(self, org_id: int, name: str, email: str, 
                                   role: str, invited_by: int) -> Dict[str, Any]:
        """
        Invite user to organization
        """
        current_time = int(time.time())
        expires_at = current_time + (7 * 24 * 3600)  # 7 days
        
        # Validate role
        try:
            role_enum = Role(role.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role"
            )
        
        # Check if user is already a member
        existing_member = self.db.query(Member).join(User).filter(
            User.email == email,
            Member.organization_id == org_id
        ).first()
        
        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this organization"
            )
        
        # Check if invitation already exists
        existing_invite = self.db.query(OrganizationInvite).filter(
            OrganizationInvite.email == email,
            OrganizationInvite.organization_id == org_id,
            OrganizationInvite.status == InviteStatus.PENDING
        ).first()
        
        if existing_invite:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pending invitation already exists"
            )
        
        # Create invitation
        invitation = OrganizationInvite(
            organization_id=org_id,
            email=email,
            name=name,
            role=role_enum,
            invitation_token=self.generate_token(),
            expires_at=expires_at,
            invited_by=invited_by,
            created_at=current_time,
            updated_at=current_time
        )
        
        self.db.add(invitation)
        self.db.commit()
        self.db.refresh(invitation)

        invite_url = f"http://localhost:3000/verify/user_to_workspace?email={email}&code={invitation.invitation_token}&user_tenant_id={invitation.organization_id}"

        mail_service = MailService()
        mail_service.send_invite_email(email, invite_url)
        
        # Send invitation email (implement with your email service)
        # self.send_invitation_email(email, invitation.invitation_token)
        
        return {
            "id": invitation.id,
            "email": invitation.email,
            "role": invitation.role.value,
            "status": invitation.status.value,
            "expires_at": invitation.expires_at
        }
    
    # API 10: Remove User from Organization
    def remove_user_from_organization(self, org_id: int, user_id: int) -> Dict[str, str]:
        """
        Remove user from organization
        """
        member = self.db.query(Member).filter(
            Member.user_id == user_id,
            Member.organization_id == org_id
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )
        
        # Don't allow removing the last owner
        if member.role == Role.OWNER:
            owner_count = self.db.query(Member).filter(
                Member.organization_id == org_id,
                Member.role == Role.OWNER,
                Member.status == 'active'
            ).count()
            
            if owner_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove the last owner"
                )
        
        self.db.delete(member)
        self.db.commit()
        
        return {"message": "Member removed successfully"}
    
    # API 11: Update Member Role
    def update_member_role(self, member_id: int, new_role: str) -> Dict[str, Any]:
        """
        Update member role
        """
        # Validate role
        try:
            role_enum = Role(new_role.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role"
            )
        
        member = self.db.query(Member).filter(Member.id == member_id).first()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )
        
        # Don't allow changing the last owner
        if member.role == Role.OWNER and role_enum != Role.OWNER:
            owner_count = self.db.query(Member).filter(
                Member.organization_id == member.organization_id,
                Member.role == Role.OWNER,
                Member.status == 'active'
            ).count()
            
            if owner_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot change role of the last owner"
                )
        
        member.role = role_enum
        member.updated_at = int(time.time())
        self.db.commit()
        
        return {
            "member_id": member.id,
            "role": member.role.value,
            "message": "Role updated successfully"
        }
    
    # API 12: Login
    def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        User login with email and password
        """
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not user.password_hash or not self.verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account not active. Please verify your email."
            )
        
        # Update last login
        user.last_login_at = int(time.time())
        self.db.commit()
        
        # Get user's organizations
        organizations = self.get_associated_organizations(user.id)
        
        # Create JWT token (without org context for now)
        access_token = jwt_manager.create_access_token(
            user_id=user.id,
            email=user.email
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "email": user.email,
            "organizations": organizations
        }
    
    # API 13: Forgot Password
    def forgot_password(self, email: str) -> Dict[str, str]:
        """
        Send password reset email
        """
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            # Don't reveal if user exists
            return {"message": "If the email exists, you will receive a password reset link"}
        
        current_time = int(time.time())
        expires_at = current_time + (3600)  # 1 hour
        
        # Delete existing reset tokens for this user
        self.db.query(PasswordReset).filter(PasswordReset.user_id == user.id).delete()
        
        # Create password reset
        reset = PasswordReset(
            user_id=user.id,
            email=email,
            token=self.generate_token(),
            expires_at=expires_at,
            created_at=current_time
        )
        
        self.db.add(reset)
        self.db.commit()

        verification_url = f"http://localhost:3000/auth/forgot-password?token={reset.token}&email={user.email}"

        mail_service = MailService()
        mail_service.send_forgot_password_email(email, verification_url)
        
        # Send password reset email (implement with your email service)
        # self.send_password_reset_email(email, reset.token)
        
        return {"message": "If the email exists, you will receive a password reset link"}
    
    # API 14: Accept Forgot Password (Reset Password)
    def accept_forgot_password(self, email: str, password: str, token: str) -> Dict[str, str]:
        """
        Reset password with token
        """
        current_time = int(time.time())
        
        reset = self.db.query(PasswordReset).filter(
            PasswordReset.email == email,
            PasswordReset.token == token,
            PasswordReset.used == False,
            PasswordReset.expires_at > current_time
        ).first()
        
        if not reset:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Update user password
        user = self.db.query(User).filter(User.id == reset.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.password_hash = self.hash_password(password)
        user.updated_at = current_time
        
        # Mark reset as used
        reset.used = True
        reset.used_at = current_time
        
        self.db.commit()
        
        return {"message": "Password reset successfully"}