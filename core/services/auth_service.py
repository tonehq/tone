import logging
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional, Dict, Any
import time
from uuid import UUID
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

from core.services.base import BaseService
from core.models.user import User
from core.models.member import Member
from core.models.organization import Organization
from core.models.organization_invite import OrganizationInvite
from core.models.email_verification import EmailVerification
from core.models.password_reset import PasswordReset
from core.models.organization_access_request import OrganizationAccessRequest
from core.models.enums import UserStatus, Role, InviteStatus, AuthProvider, AccessRequestStatus, OrganizationStatus
from core.middleware.auth import jwt_manager
from core.utils.security import hash_password, verify_password, generate_verification_code, generate_token
from core.services.email_service import MailService
from core.config import settings
import uuid as uuid_lib


class AuthService(BaseService):
    def __init__(self, db: Session, user_id: Optional[int] = None, org_id=None):
        super().__init__(db, user_id, org_id=org_id)

    def ensure_default_organization(self, created_by: int) -> Organization:
        from uuid import UUID
        default_org_id = UUID(settings.DEFAULT_ORG_ID)
        existing = self.db.query(Organization).filter(Organization.id == default_org_id).first()
        if existing:
            return existing

        current_time = int(time.time())
        org = Organization(
            id=default_org_id,
            name="Default Organization",
            slug="default",
            description="Default organization",
            status=OrganizationStatus.ACTIVE,
            created_by=created_by,
            subscription_plan="free",
            subscription_status="active",
            created_at=current_time,
            updated_at=current_time,
        )
        self.db.add(org)
        self.db.commit()
        return org

    def signup(self, email: str, password: str, username: Optional[str] = None,
               profile: Optional[Dict] = None) -> Dict[str, Any]:
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

        verification = self.create_email_verification(user.id, email)
        verification_url = f"{settings.APPLICATION_URL}/auth/verify_signup?email={email}&code={verification.code}&user_id={user.id}"

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
        verification_url = f"{settings.APPLICATION_URL}/auth/verify_signup?email={email}&code={verification.code}&user_id={user.id}"

        mail_service = MailService()
        mail_service.send_signup_email(email, verification_url, user.username or email.split('@')[0])

        return {"message": "Verification email sent successfully"}

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

            self.ensure_default_organization(user.id)

            existing_member_count = self.db.query(Member).filter(
                Member.organization_id == settings.DEFAULT_ORG_ID
            ).count()
            role = Role.OWNER if existing_member_count == 0 else Role.MEMBER

            self.upsert(
                model=Member,
                values={
                    "user_id": user.id,
                    "role": role,
                    "status": "active",
                    "created_by": user.id,
                    "created_at": current_time,
                    "updated_at": current_time,
                    "joined_at": current_time,
                    "organization_id": settings.DEFAULT_ORG_ID,
                },
                conflict_fields=["organization_id", "user_id"],
                update_fields=["role", "status", "updated_at", "joined_at"],
                auto_commit=False,
            )

        self.db.commit()

        return {"message": "Email verified successfully"}

    def get_all_users_for_organization(self) -> List[Dict[str, Any]]:
        members = self.db.query(Member, User).join(
            User, Member.user_id == User.id
        ).filter(
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

    def get_all_invited_users_for_organization(self) -> List[Dict[str, Any]]:
        invites = self.db.query(OrganizationInvite).filter(
            OrganizationInvite.status == InviteStatus.PENDING
        ).all()

        result = []
        for invite in invites:
            result.append({
                "member_id": invite.id,
                "email": invite.email,
                "username": invite.name,
                "name": invite.name,
                "role": invite.role.value,
                "status": invite.status.value,
            })

        return result

    def get_roles_by_scope(self) -> List[Dict[str, str]]:
        return [
            {"role": "owner", "description": "Full access to organization"},
            {"role": "admin", "description": "Administrative access"},
            {"role": "member", "description": "Standard member access"},
            {"role": "viewer", "description": "Read-only access"}
        ]

    def invite_user_to_organization(self, name: str, email: str,
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

        existing_user = self.db.query(User).filter(User.email == email).first()

        if existing_user:
            existing_member = (
                self.db.query(Member)
                .filter(Member.user_id == existing_user.id)
                .first()
            )
            if existing_member:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User is already a member of the organization"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists"
            )

        # Clean up expired invites for same email before checking for pending duplicates
        self.db.query(OrganizationInvite).filter(
            OrganizationInvite.email == email,
            OrganizationInvite.status == InviteStatus.PENDING,
            OrganizationInvite.expires_at <= current_time
        ).delete()
        self.db.flush()

        existing_invite = self.db.query(OrganizationInvite).filter(
            OrganizationInvite.email == email,
            OrganizationInvite.status == InviteStatus.PENDING
        ).first()

        if existing_invite:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pending invitation already exists"
            )

        invite_uuid = uuid_lib.uuid4()
        invitation_token = generate_token()
        self.upsert(
            model=OrganizationInvite,
            values={
                "uuid": invite_uuid,
                "email": email,
                "name": name,
                "role": role_enum,
                "invitation_token": invitation_token,
                "expires_at": expires_at,
                "invited_by": invited_by,
                "created_at": current_time,
                "updated_at": current_time,
            },
            conflict_fields=["uuid"],
            update_fields=["name", "role", "invitation_token", "expires_at", "updated_at"],
        )
        invitation = self.db.query(OrganizationInvite).filter(OrganizationInvite.uuid == invite_uuid).first()

        invite_url = (
            f"{settings.APPLICATION_URL}/accept-invite"
            f"?token={invitation.invitation_token}"
        )

        mail_service = MailService()
        mail_service.send_invite_email(email, invite_url)

        return {
            "id": invitation.id,
            "email": invitation.email,
            "role": invitation.role.value,
            "status": invitation.status.value,
            "expires_at": invitation.expires_at
        }

    def accept_invitation(self, email: str, token: str) -> Dict[str, Any]:
        current_time = int(time.time())

        invitation = self.db.query(OrganizationInvite).filter(
            OrganizationInvite.email == email,
            OrganizationInvite.invitation_token == token,
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
            Member.user_id == user.id
        ).first()

        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already a member"
            )

        org_id = invitation.organization_id if invitation.organization_id else settings.DEFAULT_ORG_ID
        self.upsert(
            model=Member,
            values={
                "user_id": user.id,
                "role": invitation.role,
                "status": "active",
                "created_by": invitation.invited_by,
                "created_at": current_time,
                "updated_at": current_time,
                "joined_at": current_time,
                "organization_id": org_id,
            },
            conflict_fields=["organization_id", "user_id"],
            update_fields=["role", "status", "updated_at", "joined_at"],
            auto_commit=False,
        )

        invitation.status = InviteStatus.ACCEPTED
        invitation.updated_at = current_time

        self.db.commit()

        return {
            "message": "Invitation accepted successfully",
            "role": invitation.role.value
        }

    def validate_invitation_token(self, email: str, token: str) -> Dict[str, Any]:
        current_time = int(time.time())

        invitation = self.db.query(OrganizationInvite).filter(
            OrganizationInvite.email == email,
            OrganizationInvite.invitation_token == token,
            OrganizationInvite.status == InviteStatus.PENDING,
            OrganizationInvite.expires_at > current_time
        ).first()

        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invitation"
            )

        existing_user = self.db.query(User).filter(User.email == email).first()
        user_exists = existing_user is not None
        has_password = existing_user.password_hash is not None if existing_user else False

        return {
            "valid": True,
            "email": invitation.email,
            "name": invitation.name,
            "role": invitation.role.value,
            "user_exists": user_exists,
            "has_password": has_password
        }

    def accept_invitation_with_password(self, email: str, token: str,
                                        password: str) -> Dict[str, Any]:
        current_time = int(time.time())

        invitation = self.db.query(OrganizationInvite).filter(
            OrganizationInvite.email == email,
            OrganizationInvite.invitation_token == token,
            OrganizationInvite.status == InviteStatus.PENDING,
            OrganizationInvite.expires_at > current_time
        ).first()

        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invitation"
            )

        existing_user = self.db.query(User).filter(User.email == email).first()

        # Existing account with a password — skip the password parameter and
        # just attach the membership row so the user shows up in the new org
        # next time they sign in.
        if existing_user and existing_user.password_hash is not None:
            user = existing_user
            self.db.flush()
            org_id = invitation.organization_id if invitation.organization_id else settings.DEFAULT_ORG_ID
            self.upsert(
                model=Member,
                values={
                    "user_id": user.id,
                    "role": invitation.role,
                    "status": "active",
                    "created_by": invitation.invited_by,
                    "created_at": current_time,
                    "updated_at": current_time,
                    "joined_at": current_time,
                    "organization_id": org_id,
                },
                conflict_fields=["organization_id", "user_id"],
                update_fields=["role", "status", "updated_at", "joined_at"],
                auto_commit=False,
            )
            invitation.status = InviteStatus.ACCEPTED
            invitation.accepted_by = user.id
            invitation.accepted_at = current_time
            invitation.updated_at = current_time
            self.db.commit()
            return {
                "message": "You have been added to the organization. Please sign in to continue.",
                "account_exists": True,
                "email": email,
                "requires_login": True,
            }

        password_hash = hash_password(password)

        if existing_user and existing_user.password_hash is None:
            existing_user.password_hash = password_hash
            existing_user.updated_at = current_time
            user = existing_user
            self.db.flush()
        else:
            user = User(
                email=email,
                username=invitation.name,
                password_hash=password_hash,
                profile={},
                auth_provider=AuthProvider.EMAIL,
                status=UserStatus.ACTIVE,
                email_verified=True,
                email_verified_at=current_time,
                created_at=current_time,
                updated_at=current_time
            )

            self.db.add(user)
            self.db.flush()

        org_id = invitation.organization_id if invitation.organization_id else settings.DEFAULT_ORG_ID
        self.upsert(
            model=Member,
            values={
                "user_id": user.id,
                "role": invitation.role,
                "status": "active",
                "created_by": invitation.invited_by,
                "created_at": current_time,
                "updated_at": current_time,
                "joined_at": current_time,
                "organization_id": org_id,
            },
            conflict_fields=["organization_id", "user_id"],
            update_fields=["role", "status", "updated_at", "joined_at"],
            auto_commit=False,
        )

        invitation.status = InviteStatus.ACCEPTED
        invitation.accepted_by = user.id
        invitation.accepted_at = current_time
        invitation.updated_at = current_time

        self.db.commit()

        return {
            "message": "Account created and invitation accepted successfully",
            "role": invitation.role.value
        }

    def cancel_invitation(self, invite_id: int) -> Dict[str, str]:
        invitation = self.db.query(OrganizationInvite).filter(
            OrganizationInvite.id == invite_id,
            OrganizationInvite.status == InviteStatus.PENDING
        ).first()

        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pending invitation not found"
            )

        self.db.delete(invitation)
        self.db.commit()

        return {"message": "Invitation cancelled successfully"}

    def resend_invitation(self, invite_id: int) -> Dict[str, str]:
        invitation = (
            self.db.query(OrganizationInvite)
            .filter(
                OrganizationInvite.id == invite_id,
                OrganizationInvite.status == InviteStatus.PENDING,
            )
            .first()
        )
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pending invitation not found",
            )

        current_time = int(time.time())
        # Rotate the token + extend expiry so the previous email link stops
        # working once a new one is sent.
        invitation.invitation_token = generate_token()
        invitation.expires_at = current_time + (7 * 24 * 3600)
        invitation.updated_at = current_time
        self.db.commit()
        self.db.refresh(invitation)

        invite_url = (
            f"{settings.APPLICATION_URL}/accept-invite"
            f"?token={invitation.invitation_token}"
        )
        try:
            MailService().send_invite_email(invitation.email, invite_url)
        except Exception:
            logger.exception(
                "Failed to resend invitation email to %s", invitation.email
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Couldn't send the invitation email. Please try again.",
            )

        return {"message": "Invitation re-sent successfully"}

    def remove_user_from_organization(self, user_id: int) -> Dict[str, str]:
        member = self.db.query(Member).filter(
            Member.user_id == user_id
        ).first()

        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )

        if member.role == Role.OWNER:
            owner_count = self.db.query(Member).filter(
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

    def update_member_role(self, member_id: int, new_role: str) -> Dict[str, Any]:
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

        current_user_member = self.db.query(Member).filter(
            Member.user_id == self._user_id,
            Member.status == 'active'
        ).first()

        if not current_user_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member"
            )

        current_user_role = current_user_member.role

        if current_user_role == Role.ADMIN:
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

    def get_organization_settings(self) -> Dict[str, Any]:
        return {}

    def update_organization_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        return {"message": "Settings updated successfully", "settings": new_settings}

    def get_access_requests(self) -> List[Dict[str, Any]]:
        requests = self.db.query(OrganizationAccessRequest, User).join(
            User, OrganizationAccessRequest.user_id == User.id
        ).filter(
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

    def handle_access_request(self, request_id: int, action: str, reviewer_id: int) -> Dict[str, str]:
        current_time = int(time.time())

        access_request = self.db.query(OrganizationAccessRequest).filter(
            OrganizationAccessRequest.id == request_id
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

            org_id = access_request.organization_id if access_request.organization_id else settings.DEFAULT_ORG_ID
            self.upsert(
                model=Member,
                values={
                    "user_id": access_request.user_id,
                    "role": Role.MEMBER,
                    "status": "active",
                    "created_by": reviewer_id,
                    "created_at": current_time,
                    "updated_at": current_time,
                    "joined_at": current_time,
                    "organization_id": org_id,
                },
                conflict_fields=["organization_id", "user_id"],
                update_fields=["role", "status", "updated_at", "joined_at"],
                auto_commit=False,
            )
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

        # Get user's organization membership
        member = self.db.query(Member).filter(
            Member.user_id == user.id,
            Member.status == 'active'
        ).first()

        org_id = None
        role = None
        if member:
            org_id = str(member.organization_id)
            role = member.role.value

        access_token = jwt_manager.create_access_token(
            user_id=user.id,
            email=user.email,
            org_id=org_id,
            role=role
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "email": user.email,
            "org_id": org_id,
            "role": role
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

        verification_url = (
            f"{settings.APPLICATION_URL}/reset-password"
            f"?token={reset.token}&email={user.email}"
        )

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

    # ─────────────────────────────────────────────────────────────────────────
    # tone-test shaped helpers
    # New surface area; mirrors tone-test's AuthService contract.
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def user_to_dict(user: User) -> Dict[str, Any]:
        profile = user.profile or {}
        return {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name or profile.get("first_name"),
            "last_name": user.last_name or profile.get("last_name"),
            "avatar_url": user.avatar_url,
            "is_active": user.status == UserStatus.ACTIVE,
            "is_verified": bool(user.email_verified),
            "auth_provider": user.auth_provider.value if user.auth_provider else None,
            "last_login_at": user.last_login_at,
        }

    @staticmethod
    def org_to_dict(org: Optional[Organization]) -> Optional[Dict[str, Any]]:
        if not org:
            return None
        return {
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "description": org.description,
            "logo_url": org.logo_url,
            "subscription_plan": org.subscription_plan,
            "subscription_status": org.subscription_status,
            "status": org.status.value if org.status else None,
        }

    def _membership_for(self, user_id: int) -> Optional[Member]:
        return (
            self.db.query(Member)
            .filter(Member.user_id == user_id, Member.status == "active")
            .first()
        )

    def _build_auth_tokens(self, user: User, organization: Optional[Organization] = None,
                            email_verification_token: Optional[str] = None) -> Dict[str, Any]:
        member = self._membership_for(user.id)
        org_id = str(organization.id) if organization else (
            str(member.organization_id) if member else None
        )
        role = member.role.value if member else None

        access_token = jwt_manager.create_access_token(
            user_id=user.id, email=user.email, org_id=org_id, role=role
        )
        refresh_token = jwt_manager.create_refresh_token(
            user_id=user.id, email=user.email, org_id=org_id
        )
        org = organization or (
            self.db.query(Organization).filter(Organization.id == member.organization_id).first()
            if member else None
        )

        user_payload = self.user_to_dict(user)
        if role:
            user_payload["role"] = role
        payload = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": jwt_manager.access_token_expire_seconds(),
            "user": user_payload,
            "organization": self.org_to_dict(org),
            "role": role,
        }
        if email_verification_token:
            payload["email_verification_token"] = email_verification_token
        return payload

    def signup_v2(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        organization_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        current_time = int(time.time())

        if self.db.query(User).filter(User.email == email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists",
            )

        password_hash = hash_password(password)
        profile = {"first_name": first_name, "last_name": last_name}
        user = User(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            profile=profile,
            auth_provider=AuthProvider.EMAIL,
            status=UserStatus.PENDING,
            email_verified=False,
            created_at=current_time,
            updated_at=current_time,
        )
        self.db.add(user)
        self.db.flush()

        normalized_org_name = (organization_name or "").strip()
        created_new_org = bool(normalized_org_name)
        if created_new_org:
            slug_base = "".join(
                ch.lower() if ch.isalnum() else "-" for ch in normalized_org_name
            ).strip("-") or f"org-{user.id}"
            slug = slug_base
            suffix = 1
            while self.db.query(Organization).filter(Organization.slug == slug).first():
                suffix += 1
                slug = f"{slug_base}-{suffix}"
            org = Organization(
                name=normalized_org_name,
                slug=slug,
                status=OrganizationStatus.ACTIVE,
                created_by=user.id,
                subscription_plan="free",
                subscription_status="active",
                created_at=current_time,
                updated_at=current_time,
            )
            self.db.add(org)
            self.db.flush()
        else:
            org = self.ensure_default_organization(user.id)

        member = Member(
            user_id=user.id,
            organization_id=org.id,
            role=Role.OWNER if created_new_org else Role.MEMBER,
            status="active",
            created_by=user.id,
            created_at=current_time,
            updated_at=current_time,
            joined_at=current_time,
        )
        self.db.add(member)

        verification = self.create_email_verification(user.id, email)
        verification_url = (
            f"{settings.APPLICATION_URL}/verify-email"
            f"?token={verification.token}"
        )
        try:
            MailService().send_signup_email(email, verification_url, first_name or email.split("@")[0])
        except Exception:
            logger.exception("Failed to send signup verification email to %s", email)

        self.db.commit()
        self.db.refresh(user)

        return self._build_auth_tokens(user, org, email_verification_token=verification.token)

    def login_v2(self, email: str, password: str) -> Dict[str, Any]:
        user = self.db.query(User).filter(User.email == email).first()
        if not user or not user.password_hash or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account not active. Please verify your email.",
            )
        if user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is not active. Please contact support.",
            )
        user.last_login_at = int(time.time())
        self.db.commit()
        member = self._membership_for(user.id)
        org = (
            self.db.query(Organization).filter(Organization.id == member.organization_id).first()
            if member else None
        )
        return self._build_auth_tokens(user, org)

    def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        payload = jwt_manager.decode_refresh_token(refresh_token)
        user_id = payload.get("user_id")
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        member = self._membership_for(user.id)
        org = (
            self.db.query(Organization).filter(Organization.id == member.organization_id).first()
            if member else None
        )
        return self._build_auth_tokens(user, org)

    def verify_email_by_token(self, token: str) -> Dict[str, str]:
        current_time = int(time.time())
        verification = (
            self.db.query(EmailVerification)
            .filter(
                EmailVerification.token == token,
                EmailVerification.verified == False,
                EmailVerification.expires_at > current_time,
            )
            .first()
        )
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )
        verification.verified = True
        verification.verified_at = current_time
        verification.updated_at = current_time

        user = self.db.query(User).filter(User.id == verification.user_id).first()
        if user:
            user.email_verified = True
            user.email_verified_at = current_time
            user.status = UserStatus.ACTIVE
            user.updated_at = current_time
        self.db.commit()
        return {"message": "Email verified successfully"}

    def request_password_reset(self, email: str) -> Dict[str, str]:
        return self.forgot_password(email)

    def reset_password_by_token(self, token: str, new_password: str) -> Dict[str, str]:
        current_time = int(time.time())
        reset = (
            self.db.query(PasswordReset)
            .filter(
                PasswordReset.token == token,
                PasswordReset.used == False,
                PasswordReset.expires_at > current_time,
            )
            .first()
        )
        if not reset:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )
        user = self.db.query(User).filter(User.id == reset.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        user.password_hash = hash_password(new_password)
        user.updated_at = current_time
        reset.used = True
        reset.used_at = current_time
        self.db.commit()
        return {"message": "Password reset successfully"}

    def change_password_for_user(self, user_id: int, new_password: str) -> Dict[str, str]:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        user.password_hash = hash_password(new_password)
        user.updated_at = int(time.time())
        self.db.commit()
        return {"message": "Password changed successfully"}

    def validate_invitation_by_token(self, token: str) -> Dict[str, Any]:
        current_time = int(time.time())
        invitation = (
            self.db.query(OrganizationInvite)
            .filter(
                OrganizationInvite.invitation_token == token,
                OrganizationInvite.status == InviteStatus.PENDING,
                OrganizationInvite.expires_at > current_time,
            )
            .first()
        )
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invitation",
            )
        existing_user = self.db.query(User).filter(User.email == invitation.email).first()
        org_id = invitation.organization_id or settings.DEFAULT_ORG_ID
        org = self.db.query(Organization).filter(Organization.id == org_id).first()
        return {
            "valid": True,
            "email": invitation.email,
            "role": invitation.role.value,
            "organization_id": str(org_id) if org_id else None,
            "organization_name": org.name if org else "",
            "account_exists": existing_user is not None and existing_user.password_hash is not None,
        }

    def accept_invitation_by_token(
        self,
        token: str,
        password: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        current_user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        current_time = int(time.time())
        invitation = (
            self.db.query(OrganizationInvite)
            .filter(
                OrganizationInvite.invitation_token == token,
                OrganizationInvite.status == InviteStatus.PENDING,
                OrganizationInvite.expires_at > current_time,
            )
            .first()
        )
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invitation",
            )

        org_id = invitation.organization_id or settings.DEFAULT_ORG_ID

        target_user: Optional[User] = None
        if current_user_id:
            target_user = self.db.query(User).filter(User.id == current_user_id).first()
            if target_user and target_user.email != invitation.email:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This invitation was sent to a different email address.",
                )

        existing_account = (
            self.db.query(User).filter(User.email == invitation.email).first()
        )
        if not target_user:
            target_user = existing_account

        if target_user and target_user.password_hash:
            # Existing account — upsert the membership so the user shows up
            # in the new org immediately.
            self.upsert(
                model=Member,
                values={
                    "user_id": target_user.id,
                    "role": invitation.role,
                    "status": "active",
                    "created_by": invitation.invited_by,
                    "created_at": current_time,
                    "updated_at": current_time,
                    "joined_at": current_time,
                    "organization_id": org_id,
                },
                conflict_fields=["organization_id", "user_id"],
                update_fields=["role", "status", "updated_at", "joined_at"],
                auto_commit=False,
            )
            invitation.status = InviteStatus.ACCEPTED
            invitation.accepted_by = target_user.id
            invitation.accepted_at = current_time
            invitation.updated_at = current_time
            self.db.commit()

            # Issue auth tokens only when the caller is already authenticated
            # as the target user — an anonymous link-clicker gets a success
            # response and is asked to sign in to access the new org.
            if current_user_id and current_user_id == target_user.id:
                org = self.db.query(Organization).filter(Organization.id == org_id).first()
                return self._build_auth_tokens(target_user, org)
            return {
                "message": "You have been added to the organization. Please sign in to continue.",
                "account_exists": True,
                "email": invitation.email,
                "requires_login": True,
            }

        if not password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="password is required to create a new account",
            )

        password_hash = hash_password(password)
        if target_user and not target_user.password_hash:
            target_user.password_hash = password_hash
            if first_name:
                target_user.first_name = first_name
            if last_name:
                target_user.last_name = last_name
            target_user.updated_at = current_time
            user = target_user
        else:
            user = User(
                email=invitation.email,
                password_hash=password_hash,
                first_name=first_name,
                last_name=last_name,
                profile={"first_name": first_name, "last_name": last_name},
                auth_provider=AuthProvider.EMAIL,
                status=UserStatus.ACTIVE,
                email_verified=True,
                email_verified_at=current_time,
                created_at=current_time,
                updated_at=current_time,
            )
            self.db.add(user)
            self.db.flush()

        self.upsert(
            model=Member,
            values={
                "user_id": user.id,
                "role": invitation.role,
                "status": "active",
                "created_by": invitation.invited_by,
                "created_at": current_time,
                "updated_at": current_time,
                "joined_at": current_time,
                "organization_id": org_id,
            },
            conflict_fields=["organization_id", "user_id"],
            update_fields=["role", "status", "updated_at", "joined_at"],
            auto_commit=False,
        )
        invitation.status = InviteStatus.ACCEPTED
        invitation.accepted_by = user.id
        invitation.accepted_at = current_time
        invitation.updated_at = current_time
        self.db.commit()

        org = self.db.query(Organization).filter(Organization.id == org_id).first()
        return self._build_auth_tokens(user, org)

    def get_user_me(self, user_id: int) -> Dict[str, Any]:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return self.user_to_dict(user)

    def get_organization_me(self, user_id: int) -> Optional[Dict[str, Any]]:
        member = self._membership_for(user_id)
        if not member:
            return None
        org = (
            self.db.query(Organization)
            .filter(Organization.id == member.organization_id)
            .first()
        )
        return self.org_to_dict(org)
