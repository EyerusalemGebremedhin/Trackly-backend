from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from tracker.models.help_request import HelpRequestStatus


class HelpRequestCreate(BaseModel):
    skill_needed: str
    task_id: Optional[int] = None
    note: Optional[str] = None


class HelpRequestOut(BaseModel):
    id: int
    group_id: int
    task_id: Optional[int]
    requested_by: int
    requested_by_name: str
    skill_needed: str
    note: Optional[str]
    status: HelpRequestStatus
    resolved_by: Optional[int]
    created_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True
