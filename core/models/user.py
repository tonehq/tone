from sqlalchemy import Column, BigInteger, String, Boolean, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from core.models.base import TimestampModel
from core.models.enums import UserStatus, AuthProvider


class User(TimestampModel):
    __tablename__ = 'users'
    __table_args__ = (
        UniqueConstraint('email', name='user_email_unique'),
        UniqueConstraint('username', name='user_username_unique'),
    )

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    email = Column(String, nullable=False, index=True)
    username = Column(String, nullable=True, index=True)
    password_hash = Column(String, nullable=True)
    first_name = Column(String)
    last_name = Column(String)
    profile = Column(JSONB)
    avatar_url = Column(String)
    phone_number = Column(String)
    auth_provider = Column(Enum(AuthProvider), default=AuthProvider.EMAIL)
    firebase_uid = Column(String, nullable=True)
    external_id = Column(String, nullable=True)
    status = Column(Enum(UserStatus), default=UserStatus.PENDING)
    email_verified = Column(Boolean, default=False)
    email_verified_at = Column(BigInteger)
    phone_verified = Column(Boolean, default=False)
    phone_verified_at = Column(BigInteger)
    last_login_at = Column(BigInteger)
    user_metadata = Column(JSONB, default={})

