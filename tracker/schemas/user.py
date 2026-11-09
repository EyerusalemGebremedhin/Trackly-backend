from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    skills: Optional[str] = None


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    skills: Optional[str] = None
    job_title: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    is_verified: bool = False
    is_active: bool = True
    is_online: bool = False
    mfa_enabled: bool = False

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class ForgotPassword(BaseModel):
    email: EmailStr


class ResetPassword(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    skills: Optional[str] = None
    job_title: Optional[str] = None
    bio: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)


class VerifyEmail(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=4, max_length=10)


class ResendVerification(BaseModel):
    email: EmailStr


class ResendActivation(BaseModel):
    email: EmailStr


class ActivateAccount(BaseModel):
    email: Optional[EmailStr] = None
    code: Optional[str] = Field(None, min_length=4, max_length=10)
    token: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)


class TeamRegisterUser(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    skills: Optional[str] = None


class EnableMFA(BaseModel):
    code: str = Field(..., min_length=4, max_length=10)


class MFAVerify(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=4, max_length=10)
