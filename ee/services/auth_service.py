from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional, Dict, Any
from uuid import UUID
import time
from fastapi import HTTPException, status

from core.models.enums import UserStatus, Role, InviteStatus, AuthProvider, AccessRequestStatus, OrganizationStatus
from core.utils.security import hash_password, verify_password, generate_verification_code, generate_token
from core.services.email_service import MailService

from ee.models.user import User
from ee.models.email_verification import EmailVerification
from ee.models.password_reset import PasswordReset
from ee.models.organization import Organization
from ee.models.member import Member
from ee.models.organization_invite import OrganizationInvite
from ee.models.organization_access_request import OrganizationAccessRequest
from ee.config import ee_settings
from ee.middleware.auth import ee_jwt_manager


class EEAuthService:
    def __init__(self, db: Session, org_id: Optional[UUID] = None, user_id: Optional[int] = None):
        self.db = db
        self._org_id = org_id
        self._user_id = user_id

    def create_slug_from_name(self, name: str) -> str:
        slug = name.lower().replace(' ', '-').replace('_', '-')
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')
        return slug[:50]

    def signup(self, email: str, password: str, username: Optional[str] = None,
               profile: Optional[Dict] = None, org_name: Optional[str] = None) -> Dict[str, Any]:
        current_time = int(time.time())

        existing_user = self.db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

        if username:
            existing_username = self.db.query(User).filter(User.username == username).first()
            if existing_username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )

        password_hash = hash_password(password)

        user_profile = profile or {}
        if org_name:
            user_profile["org_name"] = org_name

        user = User(
            email=email,
            username=username,
            password_hash=password_hash,
            profile=user_profile,
            auth_provider=AuthProvider.EMAIL,
            status=UserStatus.PENDING,
            created_at=current_time,
            updated_at=current_time
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        verification = self.create_email_verification(user.id, email)
        verification_url = f"{ee_settings.APPLICATION_URL}/auth/verify_signup?email={email}&code={verification.code}&user_id={user.id}"

        mail_service = MailService()
        mail_service.send_signup_email(email, verification_url, username or email.split('@')[0])

        return {
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "status": user.status.value,
            "message": "User created successfully. Please verify your email."
        }

    def signup_with_firebase(self, firebase_token: str, email: str,
                             profile: Optional[Dict] = None) -> Dict[str, Any]:
        current_time = int(time.time())

        firebase_uid = self.verify_firebase_token(firebase_token)

        existing_user = self.db.query(User).filter(
            or_(User.email == email, User.firebase_uid == firebase_uid)
        ).first()

        if existing_user:
            existing_user.firebase_uid = firebase_uid
            existing_user.email_verified = True
            existing_user.email_verified_at = current_time
            existing_user.status = UserStatus.ACTIVE
            existing_user.updated_at = current_time
            self.db.commit()
            user = existing_user
        else:
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
        try:
            return f"firebase_uid_{int(time.time())}"
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Firebase token"
            )

    def create_email_verification(self, user_id: int, email: str) -> EmailVerification:
        current_time = int(time.time())
        expires_at = current_time + (24 * 3600)

        self.db.query(EmailVerification).filter(EmailVerification.email == email).delete()

        verification = EmailVerification(
            user_id=user_id,
            email=email,
            code=generate_verification_code(),
            token=generate_token(),
            expires_at=expires_at,
            created_at=current_time,
            updated_at=current_time
        )

        self.db.add(verification)
        self.db.commit()

        return verification

    def resend_verification_email(self, email: str) -> Dict[str, str]:
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

        verification = self.create_email_verification(user.id, email)
        verification_url = f"{ee_settings.APPLICATION_URL}/auth/verify_signup?email={email}&code={verification.code}&user_id={user.id}"

        mail_service = MailService()
        mail_service.send_signup_email(email, verification_url, user.username or email.split('@')[0])

        return {"message": "Verification email sent successfully"}

    def verify_user_email(self, email: str, code: str, user_id: int) -> Dict[str, str]:
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

        verification.verified = True
        verification.verified_at = current_time
        verification.updated_at = current_time

        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.email_verified = True
            user.email_verified_at = current_time
            user.status = UserStatus.ACTIVE
            user.updated_at = current_time

            org_name = user.profile.get("org_name") if user.profile else None
            if org_name:
                self.create_organization(org_name, user.id)

        self.db.commit()

        return {"message": "Email verified successfully"}

    def login(self, email: str, password: str) -> Dict[str, Any]:
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        if not user.password_hash or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        if user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account not active. Please verify your email."
            )

        user.last_login_at = int(time.time())
        self.db.commit()

        organizations = self.get_associated_organizations(user.id)

        access_token = ee_jwt_manager.create_access_token(
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

    def forgot_password(self, email: str) -> Dict[str, str]:
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return {"message": "If the email exists, you will receive a password reset link"}

        current_time = int(time.time())
        expires_at = current_time + 3600

        self.db.query(PasswordReset).filter(PasswordReset.user_id == user.id).delete()

        reset = PasswordReset(
            user_id=user.id,
            email=email,
            token=generate_token(),
            expires_at=expires_at,
            created_at=current_time,
            updated_at=current_time
        )

        self.db.add(reset)
        self.db.commit()

        verification_url = f"{ee_settings.APPLICATION_URL}/auth/reset-password?token={reset.token}&email={user.email}"

        mail_service = MailService()
        mail_service.send_forgot_password_email(email, verification_url)

        return {"message": "If the email exists, you will receive a password reset link"}

    def accept_forgot_password(self, email: str, password: str, token: str) -> Dict[str, str]:
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

        user = self.db.query(User).filter(User.id == reset.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user.password_hash = hash_password(password)
        user.updated_at = current_time

        reset.used = True
        reset.used_at = current_time

        self.db.commit()

        return {"message": "Password reset successfully"}

    def check_organization_exists(self, name: str) -> Dict[str, Any]:
        slug = self.create_slug_from_name(name)
        org = self.db.query(Organization).filter(Organization.slug == slug).first()

        if org:
            return {"exists": True, "organization": {"id": str(org.id), "name": org.name, "slug": org.slug}}
        return {"exists": False, "organization": None}

    def create_organization(self, name: str, user_id: int) -> Dict[str, Any]:
        current_time = int(time.time())
        slug = self.create_slug_from_name(name)

        existing_org = self.db.query(Organization).filter(Organization.slug == slug).first()
        if existing_org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization with this name already exists"
            )

        org = Organization(
            name=name,
            slug=slug,
            created_by=user_id,
            created_at=current_time,
            updated_at=current_time
        )

        self.db.add(org)
        self.db.commit()
        self.db.refresh(org)

        member = Member(
            user_id=user_id,
            organization_id=org.id,
            role=Role.OWNER,
            status='active',
            created_by=user_id,
            joined_at=current_time,
            created_at=current_time,
            updated_at=current_time
        )

        self.db.add(member)
        self.db.commit()

        return {
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "role": "owner"
        }

    def get_associated_organizations(self, user_id: int) -> List[Dict[str, Any]]:
        members = self.db.query(Member, Organization).join(
            Organization, Member.organization_id == Organization.id
        ).filter(
            Member.user_id == user_id,
            Member.status == 'active'
        ).all()

        organizations = []
        for member, org in members:
            organizations.append({
                "id": str(org.id),
                "name": org.name,
                "slug": org.slug,
                "role": member.role.value,
                "joined_at": member.joined_at
            })

        return organizations

    def switch_organization(self, user_id: int, org_id: UUID) -> Dict[str, Any]:
        member = self.db.query(Member).filter(
            Member.user_id == user_id,
            Member.organization_id == org_id,
            Member.status == 'active'
        ).first()

        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this organization"
            )

        org = self.db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        access_token = ee_jwt_manager.create_access_token(
            user_id=user.id,
            email=user.email,
            org_id=str(org_id),
            role=member.role.value
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "organization": {
                "id": str(org.id),
                "name": org.name,
                "slug": org.slug
            },
            "role": member.role.value
        }

    def get_all_users_for_organization(self, org_id: UUID) -> List[Dict[str, Any]]:
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

    def get_all_invited_users_for_organization(self, org_id: UUID) -> List[Dict[str, Any]]:
        invites = self.db.query(OrganizationInvite).filter(
            OrganizationInvite.organization_id == org_id,
            OrganizationInvite.status == InviteStatus.PENDING
        ).all()

        result = []
        for invite in invites:
            result.append({
                "member_id": invite.id,
                "email": invite.email,
                "name": invite.name,
                "role": invite.role.value,
                "status": invite.status.value,
            })

        return result

    def invite_user_to_organization(self, org_id: UUID, name: str, email: str,
                                    role: str, invited_by: int) -> Dict[str, Any]:
        current_time = int(time.time())
        expires_at = current_time + (7 * 24 * 3600)

        try:
            role_enum = Role(role.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role"
            )

        existing_member = (
            self.db.query(Member)
            .join(User, Member.user_id == User.id)
            .filter(
                User.email == email,
                Member.organization_id == org_id
            )
            .first()
        )

        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this organization"
            )

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

        invitation = OrganizationInvite(
            organization_id=org_id,
            email=email,
            name=name,
            role=role_enum,
            invitation_token=generate_token(),
            expires_at=expires_at,
            invited_by=invited_by,
            created_at=current_time,
            updated_at=current_time
        )

        self.db.add(invitation)
        self.db.commit()
        self.db.refresh(invitation)

        invite_url = f"{ee_settings.APPLICATION_URL}/verify/user_to_workspace?email={email}&code={invitation.invitation_token}&user_tenant_id={org_id}"

        mail_service = MailService()
        mail_service.send_invite_email(email, invite_url)

        return {
            "id": invitation.id,
            "email": invitation.email,
            "role": invitation.role.value,
            "status": invitation.status.value,
            "expires_at": invitation.expires_at
        }

    def accept_invitation(self, email: str, token: str, org_id: UUID) -> Dict[str, Any]:
        current_time = int(time.time())

        invitation = self.db.query(OrganizationInvite).filter(
            OrganizationInvite.email == email,
            OrganizationInvite.invitation_token == token,
            OrganizationInvite.organization_id == org_id,
            OrganizationInvite.status == InviteStatus.PENDING,
            OrganizationInvite.expires_at > current_time
        ).first()

        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invitation"
            )

        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please sign up first before accepting the invitation"
            )

        if user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please verify your email before accepting the invitation"
            )

        existing_member = self.db.query(Member).filter(
            Member.user_id == user.id,
            Member.organization_id == org_id
        ).first()

        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already a member of this organization"
            )

        org = self.db.query(Organization).filter(Organization.id == org_id).first()

        member = Member(
            user_id=user.id,
            organization_id=org_id,
            role=invitation.role,
            status='active',
            created_by=invitation.invited_by,
            created_at=current_time,
            updated_at=current_time,
            joined_at=current_time
        )

        self.db.add(member)

        invitation.status = InviteStatus.ACCEPTED
        invitation.accepted_by = user.id
        invitation.accepted_at = current_time
        invitation.updated_at = current_time

        self.db.commit()

        return {
            "message": "Invitation accepted successfully",
            "organization": {
                "id": str(org.id),
                "name": org.name,
                "slug": org.slug
            },
            "role": invitation.role.value
        }

    def remove_user_from_organization(self, org_id: UUID, user_id: int) -> Dict[str, str]:
        member = self.db.query(Member).filter(
            Member.user_id == user_id,
            Member.organization_id == org_id
        ).first()

        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )

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

    def update_member_role(self, org_id: UUID, member_id: int, new_role: str) -> Dict[str, Any]:
        try:
            role_enum = Role(new_role.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role"
            )

        member = self.db.query(Member).filter(
            Member.id == member_id,
            Member.organization_id == org_id
        ).first()

        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )

        current_user_member = self.db.query(Member).filter(
            Member.user_id == self._user_id,
            Member.organization_id == org_id,
            Member.status == 'active'
        ).first()

        if not current_user_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this organization"
            )

        if current_user_member.role == Role.ADMIN:
            if member.role == Role.OWNER:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admins cannot modify owner roles"
                )
            if role_enum == Role.OWNER:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admins cannot promote users to owner"
                )

        if member.role == Role.OWNER and role_enum != Role.OWNER:
            owner_count = self.db.query(Member).filter(
                Member.organization_id == org_id,
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

    def get_organization_settings(self, org_id: UUID) -> Dict[str, Any]:
        org = self.db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        return org.settings or {}

    def update_organization_settings(self, org_id: UUID, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        org = self.db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        org.settings = new_settings
        org.updated_at = int(time.time())
        self.db.commit()

        return {"message": "Settings updated successfully", "settings": new_settings}

    def request_organization_access(self, user_id: int, org_id: UUID, message: str = None) -> Dict[str, Any]:
        current_time = int(time.time())

        existing_member = self.db.query(Member).filter(
            Member.user_id == user_id,
            Member.organization_id == org_id
        ).first()

        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already a member of this organization"
            )

        existing_request = self.db.query(OrganizationAccessRequest).filter(
            OrganizationAccessRequest.user_id == user_id,
            OrganizationAccessRequest.organization_id == org_id,
            OrganizationAccessRequest.status == AccessRequestStatus.PENDING
        ).first()

        if existing_request:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have a pending access request"
            )

        access_request = OrganizationAccessRequest(
            user_id=user_id,
            organization_id=org_id,
            message=message,
            created_at=current_time,
            updated_at=current_time
        )

        self.db.add(access_request)
        self.db.commit()
        self.db.refresh(access_request)

        return {
            "id": access_request.id,
            "status": access_request.status.value,
            "message": "Access request submitted successfully"
        }

    def get_access_requests(self, org_id: UUID) -> List[Dict[str, Any]]:
        requests = self.db.query(OrganizationAccessRequest, User).join(
            User, OrganizationAccessRequest.user_id == User.id
        ).filter(
            OrganizationAccessRequest.organization_id == org_id,
            OrganizationAccessRequest.status == AccessRequestStatus.PENDING
        ).all()

        return [{
            "id": req.id,
            "user_id": req.user_id,
            "email": user.email,
            "username": user.username,
            "message": req.message,
            "created_at": req.created_at
        } for req, user in requests]

    def handle_access_request(self, org_id: UUID, request_id: int, action: str, reviewer_id: int) -> Dict[str, str]:
        current_time = int(time.time())

        access_request = self.db.query(OrganizationAccessRequest).filter(
            OrganizationAccessRequest.id == request_id,
            OrganizationAccessRequest.organization_id == org_id
        ).first()

        if not access_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Access request not found"
            )

        if access_request.status != AccessRequestStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This request has already been processed"
            )

        if action == "approve":
            access_request.status = AccessRequestStatus.APPROVED
            access_request.reviewed_by = reviewer_id
            access_request.reviewed_at = current_time
            access_request.updated_at = current_time

            member = Member(
                user_id=access_request.user_id,
                organization_id=org_id,
                role=Role.MEMBER,
                status='active',
                created_by=reviewer_id,
                created_at=current_time,
                updated_at=current_time,
                joined_at=current_time
            )
            self.db.add(member)
            self.db.commit()

            return {"message": "Access request approved"}

        elif action == "reject":
            access_request.status = AccessRequestStatus.REJECTED
            access_request.reviewed_by = reviewer_id
            access_request.reviewed_at = current_time
            access_request.updated_at = current_time
            self.db.commit()

            return {"message": "Access request rejected"}

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid action. Use 'approve' or 'reject'"
            )

    def get_roles_by_scope(self) -> List[Dict[str, str]]:
        return [
            {"role": "owner", "description": "Full access to organization"},
            {"role": "admin", "description": "Administrative access"},
            {"role": "member", "description": "Standard member access"},
            {"role": "viewer", "description": "Read-only access"}
        ]
