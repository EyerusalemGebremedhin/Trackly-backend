from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from tracker.models.feedback import FeedbackSource


class FeedbackCreate(BaseModel):
    about_user_id: int
    content: str
    task_id: Optional[int] = None
    checkin_id: Optional[int] = None


class FeedbackOut(BaseModel):
    id: int
    about_user_id: int
    given_by_id: Optional[int]
    source: FeedbackSource
    content: str
    task_id: Optional[int]
    checkin_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
