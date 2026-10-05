import enum
from datetime import datetime, date

from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship

from database import Base


class PeriodType(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"
    sprint = "sprint"


class Checkin(Base):
    """
    A structured standup entry - what someone submits for a given period,
    for themselves individually or against a group's goal.
    group_id is nullable: null means a purely personal check-in.
    """
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)  # optional link to a specific task

    goal = Column(Text, nullable=True)             # what they aimed for this period
    achieved = Column(Text, nullable=False)         # what actually got done
    went_well = Column(Text, nullable=True)
    didnt_go_well = Column(Text, nullable=True)
    improve = Column(Text, nullable=True)           # what to improve next time
    blocker = Column(Text, nullable=True)            # what's stopping them right now

    period_type = Column(Enum(PeriodType), default=PeriodType.daily, nullable=False)
    period_date = Column(Date, default=date.today, nullable=False)  # day, or start-of-week/sprint
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="checkins")
