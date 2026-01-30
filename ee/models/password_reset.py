from sqlalchemy import Column, BigInteger, String, Boolean, Text, ForeignKey
import time

from ee.database.base import EEBase


class PasswordReset(EEBase):
    __tablename__ = 'password_resets'

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    email = Column(String, nullable=False, index=True)
    token = Column(String, nullable=False, unique=True)
    used = Column(Boolean, default=False)
    expires_at = Column(BigInteger, nullable=False)
    used_at = Column(BigInteger)
    ip_address = Column(String)
    user_agent = Column(Text)
    created_at = Column(BigInteger, nullable=False, default=lambda: int(time.time()))
    updated_at = Column(BigInteger, nullable=False, default=lambda: int(time.time()))
