from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from uuid import UUID


class UserBase(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone_number: Optional[str] = None
    profile: Optional[Dict[str, Any]] = None


class UserResponse(UserBase):
    id: int
    uuid: UUID
    avatar_url: Optional[str] = None
    phone_number: Optional[str] = None
    status: str
    email_verified: bool
    created_at: int
    updated_at: int

    class Config:
        from_attributes = True


class UserProfileResponse(UserResponse):
    profile: Optional[Dict[str, Any]] = None
    user_metadata: Optional[Dict[str, Any]] = None
