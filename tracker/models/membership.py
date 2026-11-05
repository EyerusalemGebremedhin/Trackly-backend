from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, UniqueConstraint, Text
from sqlalchemy.orm import relationship

from database import Base


class Membership(Base):
    """
    Links a User to a Group with a role scoped to that group only.
    """
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "group_id", name="uq_user_group"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    role = Column(String, default="member", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    added_reason = Column(Text, nullable=True)

    user = relationship("User", back_populates="memberships", foreign_keys=[user_id])
    group = relationship("Group", back_populates="memberships")
