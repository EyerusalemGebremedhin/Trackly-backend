from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from database import Base


class UserSkill(Base):
    __tablename__ = "user_skills"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    name = Column(String(40), nullable=False)
    key = Column(String(40), nullable=False, index=True)
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_user_skill"),)
