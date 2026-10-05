from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from dependency import get_current_user
from tracker.models.user import User
from tracker.models.task import TaskStatus
from tracker.schemas.dashboard import MyDashboard, GroupDashboard
from tracker.services.dashboard_service import DashboardService
from tracker.services.task_service import TaskService
from tracker.services.checkin_service import CheckinService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/me", response_model=MyDashboard)
def my_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return DashboardService(db).my_dashboard(current_user)


@router.get("/group/{group_id}", response_model=GroupDashboard)
def group_dashboard(group_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return DashboardService(db).group_dashboard(group_id, current_user)


@router.get("/metrics/me")
def my_metrics(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Data shaped for graphs: task status breakdown, hours estimated vs actual,
    and a simple daily achieved-count trend over the last 14 days.
    """
    tasks = TaskService(db).list_for_user(current_user)
    status_counts = {s.value: 0 for s in TaskStatus}
    for t in tasks:
        status_counts[t.status.value] += 1

    est = sum(t.estimated_hours or 0 for t in tasks)
    act = sum(t.actual_hours or 0 for t in tasks)

    checkins = CheckinService(db).history_for_user(current_user.id)
    since = date.today() - timedelta(days=14)
    trend = {}
    for c in checkins:
        if c.period_date >= since:
            trend[str(c.period_date)] = trend.get(str(c.period_date), 0) + 1

    return {
        "status_breakdown": status_counts,
        "estimated_hours": est,
        "actual_hours": act,
        "checkin_trend": trend,
    }
@router.get("/metrics/group/{group_id}")
def group_metrics(group_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return DashboardService(db).group_metrics(group_id, current_user)