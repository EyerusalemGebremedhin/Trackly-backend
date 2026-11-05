from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: int
    user_id: int
    group_id: Optional[int] = None
    type: str
    title: str
    message: str
    link: Optional[str] = None
    read: bool
    created_at: datetime

    class Config:
        from_attributes = True
