from datetime import date, timedelta
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from tracker.models.user import User
from tracker.models.task import Task, TaskStatus
from tracker.models.ai_insight import AIInsight, InsightScope, InsightPeriod, RiskLevel
from tracker.repositories.ai_insight_repository import AIInsightRepository
from tracker.repositories.task_repository import TaskRepository
from tracker.repositories.checkin_repository import CheckinRepository
from tracker.repositories.membership_repository import MembershipRepository
from tracker.repositories.user_repository import UserRepository
from tracker.services.groq_client import call_groq_json

# Rough assumed focused-work capacity per person per day, used only for the
# workload/completion-date estimate. Deliberately simple and documented so it's
# easy to tune later rather than a black box.
ASSUMED_HOURS_PER_DAY = 4.0

PERIOD_DAYS = {
    InsightPeriod.weekly: 7,
    InsightPeriod.monthly: 30,
    InsightPeriod.general: 90,
}


def _predict_workload_and_completion(open_tasks: List[Task]) -> tuple[float, Optional[date]]:
    remaining_hours = sum((t.estimated_hours or 0) * (1 - (t.percent_complete or 0) / 100) for t in open_tasks)
    if remaining_hours <= 0:
        return 0.0, None
    days_needed = remaining_hours / ASSUMED_HOURS_PER_DAY
    completion = date.today() + timedelta(days=round(days_needed))
    return round(remaining_hours, 1), completion


def _task_line(t: Task) -> str:
    return f"- '{t.title}' status={t.status.value} est_hours={t.estimated_hours} deadline={t.deadline} completed_at={t.completed_at}"


class AIInsightService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AIInsightRepository(db)
        self.tasks = TaskRepository(db)
        self.checkins = CheckinRepository(db)
        self.memberships = MembershipRepository(db)
        self.users = UserRepository(db)

    def get_or_generate_individual(self, user_id: int, current_user: User, period: InsightPeriod, refresh: bool = False) -> AIInsight:
        if user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Can only view your own individual insights")

        if not refresh:
            existing = self.repo.get_latest_for_user(user_id, period)
            if existing:
                return existing

        all_tasks = self.tasks.list(assignee_id=user_id)
        open_tasks = [t for t in all_tasks if t.status != TaskStatus.done]
        done_tasks = [t for t in all_tasks if t.status == TaskStatus.done]
        workload_hours, completion_date = _predict_workload_and_completion(open_tasks)

        task_context = "\n".join(_task_line(t) for t in all_tasks[:40]) or "No tasks yet."

        system_prompt = (
            "You are Trackly's honest, fair progress analyzer for one individual. "
            "You always explicitly call out good work - finishing on time or ahead of a deadline "
            "deserves genuine, specific praise, not just generic encouragement. "
            "You are also direct about real risk or overdue work, without being harsh. "
            "Respond ONLY as JSON with keys: summary (string), risk_level (low|medium|high), "
            "risk_flags (array of short strings), recommendations (array of short strings), "
            "wins (array of short strings - specific things done well or on time)."
        )
        user_prompt = f"Period: {period.value}\nTasks:\n{task_context}"

        try:
            ai = call_groq_json(system_prompt, user_prompt)
        except Exception:
            ai = {
                "summary": f"{len(done_tasks)} of {len(all_tasks)} tasks done this {period.value}.",
                "risk_level": "medium" if any(t.deadline and t.deadline < date.today() for t in open_tasks) else "low",
                "risk_flags": [t.title + " is overdue" for t in open_tasks if t.deadline and t.deadline < date.today()][:5],
                "recommendations": ["Check in with your lead if you're blocked on anything."],
                "wins": [t.title + " - finished" for t in done_tasks[-3:]],
            }

        insight = AIInsight(
            scope=InsightScope.individual,
            period=period,
            user_id=user_id,
            summary=ai.get("summary", ""),
            risk_level=RiskLevel(ai.get("risk_level", "low")),
            risk_flags="\n".join(ai.get("risk_flags", [])),
            recommendations="\n".join(ai.get("recommendations", [])),
            wins="\n".join(ai.get("wins", [])),
            predicted_workload_hours=workload_hours,
            predicted_completion_date=completion_date,
        )
        return self.repo.create(insight)

    def get_or_generate_group(self, group_id: int, current_user: User, period: InsightPeriod, refresh: bool = False) -> AIInsight:
        if not self.memberships.get(current_user.id, group_id):
            raise HTTPException(status_code=403, detail="Not a member of this group")

        if not refresh:
            existing = self.repo.get_latest_for_group(group_id, period)
            if existing:
                return existing

        members = self.memberships.get_by_group(group_id)
        all_tasks = self.tasks.list(group_id=group_id)
        open_tasks = [t for t in all_tasks if t.status != TaskStatus.done]
        workload_hours, completion_date = _predict_workload_and_completion(open_tasks)

        member_lines = []
        for m in members:
            u = self.users.get_by_id(m.user_id)
            if not u:
                continue
            their_tasks = [t for t in all_tasks if t.assignee_id == u.id]
            member_lines.append(
                f"- {u.name} ({u.email}): "
                f"{len([t for t in their_tasks if t.status == TaskStatus.done])} done, "
                f"{len([t for t in their_tasks if t.status != TaskStatus.done])} open"
            )

        task_context = "\n".join(_task_line(t) for t in all_tasks[:60]) or "No tasks yet."
        member_context = "\n".join(member_lines) or "No members."

        system_prompt = (
            "You are Trackly's honest, fair progress analyzer for a whole group. "
            "Weigh blockers and workload before judging - a fair review, not a guess. "
            "Praise people who finished on time by name; be direct about anyone falling behind, without being harsh. "
            "Respond ONLY as JSON with keys: summary (string), risk_level (low|medium|high), "
            "risk_flags (array of short strings), recommendations (array of short strings), "
            "wins (array of short strings, can mention names), "
            "member_breakdown (array of objects: {name, percent_achieved (0-100 int or null), comment})."
        )
        user_prompt = f"Period: {period.value}\nMembers:\n{member_context}\nTasks:\n{task_context}"

        try:
            ai = call_groq_json(system_prompt, user_prompt)
        except Exception:
            ai = {
                "summary": f"{len(open_tasks)} open tasks across {len(members)} members this {period.value}.",
                "risk_level": "low",
                "risk_flags": [],
                "recommendations": ["Have the lead check in on anyone with a heavy open-task load."],
                "wins": [],
                "member_breakdown": [
                    {"name": ln.split(" (")[0].strip("- "), "percent_achieved": None, "comment": ""}
                    for ln in member_lines
                ],
            }

        member_breakdown_lines = [
            f"{item.get('name','?')}|{item.get('percent_achieved','')}|{item.get('comment','')}"
            for item in ai.get("member_breakdown", [])
        ]

        insight = AIInsight(
            scope=InsightScope.group,
            period=period,
            group_id=group_id,
            summary=ai.get("summary", ""),
            risk_level=RiskLevel(ai.get("risk_level", "low")),
            risk_flags="\n".join(ai.get("risk_flags", [])),
            recommendations="\n".join(ai.get("recommendations", [])),
            wins="\n".join(ai.get("wins", [])),
            member_breakdown="\n".join(member_breakdown_lines),
            predicted_workload_hours=workload_hours,
            predicted_completion_date=completion_date,
        )
        return self.repo.create(insight)
