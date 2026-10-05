from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel

from tracker.models.task import TaskStatus, PriorityEnum, TaskPeriodType


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assignee_id: int
    group_id: Optional[int] = None  
    priority: PriorityEnum = PriorityEnum.medium
    estimated_hours: float = 0
    deadline: Optional[date] = None
    is_management_duty: bool = False
    period_type: Optional[TaskPeriodType] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[PriorityEnum] = None
    status: Optional[TaskStatus] = None
    estimated_hours: Optional[float] = None
    deadline: Optional[date] = None
    period_type: Optional[TaskPeriodType] = None 


class TaskReassign(BaseModel):
    new_assignee_id: int
    reason: str


class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    assignee_id: int
    assigned_by_id: int
    group_id: Optional[int]
    priority: PriorityEnum
    status: TaskStatus
    estimated_hours: float
    actual_hours: float
    percent_complete: int
    deadline: Optional[date]
    created_at: datetime
    completed_at: Optional[datetime]
    is_management_duty: bool
    period_type: Optional[TaskPeriodType]
    is_archived: bool

    class Config:
        from_attributes = True