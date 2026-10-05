import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Enum, Text, Float

from database import Base


class InsightScope(str, enum.Enum):
    individual = "individual"
    group = "group"


class RiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class InsightPeriod(str, enum.Enum):
    weekly = "weekly"
    monthly = "monthly"
    general = "general"  # all-time / overall picture


class AIInsight(Base):
    """
    Cached output of the AI analyzer, so we don't call the LLM on every page load.
    For scope=group, member_breakdown holds a per-person read like:
    "David - good job, ~75% of this week's goal. Nati - finished login page, no blockers."
    """
    __tablename__ = "ai_insights"

    id = Column(Integer, primary_key=True, index=True)
    scope = Column(Enum(InsightScope), nullable=False)
    period = Column(Enum(InsightPeriod), default=InsightPeriod.weekly, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)         # set when scope == individual
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)       # set when scope == group
    group_goal_id = Column(Integer, ForeignKey("group_goals.id"), nullable=True)

    summary = Column(Text, nullable=False)
    risk_level = Column(Enum(RiskLevel), default=RiskLevel.low)
    risk_flags = Column(Text, nullable=True)          # newline-separated
    recommendations = Column(Text, nullable=True)      # newline-separated
    member_breakdown = Column(Text, nullable=True)     # newline-separated, one line per person (group scope only)
    wins = Column(Text, nullable=True)                 # newline-separated - things done well / on time, praised explicitly

    predicted_workload_hours = Column(Float, nullable=True)   # forecasted hours of open work remaining
    predicted_completion_date = Column(Date, nullable=True)   # forecasted date all open work finishes

    generated_at = Column(DateTime, default=datetime.utcnow)
