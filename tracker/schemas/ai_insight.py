from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel

from tracker.models.ai_insight import InsightScope, RiskLevel, InsightPeriod


class MemberBreakdownItem(BaseModel):
    name: str
    percent_achieved: Optional[int] = None
    comment: str


class AIInsightOut(BaseModel):
    id: int
    scope: InsightScope
    period: InsightPeriod
    user_id: Optional[int]
    group_id: Optional[int]
    group_goal_id: Optional[int]
    summary: str
    risk_level: RiskLevel
    risk_flags: List[str]
    recommendations: List[str]
    member_breakdown: List[MemberBreakdownItem]
    wins: List[str]
    predicted_workload_hours: Optional[float] = None
    predicted_completion_date: Optional[date] = None
    generated_at: datetime
