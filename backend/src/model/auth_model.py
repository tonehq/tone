from sqlalchemy import Column, BigInteger, String, JSON, Enum, Boolean, ForeignKey, Integer, UniqueConstraint, Text
from sqlalchemy.orm import declarative_base
import enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from src.database import Base

class UserStatus(enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"

class OrganizationStatus(enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"

class Role(enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"

class InviteStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class AccessRequestStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class AuthProvider(enum.Enum):
    EMAIL = "email"
    FIREBASE = "firebase"
    GOOGLE = "google"
    GITHUB = "github"

class User(Base):
    __tablename__ = 'users'
    __table_args__ = (
        UniqueConstraint('email', name='user_email_unique'),
        UniqueConstraint('username', name='user_username_unique'),
    )

    id = Column(BigInteger, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True)
    email = Column(String, nullable=False, index=True)
    username = Column(String, nullable=True, index=True)
    password_hash = Column(String, nullable=True)  # Nullable for OAuth users
    
    # Profile information
    first_name = Column(String)
    last_name = Column(String)
    profile = Column(JSONB)  # Additional profile data
    avatar_url = Column(String)
    phone_number = Column(String)
    
    # Auth provider info
    auth_provider = Column(Enum(AuthProvider), default=AuthProvider.EMAIL)
    firebase_uid = Column(String, nullable=True)  # For Firebase auth
    external_id = Column(String, nullable=True)   # For other OAuth providers
    
    # Status and verification
    status = Column(Enum(UserStatus), default=UserStatus.PENDING)
    email_verified = Column(Boolean, default=False)
    email_verified_at = Column(BigInteger)
    phone_verified = Column(Boolean, default=False)
    phone_verified_at = Column(BigInteger)
    
    # Timestamps
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)
    last_login_at = Column(BigInteger)
    
    # User metadata
    user_metadata = Column(JSONB, default={})

class Organization(Base):
    __tablename__ = 'organizations'
    __table_args__ = (
        UniqueConstraint('slug', name='org_slug_unique'),
    )

    id = Column(BigInteger, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, index=True)  # URL-friendly name
    
    # Organization details
    description = Column(Text)
    logo_url = Column(String)
    website_url = Column(String)
    
    # Settings
    settings = Column(JSONB, default={})
    
    # Status
    status = Column(Enum(OrganizationStatus), default=OrganizationStatus.ACTIVE)
    
    # Timestamps
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)
    created_by = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    
    # Billing/subscription info (if needed)
    subscription_plan = Column(String, default='free')
    subscription_status = Column(String, default='active')

class Member(Base):
    __tablename__ = 'members'
    __table_args__ = (
        UniqueConstraint('user_id', 'organization_id', name='org_member_unique'),
    )

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    organization_id = Column(BigInteger, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    
    # Role and permissions
    role = Column(Enum(Role), default=Role.MEMBER)
    custom_permissions = Column(JSONB, default=[])  # Additional permissions beyond role
    
    # Status
    status = Column(String, default='active')  # active, suspended, inactive
    
    # Timestamps
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)
    created_by = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    
    # Join metadata
    joined_at = Column(BigInteger)
    last_activity_at = Column(BigInteger)

class OrganizationInvite(Base):
    __tablename__ = 'organization_invites'
    __table_args__ = (
        UniqueConstraint('email', 'organization_id', name='org_invite_unique'),
    )

    id = Column(BigInteger, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True)
    organization_id = Column(BigInteger, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    
    # Invitee information
    email = Column(String, nullable=False, index=True)
    name = Column(String)
    role = Column(Enum(Role), default=Role.MEMBER)
    
    # Invite details
    status = Column(Enum(InviteStatus), default=InviteStatus.PENDING)
    invitation_token = Column(String, nullable=False, unique=True)
    expires_at = Column(BigInteger, nullable=False)
    
    # Who sent the invite
    invited_by = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    
    # Acceptance details
    accepted_by = Column(BigInteger, ForeignKey('users.id'), nullable=True)
    accepted_at = Column(BigInteger)
    
    # Timestamps
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)
    
    # Custom message or permissions
    message = Column(Text)
    custom_permissions = Column(JSONB, default=[])

class EmailVerification(Base):
    __tablename__ = 'email_verifications'
    __table_args__ = (
        UniqueConstraint('email', 'code', name='email_verification_unique'),
    )

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    email = Column(String, nullable=False, index=True)
    
    # Verification details
    code = Column(String, nullable=False)  # 6-digit code
    token = Column(String, nullable=False, unique=True)  # URL token
    
    # Status and expiry
    verified = Column(Boolean, default=False)
    expires_at = Column(BigInteger, nullable=False)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    
    # Timestamps
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)
    verified_at = Column(BigInteger)

class PasswordReset(Base):
    __tablename__ = 'password_resets'

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    email = Column(String, nullable=False, index=True)
    
    # Reset details
    token = Column(String, nullable=False, unique=True)
    used = Column(Boolean, default=False)
    expires_at = Column(BigInteger, nullable=False)
    
    # Timestamps
    created_at = Column(BigInteger, nullable=False)
    used_at = Column(BigInteger)
    
    # Security
    ip_address = Column(String)
    user_agent = Column(Text)

class OrganizationAccessRequest(Base):
    __tablename__ = 'organization_access_requests'
    __table_args__ = (
        UniqueConstraint('user_id', 'organization_id', name='org_access_request_unique'),
    )

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    organization_id = Column(BigInteger, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)

    status = Column(Enum(AccessRequestStatus), default=AccessRequestStatus.PENDING)
    message = Column(Text)

    reviewed_by = Column(BigInteger, ForeignKey('users.id'), nullable=True)
    reviewed_at = Column(BigInteger)

    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)