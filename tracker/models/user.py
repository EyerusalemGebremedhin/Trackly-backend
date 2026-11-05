from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    skills = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    verification_code = Column(String, nullable=True)
    verification_expires_at = Column(DateTime, nullable=True)
    activation_token = Column(String, nullable=True)
    activation_expires_at = Column(DateTime, nullable=True)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    memberships = relationship("Membership", back_populates="user", foreign_keys="Membership.user_id")
    tasks = relationship("Task", back_populates="assignee", foreign_keys="Task.assignee_id")
    checkins = relationship("Checkin", back_populates="user")
