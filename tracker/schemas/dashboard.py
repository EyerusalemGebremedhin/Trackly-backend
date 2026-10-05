from typing import List, Optional
from pydantic import BaseModel

from tracker.schemas.user import UserOut
from tracker.schemas.group import GroupOut
from tracker.schemas.task import TaskOut


class Alert(BaseModel):
    type: str  # "missed_checkin" | "overdue_task"
    message: str
    user_id: Optional[int] = None
    task_id: Optional[int] = None


class MyDashboard(BaseModel):
    total_tasks: int
    done_tasks: int
    overdue_tasks: int
    total_estimated_hours: float
    total_actual_hours: float
    completion_rate: float
    tasks: List[TaskOut]
    alerts: List[Alert]


class MemberSummary(BaseModel):
    user: UserOut
    total_tasks: int
    done_tasks: int
    overdue_tasks: int
    on_time_rate: float
    total_estimated_hours: float
    total_actual_hours: float
    workload_score: float  # sum of estimated hours across open tasks
    has_checked_in: bool   # for current period, per group cadence


class GroupDashboard(BaseModel):
    group: GroupOut
    members: List[MemberSummary]
    total_open_tasks: int
    total_overdue_tasks: int
    alerts: List[Alert]
