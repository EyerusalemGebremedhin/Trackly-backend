from datetime import datetime, time
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Time, Text

from database import Base


class GroupCheckinSettings(Base):
    __tablename__ = "group_checkin_settings"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), unique=True, nullable=False, index=True)
    enabled = Column(Boolean, default=True)
    opens_at = Column(Time, nullable=True)
    deadline_at = Column(Time, nullable=True)
    days_of_week = Column(String, nullable=True)  # comma separated e.g. mon,tue,wed,thu,fri
    timezone = Column(String, default="Africa/Nairobi")
    reminder_minutes_before = Column(Integer, default=60)
    list_missed_publicly = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
