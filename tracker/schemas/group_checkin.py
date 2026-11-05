from datetime import time
from typing import Optional, List

from pydantic import BaseModel


class GroupCheckinSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    opens_at: Optional[str] = None  # HH:MM
    deadline_at: Optional[str] = None  # HH:MM
    days_of_week: Optional[str] = None
    timezone: Optional[str] = None
    reminder_minutes_before: Optional[int] = None
    list_missed_publicly: Optional[bool] = None


class GroupCheckinSettingsOut(BaseModel):
    id: int
    group_id: int
    enabled: bool
    opens_at: Optional[str] = None
    deadline_at: Optional[str] = None
    days_of_week: Optional[str] = None
    timezone: str
    reminder_minutes_before: int
    list_missed_publicly: bool

    class Config:
        from_attributes = True
