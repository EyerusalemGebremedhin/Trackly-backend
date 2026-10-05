from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from dependency import get_current_user
from tracker.models.user import User
from tracker.models.ai_insight import AIInsight, InsightPeriod
from tracker.schemas.ai_insight import AIInsightOut, MemberBreakdownItem
from tracker.services.ai_insight_service import AIInsightService

router = APIRouter(prefix="/insights", tags=["insights"])


def _lines(text):
    return [l for l in (text or "").split("\n") if l.strip()]


def _to_out(insight: AIInsight) -> AIInsightOut:
    breakdown = []
    for line in _lines(insight.member_breakdown):
        parts = line.split("|")
        name = parts[0] if len(parts) > 0 else "?"
        pct_raw = parts[1] if len(parts) > 1 else ""
        comment = parts[2] if len(parts) > 2 else ""
        try:
            pct = int(pct_raw) if pct_raw not in ("", "None") else None
        except ValueError:
            pct = None
        breakdown.append(MemberBreakdownItem(name=name, percent_achieved=pct, comment=comment))

    return AIInsightOut(
        id=insight.id,
        scope=insight.scope,
        period=insight.period,
        user_id=insight.user_id,
        group_id=insight.group_id,
        group_goal_id=insight.group_goal_id,
        summary=insight.summary,
        risk_level=insight.risk_level,
        risk_flags=_lines(insight.risk_flags),
        recommendations=_lines(insight.recommendations),
        member_breakdown=breakdown,
        wins=_lines(insight.wins),
        predicted_workload_hours=insight.predicted_workload_hours,
        predicted_completion_date=insight.predicted_completion_date,
        generated_at=insight.generated_at,
    )


@router.get("/me", response_model=AIInsightOut)
def my_insight(
    period: InsightPeriod = InsightPeriod.weekly,
    refresh: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    insight = AIInsightService(db).get_or_generate_individual(current_user.id, current_user, period, refresh=refresh)
    return _to_out(insight)


@router.get("/group/{group_id}", response_model=AIInsightOut)
def group_insight(
    group_id: int,
    period: InsightPeriod = InsightPeriod.weekly,
    refresh: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    insight = AIInsightService(db).get_or_generate_group(group_id, current_user, period, refresh=refresh)
    return _to_out(insight)
