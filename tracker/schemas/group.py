from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

from tracker.models.group import CheckinCadence
from tracker.models.membership import MembershipRole


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    checkin_cadence: CheckinCadence = CheckinCadence.weekly


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    checkin_cadence: Optional[CheckinCadence] = None


class GroupOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_by: int
    checkin_cadence: CheckinCadence
    is_archived: bool
    created_at: datetime
    my_role: MembershipRole

    class Config:
        from_attributes = True


class MemberAdd(BaseModel):
    email: EmailStr
    role: MembershipRole = MembershipRole.member


class MembershipOut(BaseModel):
    id: int
    user_id: int
    group_id: int
    role: MembershipRole
    created_at: datetime
    name: str
    email: EmailStr
    skills: Optional[str] = None

    class Config:
        from_attributes = True


class TransferLead(BaseModel):
    new_lead_user_id: int