import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text, Boolean
from sqlalchemy.orm import relationship

from database import Base


class CheckinCadence(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"
    sprint = "sprint"


class Group(Base):
    """A team, company department, or project group. Any user can create one and becomes its first lead."""
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)  # what the project/group is about
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    checkin_cadence = Column(Enum(CheckinCadence), default=CheckinCadence.weekly)
    is_archived = Column(Boolean, default=False)  # moved to "Past Groups" when true
    created_at = Column(DateTime, default=datetime.utcnow)

    memberships = relationship("Membership", back_populates="group", cascade="all, delete-orphan")
    goals = relationship("GroupGoal", back_populates="group", cascade="all, delete-orphan")
