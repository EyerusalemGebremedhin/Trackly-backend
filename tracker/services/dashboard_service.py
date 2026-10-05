from datetime import date, timedelta
from typing import List
from fastapi import HTTPException
from sqlalchemy.orm import Session

from tracker.models.user import User
from tracker.models.task import Task, TaskStatus
from tracker.models.membership import MembershipRole
from tracker.repositories.task_repository import TaskRepository
from tracker.repositories.membership_repository import MembershipRepository
from tracker.repositories.checkin_repository import CheckinRepository
from tracker.repositories.group_repository import GroupRepository
from tracker.repositories.user_repository import UserRepository
from tracker.schemas.dashboard import MyDashboard, MemberSummary, GroupDashboard, Alert


def _summarize_tasks(tasks: List[Task]):
    today = date.today()
    total = len(tasks)
    done = sum(1 for t in tasks if t.status == TaskStatus.done)
    overdue = sum(1 for t in tasks if t.deadline and t.deadline < today and t.status != TaskStatus.done)
    est_hours = sum(t.estimated_hours or 0 for t in tasks)
    act_hours = sum(t.actual_hours or 0 for t in tasks)
    return total, done, overdue, est_hours, act_hours


from tracker.models.checkin import PeriodType
from tracker.services.checkin_service import period_start_for


def _period_start_for_cadence(cadence: str) -> date:
    return period_start_for(PeriodType(cadence))


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.tasks = TaskRepository(db)
        self.memberships = MembershipRepository(db)
        self.checkins = CheckinRepository(db)
        self.groups = GroupRepository(db)
        self.users = UserRepository(db)

    def my_dashboard(self, current_user: User) -> MyDashboard:
        tasks = self.tasks.list(assignee_id=current_user.id, is_archived=False)
        total, done, overdue, est_hours, act_hours = _summarize_tasks(tasks)
        completion_rate = round((done / total) * 100, 1) if total else 0.0

        alerts: List[Alert] = []
        today = date.today()
        for t in tasks:
            if t.deadline and t.deadline < today and t.status != TaskStatus.done:
                alerts.append(Alert(
                    type="overdue_task",
                    message=f"'{t.title}' was due {t.deadline} and isn't marked done",
                    task_id=t.id,
                ))

        return MyDashboard(
            total_tasks=total, done_tasks=done, overdue_tasks=overdue,
            total_estimated_hours=est_hours, total_actual_hours=act_hours,
            completion_rate=completion_rate, tasks=tasks, alerts=alerts,
        )

    def group_dashboard(self, group_id: int, current_user: User, lead_only: bool = True) -> GroupDashboard:
        group = self.groups.get_by_id(group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        membership = self.memberships.get(current_user.id, group_id)
        if not membership:
            raise HTTPException(status_code=403, detail="You are not a member of this group")
        if lead_only and membership.role != MembershipRole.lead:
            raise HTTPException(status_code=403, detail="Only a lead can view the group dashboard")

        group.my_role = membership.role

        memberships = self.memberships.get_by_group(group_id)
        period_start = _period_start_for_cadence(group.checkin_cadence.value)

        member_summaries = []
        total_open = 0
        total_overdue = 0
        alerts: List[Alert] = []
        today = date.today()

        for m in memberships:
            user = self.users.get_by_id(m.user_id)
            tasks = self.tasks.list(assignee_id=user.id, group_id=group_id)
            total, done, overdue, est_hours, act_hours = _summarize_tasks(tasks)

            completed_with_deadline = [t for t in tasks if t.status == TaskStatus.done and t.deadline]
            on_time = sum(1 for t in completed_with_deadline if t.completed_at and t.completed_at.date() <= t.deadline)
            on_time_rate = round((on_time / len(completed_with_deadline)) * 100, 1) if completed_with_deadline else 100.0

            open_tasks = [t for t in tasks if t.status != TaskStatus.done]
            workload_score = round(sum(t.estimated_hours or 0 for t in open_tasks), 1)

            recent_checkin = self.checkins.get_for_period(user.id, group_id, period_start)
            has_checked_in = recent_checkin is not None
            if not has_checked_in:
                alerts.append(Alert(
                    type="missed_checkin",
                    message=f"{user.name} hasn't submitted a check-in for this period yet",
                    user_id=user.id,
                ))

            for t in tasks:
                if t.deadline and t.deadline < today and t.status != TaskStatus.done:
                    alerts.append(Alert(
                        type="overdue_task",
                        message=f"{user.name}'s task '{t.title}' was due {t.deadline}",
                        user_id=user.id, task_id=t.id,
                    ))

            total_open += len(open_tasks)
            total_overdue += overdue

            member_summaries.append(MemberSummary(
                user=user, total_tasks=total, done_tasks=done, overdue_tasks=overdue,
                on_time_rate=on_time_rate, total_estimated_hours=est_hours,
                total_actual_hours=act_hours, workload_score=workload_score,
                has_checked_in=has_checked_in,
            ))

        return GroupDashboard(
            group=group, members=member_summaries,
            total_open_tasks=total_open, total_overdue_tasks=total_overdue,
            alerts=alerts,
        )

    def group_metrics(self, group_id: int, current_user: User) -> dict:
        dash = self.group_dashboard(group_id, current_user, lead_only=False)
        return {
            "members": [
                {
                    "name": m.user.name,
                    "done_tasks": m.done_tasks,
                    "total_tasks": m.total_tasks,
                    "workload_score": m.workload_score,
                    "on_time_rate": m.on_time_rate,
                    "estimated_hours": m.total_estimated_hours,
                    "actual_hours": m.total_actual_hours,
                }
                for m in dash.members
            ]
        }