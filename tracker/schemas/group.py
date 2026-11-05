from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    checkin_cadence: str = "weekly"


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    checkin_cadence: Optional[str] = None


class GroupOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_by: int
    checkin_cadence: str
    is_archived: bool
    created_at: datetime
    my_role: str

    class Config:
        from_attributes = True


class MemberAdd(BaseModel):
    email: EmailStr
    role: str = "member"
    reason: Optional[str] = None


class RoleUpdate(BaseModel):
    role: str
    reason: Optional[str] = None


class MembershipOut(BaseModel):
    id: int
    user_id: int
    group_id: int
    role: str
    created_at: datetime
    name: str
    email: EmailStr
    skills: Optional[str] = None
    added_reason: Optional[str] = None

    class Config:
        from_attributes = True


class TransferLead(BaseModel):
    new_lead_user_id: int


class InviteMember(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = "member"
    reason: Optional[str] = None
