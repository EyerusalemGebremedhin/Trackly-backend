from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    """
    A single account. Every user can track things purely individually.
    Group role (lead vs member) lives on Membership, not here -
    the same person can lead one group and be a member of another.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    skills = Column(String, nullable=True)  # simple comma-separated list for v1
    created_at = Column(DateTime, default=datetime.utcnow)

    memberships = relationship("Membership", back_populates="user", foreign_keys="Membership.user_id")
    tasks = relationship("Task", back_populates="assignee", foreign_keys="Task.assignee_id")
    checkins = relationship("Checkin", back_populates="user")
