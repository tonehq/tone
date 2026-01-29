from sqlalchemy import Column, BigInteger, String, Boolean, Integer, ForeignKey, UniqueConstraint
import time

from ee.database.base import EEBase


class EmailVerification(EEBase):
    __tablename__ = 'email_verifications'
    __table_args__ = (UniqueConstraint('email', 'code', name='email_verification_unique'),)

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    email = Column(String, nullable=False, index=True)
    code = Column(String, nullable=False)
    token = Column(String, nullable=False, unique=True)
    verified = Column(Boolean, default=False)
    expires_at = Column(BigInteger, nullable=False)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    verified_at = Column(BigInteger)
    created_at = Column(BigInteger, nullable=False, default=lambda: int(time.time()))
    updated_at = Column(BigInteger, nullable=False, default=lambda: int(time.time()))
