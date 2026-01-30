from sqlalchemy import Column, BigInteger, String, Boolean, Text, ForeignKey

from core.models.base import TimestampModel


class PasswordReset(TimestampModel):
    __tablename__ = 'password_resets'

    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    email = Column(String, nullable=False, index=True)
    token = Column(String, nullable=False, unique=True)
    used = Column(Boolean, default=False)
    expires_at = Column(BigInteger, nullable=False)
    used_at = Column(BigInteger)
    ip_address = Column(String)
    user_agent = Column(Text)

