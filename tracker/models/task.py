import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey, Enum, Text, Boolean
from sqlalchemy.orm import relationship

from database import Base


class TaskStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    in_review = "in_review"
    blocked = "blocked"
    done = "done"


class PriorityEnum(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class TaskPeriodType(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class Task(Base):
    """
    A task. group_id is nullable: if set, it's a group-assigned task (visible to
    that group's lead); if null, it's purely personal to the assignee.

    period_type and is_archived are mainly used for personal (group_id is null) tasks:
    period_type is the plan's own cadence (daily/weekly/monthly) - freely editable later
    in case it was set by mistake. is_archived lets someone move a finished personal
    plan into their "Past plans" list, without deleting it.
    """
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)

    priority = Column(Enum(PriorityEnum), default=PriorityEnum.medium)
    status = Column(Enum(TaskStatus), default=TaskStatus.todo)
    period_type = Column(Enum(TaskPeriodType), nullable=True)
    is_archived = Column(Boolean, default=False)

    estimated_hours = Column(Float, default=0)
    actual_hours = Column(Float, default=0)
    percent_complete = Column(Integer, default=0)

    deadline = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    is_management_duty = Column(Boolean, default=False)

    assignee = relationship("User", back_populates="tasks", foreign_keys=[assignee_id])


class TaskReassignment(Base):
    """History of a task being handed from one assignee to another. Never deleted."""
    __tablename__ = "task_reassignments"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reassigned_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)