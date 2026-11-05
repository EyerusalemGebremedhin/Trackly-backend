import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text

from database import Base


class GroupActivityAction(str, enum.Enum):
    LEADERSHIP_TRANSFERRED = "LEADERSHIP_TRANSFERRED"
    CO_LEAD_ADDED = "CO_LEAD_ADDED"
    LEAD_ROLE_REMOVED = "LEAD_ROLE_REMOVED"
    MEMBER_ADDED = "MEMBER_ADDED"
    MEMBER_INVITED = "MEMBER_INVITED"
    MEMBER_REMOVED = "MEMBER_REMOVED"
    GROUP_ARCHIVED = "GROUP_ARCHIVED"
    GROUP_DELETED = "GROUP_DELETED"
    HELP_REQUEST_CREATED = "HELP_REQUEST_CREATED"
    HELP_REQUEST_RESOLVED = "HELP_REQUEST_RESOLVED"
    GOAL_UPDATED = "GOAL_UPDATED"
    TASK_ASSIGNED = "TASK_ASSIGNED"
    TASK_REASSIGNED = "TASK_REASSIGNED"


class GroupActivity(Base):
    __tablename__ = "group_activity"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    reason = Column(Text, nullable=True)
    actor_name = Column(String, nullable=True)
    target_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
