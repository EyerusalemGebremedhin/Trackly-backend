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
    est = t.estimated_hours if t.estimated_hours is not None else "not set"
    actual = t.actual_hours if t.actual_hours is not None else "not set"
    return (
        f"- '{t.title}' status={t.status.value} est_hours={est} actual_hours={actual} "
        f"percent_complete={t.percent_complete or 0} deadline={t.deadline} completed_at={t.completed_at}"
    )


def _has_recorded_actual_hours(tasks: List[Task]) -> bool:
    return any(t.actual_hours is not None and float(t.actual_hours) > 0 for t in tasks)


def _ensure_text_suffix(text: str, suffix: str) -> str:
    text = (text or "").strip()
    if not suffix:
        return text
    if suffix.lower() in text.lower():
        return text
    return f"{text} {suffix}".strip()


def _sanitize_ai_output(ai: dict, tasks: List[Task], checkin_count: int) -> dict:
    summary = (ai.get("summary") or "").strip()
    risk_flags = list(ai.get("risk_flags") or [])
    recommendations = list(ai.get("recommendations") or [])
    wins = list(ai.get("wins") or [])

    # Ground check-in facts
    if checkin_count > 0:
        lowered = summary.lower()
        if "no check-in" in lowered or "no checkins" in lowered or "no check ins" in lowered:
            summary = f"Saved check-ins: {checkin_count}. " + summary
        else:
            summary = _ensure_text_suffix(summary, f"(Based on {checkin_count} saved check-in{'s' if checkin_count != 1 else ''}.)")
    else:
        summary = _ensure_text_suffix(summary, "No saved check-ins found.")

    # Ground actual-hours/time-estimate facts
    if not _has_recorded_actual_hours(tasks):
        summary = _ensure_text_suffix(
            summary,
            "Actual hours are not recorded, so time estimates cannot be confirmed.",
        )
        rec_text = "Record actual hours for completed work before comparing to time estimates."
        if not any("actual hour" in (r or "").lower() for r in recommendations):
            recommendations.append(rec_text)
        if not any("actual hour" in (f or "").lower() for f in risk_flags):
            risk_flags.append("Actual hours not recorded; time estimate comparisons are insufficient.")

    ai["summary"] = summary
    ai["risk_flags"] = risk_flags
    ai["recommendations"] = recommendations
    ai["wins"] = wins
    return ai


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
            if cached:
                return cached

        all_tasks = self.tasks.list(assignee_id=user_id)
        open_tasks = [t for t in all_tasks if t.status != TaskStatus.done]
        done_tasks = [t for t in all_tasks if t.status == TaskStatus.done]
        workload_hours, completion_date = _predict_workload_and_completion(open_tasks)

        current_user_obj = self.users.get_by_id(user_id)
        profile = f"Name: {current_user_obj.name if current_user_obj else ''}; Job: {getattr(current_user_obj,'job_title',None)}; Skills: {getattr(current_user_obj,'skills',None)}"
        recent_checkins = self.checkins.get_by_user(user_id=user_id, limit=20)
        if recent_checkins:
            checkin_context = "\n".join(
                f"- {c.period_date} ({c.period_type.value if hasattr(c.period_type, 'value') else c.period_type}): "
                f"achieved={getattr(c,'achieved',None)} goal={getattr(c,'goal',None)} blocker={getattr(c,'blocker',None)}"
                for c in recent_checkins[:10]
            )
        else:
            checkin_context = "No saved check-ins found for this user."

        task_context = "\n".join(_task_line(t) for t in all_tasks[:40]) or "No tasks yet."
        has_actual = _has_recorded_actual_hours(all_tasks)

        system_prompt = (
            "You are Trackly's advanced AI analyst. "
            "Provide insights based ONLY on the saved records provided. "
            "Do not invent check-ins, hours, or progress. "
            "If saved check-ins are present, you must acknowledge them and never claim there are no check-ins. "
            "If saved check-ins are missing, state clearly that no saved check-ins were found. "
            "If actual hours are not recorded for tasks, state that actual hours are insufficient and do NOT claim work met, beat, or matched its time estimate. "
            "Praise good work only when supported by records. Be direct about risks without being harsh. "
            "Respond ONLY as JSON with keys: summary (string), risk_level (low|medium|high), "
            "risk_flags (array of short strings), recommendations (array of short strings), "
            "wins (array of short strings)."
        )
        user_prompt = (
            f"Period: {period.value}\nProfile: {profile}\n"
            f"Saved check-ins count: {len(recent_checkins)} (showing up to 10)\n{checkin_context}\n"
            f"Actual hours recorded on any task: {'yes' if has_actual else 'no'}\n"
            f"Tasks:\n{task_context}\nDone: {len(done_tasks)}, Open: {len(open_tasks)}"
        )

        try:
            ai = call_groq_json(system_prompt, user_prompt, model="openai/gpt-oss-20b")
        except Exception:
            notes = []
            if not recent_checkins:
                notes.append("No saved check-ins found.")
            else:
                notes.append(f"{len(recent_checkins)} saved check-in(s) found.")
            if not has_actual:
                notes.append("Actual hours are not recorded, so time estimates cannot be confirmed.")
            summary = f"{len(done_tasks)} of {len(all_tasks)} tasks completed, {len(open_tasks)} open based on saved records. " + " ".join(notes)
            ai = {
                "summary": summary,
                "risk_level": "medium" if any(t.deadline and t.deadline < date.today() for t in open_tasks) else "low",
                "risk_flags": [t.title + " overdue" for t in open_tasks if t.deadline and t.deadline < date.today()][:5],
                "recommendations": (["Log regular check-ins to improve insight accuracy."] if not recent_checkins else []) + (["Record actual hours when work is completed."] if not has_actual else []) or ["Focus on high-priority tasks first.", "Break large tasks into smaller subtasks."],
                "wins": [t.title for t in done_tasks[-3:]] if done_tasks else [],
            }

        ai = _sanitize_ai_output(ai if isinstance(ai, dict) else {}, all_tasks, len(recent_checkins))

        insight = AIInsight(
            scope=InsightScope.individual,
            period=period,
            user_id=user_id,
            summary=ai.get("summary", ""),
            risk_level=RiskLevel(ai.get("risk_level", "low") if ai.get("risk_level") in {"low","medium","high"} else "low"),
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

        group_checkins = self.checkins.get_by_group(group_id, limit=100)
        checkin_counts = {}
        for c in group_checkins:
            checkin_counts[c.user_id] = checkin_counts.get(c.user_id, 0) + 1

        members = self.memberships.get_by_group(group_id)
        member_lines = []
        for m in members:
            u = self.users.get_by_id(m.user_id)
            if not u:
                continue
            their_tasks = [t for t in all_tasks if t.assignee_id == u.id]
            done_n = len([t for t in their_tasks if t.status == TaskStatus.done])
            open_n = len([t for t in their_tasks if t.status != TaskStatus.done])
            actual_n = len([t for t in their_tasks if t.actual_hours is not None and float(t.actual_hours) > 0])
            member_lines.append(
                f"- {u.name}: {done_n} done, {open_n} open, {checkin_counts.get(u.id, 0)} saved check-in(s), {actual_n} task(s) with recorded actual hours"
            )

        task_context = "\n".join(_task_line(t) for t in all_tasks[:60]) or "No tasks yet."
        member_context = "\n".join(member_lines) or "No members."
        has_actual = _has_recorded_actual_hours(all_tasks)
        checkin_count = len(group_checkins)

        system_prompt = (
            "You are Trackly's team AI analyst. "
            "Provide insights based ONLY on the saved records provided. "
            "Do not invent check-ins, hours, or progress. "
            "If saved check-ins are present, acknowledge them and never claim there are no check-ins. "
            "If no saved check-ins exist, state that clearly. "
            "If actual hours are not recorded, state that actual hours are insufficient and do NOT claim work met, beat, or matched its time estimate. "
            "Be honest and constructive. "
            "Respond ONLY as JSON with keys: summary (string), risk_level (low|medium|high), "
            "risk_flags (array of short strings), recommendations (array of short strings), "
            "wins (array of short strings, can mention names), "
            "member_breakdown (array of objects: {name, percent_achieved (0-100 int or null), comment})."
        )
        user_prompt = (
            f"Period: {period.value}\nSaved group check-ins count: {checkin_count}\n"
            f"Actual hours recorded on any group task: {'yes' if has_actual else 'no'}\n"
            f"Members:\n{member_context}\nTasks:\n{task_context}\nTotal open: {len(open_tasks)}"
        )

        try:
            ai = call_groq_json(system_prompt, user_prompt, model="openai/gpt-oss-20b")
        except Exception:
            notes = []
            if checkin_count == 0:
                notes.append("No saved group check-ins found.")
            else:
                notes.append(f"{checkin_count} saved group check-in(s) found.")
            if not has_actual:
                notes.append("Actual hours are not recorded, so time estimates cannot be confirmed.")
            ai = {
                "summary": f"Team overview: {len(open_tasks)} open tasks across {len(members)} members based on saved records. " + " ".join(notes),
                "risk_level": "low",
                "risk_flags": ([] if has_actual else ["Actual hours not recorded; time estimate comparisons are insufficient."]),
                "recommendations": (["Encourage regular check-ins."] if checkin_count == 0 else []) + (["Record actual hours for tasks."] if not has_actual else []) or ["Balance workload across team"],
                "wins": [],
                "member_breakdown": [{"name": ln.split(":")[0].strip("- "), "percent_achieved": None, "comment": "Based on saved records"} for ln in member_lines],
            }

        ai = _sanitize_ai_output(ai if isinstance(ai, dict) else {}, all_tasks, checkin_count)

        member_breakdown_lines = [
            f"{item.get('name','?')}|{item.get('percent_achieved','')}|{item.get('comment','')}"
            for item in (ai.get("member_breakdown") or [])
        ]

        insight = AIInsight(
            scope=InsightScope.group,
            period=period,
            group_id=group_id,
            summary=ai.get("summary", ""),
            risk_level=RiskLevel(ai.get("risk_level", "low") if ai.get("risk_level") in {"low","medium","high"} else "low"),
            risk_flags="\n".join(ai.get("risk_flags", [])),
            recommendations="\n".join(ai.get("recommendations", [])),
            wins="\n".join(ai.get("wins", [])),
            member_breakdown="\n".join(member_breakdown_lines),
            predicted_workload_hours=workload_hours,
            predicted_completion_date=completion_date,
        )
        return self.repo.create(insight)
