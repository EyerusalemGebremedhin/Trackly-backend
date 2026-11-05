from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class HelpRequestCreate(BaseModel):
    task_id: Optional[int] = None
    skill_needed: str
    note: Optional[str] = None
    reason: Optional[str] = None
    task_type: Optional[str] = None


class HelpRequestOut(BaseModel):
    id: int
    group_id: int
    task_id: Optional[int] = None
    requested_by: int
    requested_by_name: str
    skill_needed: str
    note: Optional[str] = None
    reason: Optional[str] = None
    task_type: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
