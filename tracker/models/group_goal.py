from datetime import datetime, date

from sqlalchemy import Column, Integer, DateTime, Date, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship

from database import Base
from tracker.models.checkin import PeriodType


class GroupGoal(Base):
    """The lead's stated goal for a group, for one period (a day, a week, or a sprint)."""
    __tablename__ = "group_goals"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    goal_text = Column(Text, nullable=False)
    period_type = Column(Enum(PeriodType), default=PeriodType.weekly, nullable=False)
    period_start = Column(Date, default=date.today, nullable=False)
    period_end = Column(Date, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    group = relationship("Group", back_populates="goals")
