from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LeadershipTransferRequest(BaseModel):
    new_lead_id: int
    reason: str


class CoLeadRequest(BaseModel):
    user_id: int
    reason: str


class GroupActivityOut(BaseModel):
    id: int
    group_id: int
    actor_id: int
    target_user_id: Optional[int] = None
    action: str
    reason: Optional[str] = None
    actor_name: Optional[str] = None
    target_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
