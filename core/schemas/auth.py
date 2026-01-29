from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    username: Optional[str] = None
    org_name: Optional[str] = None


class SignupFirebaseRequest(BaseModel):
    firebase_token: str
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    password: str
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str
    user_id: int


class SwitchOrganizationRequest(BaseModel):
    org_id: int


class CheckOrganizationRequest(BaseModel):
    name: str
