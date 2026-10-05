from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel

from tracker.models.checkin import PeriodType


class GroupGoalCreate(BaseModel):
    goal_text: str
    period_type: PeriodType = PeriodType.weekly
    period_start: date = None  # defaults to today in the service layer
    period_end: Optional[date] = None


class GroupGoalOut(BaseModel):
    id: int
    group_id: int
    created_by: int
    goal_text: str
    period_type: PeriodType
    period_start: date
    period_end: Optional[date]
    created_at: datetime

    class Config:
        from_attributes = True
