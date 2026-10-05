from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel

from tracker.models.checkin import PeriodType


class CheckinCreate(BaseModel):
    group_id: Optional[int] = None  # null = personal check-in
    task_id: Optional[int] = None
    goal: Optional[str] = None
    achieved: str  # only required field - fast to fill on a busy day
    went_well: Optional[str] = None
    didnt_go_well: Optional[str] = None
    improve: Optional[str] = None
    blocker: Optional[str] = None
    period_type: PeriodType = PeriodType.daily
    period_date: date = None  # defaults to today in the service layer


class CheckinOut(BaseModel):
    id: int
    user_id: int
    group_id: Optional[int]
    task_id: Optional[int]
    goal: Optional[str]
    achieved: str
    went_well: Optional[str]
    didnt_go_well: Optional[str]
    improve: Optional[str]
    blocker: Optional[str]
    period_type: PeriodType
    period_date: date
    created_at: datetime

    class Config:
        from_attributes = True
