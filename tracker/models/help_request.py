import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text

from database import Base


class HelpRequestStatus(str, enum.Enum):
    open = "open"
    resolved = "resolved"


class HelpRequest(Base):
    """
    A member flagging they're stuck on a task and need help in a specific skill area,
    so the group can see who's listed with that skill and step in.
    """
    __tablename__ = "help_requests"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    skill_needed = Column(String, nullable=False)
    note = Column(Text, nullable=True)
    status = Column(Enum(HelpRequestStatus), default=HelpRequestStatus.open, nullable=False)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
