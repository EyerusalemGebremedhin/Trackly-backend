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

ASSUMED_HOURS_PER_DAY = 4.0

PERIOD_DAYS = {
    InsightPeriod.daily: 1,
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
            target_groups = {m.group_id for m in self.memberships.get_by_user(user_id)}
            current_groups = {m.group_id for m in self.memberships.get_by_user(current_user.id)}
            if not (target_groups & current_groups):
                raise HTTPException(status_code=403, detail="Can only view insights of group members")

        if not refresh:
            cached = self.repo.get_latest_for_user(user_id, period)
        all_tasks = self.tasks.list(assignee_id=user_id)
        open_tasks = [t for t in all_tasks if t.status != TaskStatus.done]
        done_tasks = [t for t in all_tasks if t.status == TaskStatus.done]
        workload_hours, completion_date = _predict_workload_and_completion(open_tasks)

        current_user_obj = self.users.get_by_id(user_id)
        profile = f"Name: {current_user_obj.name if current_user_obj else ''}; Job: {getattr(current_user_obj,'job_title',None)}; Skills: {getattr(current_user_obj,'skills',None)}"
        recent_checkins = self.checkins.list(user_id=user_id) if hasattr(self.checkins,'list') else []
        checkin_context = "\n".join(f"- {c.created_at}: mood={getattr(c,'mood',None)}" for c in (recent_checkins or [])[:10]) or "No check-ins."

        task_context = "\n".join(_task_line(t) for t in all_tasks[:40]) or "No tasks yet."

        system_prompt = (
            "You are Trackly's advanced AI analyst. "
            "Provide deep, actionable insights with specific recommendations. "
            "Always praise good work explicitly. Be direct about risks without being harsh. "
            "Analyze patterns, productivity trends, time management, and provide concrete next steps. "
            "Be specific with numbers and task names. "
            "Respond ONLY as JSON with keys: summary (string), risk_level (low|medium|high), "
            "risk_flags (array of short strings), recommendations (array of short strings), "
            "wins (array of short strings)."
        )
        user_prompt = (
            f"Period: {period.value}\nProfile: {profile}\n"
            f"Recent check-ins:\n{checkin_context}\n"
            f"Tasks:\n{task_context}\nDone: {len(done_tasks)}, Open: {len(open_tasks)}"
        )

        try:
            ai = call_groq_json(system_prompt, user_prompt, model="openai/gpt-oss-20b")
        except Exception:
            ai = {
                "summary": f"AI analysis: {len(done_tasks)} of {len(all_tasks)} tasks completed. {len(open_tasks)} remaining.",
                "risk_level": "medium" if any(t.deadline and t.deadline < date.today() for t in open_tasks) else "low",
                "risk_flags": [t.title + " overdue" for t in open_tasks if t.deadline and t.deadline < date.today()][:5],
                "recommendations": ["Focus on high-priority tasks first", "Break large tasks into smaller subtasks"],
                "wins": [t.title for t in done_tasks[-3:]],
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
            cached = self.repo.get_latest_for_group(group_id, period)
            if cached:
                return cached
        all_tasks = self.tasks.list(group_id=group_id)
        open_tasks = [t for t in all_tasks if t.status != TaskStatus.done]
        workload_hours, completion_date = _predict_workload_and_completion(open_tasks)

        members = self.memberships.get_by_group(group_id)
        member_lines = []
            u = self.users.get_by_id(m.user_id)
            if not u:
                continue
            their_tasks = [t for t in all_tasks if t.assignee_id == u.id]
            member_lines.append(
                f"- {u.name} ({u.email}): {len([t for t in their_tasks if t.status == TaskStatus.done])} done, {len([t for t in their_tasks if t.status != TaskStatus.done])} open"
            )

        task_context = "\n".join(_task_line(t) for t in all_tasks[:60]) or "No tasks yet."
        member_context = "\n".join(member_lines) or "No members."

        system_prompt = (
            "You are Trackly's team AI analyst using Google Gemini Flash via Groq. "
            "Provide comprehensive team insights with workload balancing advice, identify bottlenecks, "
            "recognize top performers by name, and suggest fair task redistribution. "
            "Be honest and constructive. "
            "Respond ONLY as JSON with keys: summary (string), risk_level (low|medium|high), "
            "risk_flags (array of short strings), recommendations (array of short strings), "
            "wins (array of short strings, can mention names), "
            "member_breakdown (array of objects: {name, percent_achieved (0-100 int or null), comment})."
        )
        user_prompt = f"Period: {period.value}\nMembers:\n{member_context}\nTasks:\n{task_context}\nTotal open: {len(open_tasks)}"

        try:
            ai = call_groq_json(system_prompt, user_prompt, model="openai/gpt-oss-20b")
        except Exception:
            ai = {
                "summary": f"Team overview: {len(open_tasks)} open tasks across {len(members)} members.",
                "risk_level": "low",
                "risk_flags": [],
                "recommendations": ["Regular check-ins recommended", "Balance workload across team"],
                "wins": [],
                "member_breakdown": [{"name": ln.split(" (")[0].strip("- "), "percent_achieved": None, "comment": "Active member"} for ln in member_lines],
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
