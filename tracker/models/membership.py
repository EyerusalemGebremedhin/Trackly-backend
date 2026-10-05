import enum
from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


class MembershipRole(str, enum.Enum):
    lead = "lead"
    member = "member"


class Membership(Base):
    """
    Links a User to a Group with a role scoped to that group only.
    The same user can be `lead` of one group and `member` of another.
    Added directly by a lead (Jira-style) - an email notification goes out,
    but membership is active immediately, no accept step required.
    """
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "group_id", name="uq_user_group"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    role = Column(Enum(MembershipRole), default=MembershipRole.member, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="memberships", foreign_keys=[user_id])
    group = relationship("Group", back_populates="memberships")
