from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, UniqueConstraint

from database import Base


class SentReminder(Base):
    __tablename__ = "sent_reminders"
    __table_args__ = (UniqueConstraint('group_id', 'reminder_date', 'reminder_type', name='uq_sent_reminder'),)

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True)
    reminder_date = Column(Date, nullable=False)
    reminder_type = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
