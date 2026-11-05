from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from dependency import get_current_user
from tracker.models.user import User
from tracker.models.group_checkin_settings import GroupCheckinSettings
from tracker.models.membership import Membership
from tracker.schemas.group_checkin import GroupCheckinSettingsUpdate, GroupCheckinSettingsOut
from datetime import time

router = APIRouter(prefix="/groups", tags=["group-checkins"])


@router.get("/{group_id}/checkin-settings", response_model=GroupCheckinSettingsOut)
def get_checkin_settings(group_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not db.query(Membership).filter(Membership.group_id == group_id, Membership.user_id == current_user.id).first():
        raise HTTPException(status_code=403, detail="Not a member")
    s = db.query(GroupCheckinSettings).filter(GroupCheckinSettings.group_id == group_id).first()
    if not s:
        s = GroupCheckinSettings(group_id=group_id)
        db.add(s)
        db.commit()
        db.refresh(s)
    out = GroupCheckinSettingsOut(
        id=s.id,
        group_id=s.group_id,
        enabled=s.enabled,
        opens_at=s.opens_at.strftime("%H:%M") if s.opens_at else None,
        deadline_at=s.deadline_at.strftime("%H:%M") if s.deadline_at else None,
        days_of_week=s.days_of_week,
        timezone=s.timezone,
        reminder_minutes_before=s.reminder_minutes_before,
        list_missed_publicly=s.list_missed_publicly,
    )
    return out


@router.put("/{group_id}/checkin-settings", response_model=GroupCheckinSettingsOut)
def update_checkin_settings(group_id: int, data: GroupCheckinSettingsUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    m = db.query(Membership).filter(Membership.group_id == group_id, Membership.user_id == current_user.id).first()
    if not m or (str(m.role).lower() != 'lead'):
        raise HTTPException(status_code=403, detail="Only lead can update check-in settings")
    s = db.query(GroupCheckinSettings).filter(GroupCheckinSettings.group_id == group_id).first()
    if not s:
        s = GroupCheckinSettings(group_id=group_id)
        db.add(s)
    if data.enabled is not None:
        s.enabled = data.enabled
    if data.opens_at:
        try:
            h, mi = data.opens_at.split(":")
            s.opens_at = time(int(h), int(mi))
        except Exception:
            pass
    if data.deadline_at:
        try:
            h, mi = data.deadline_at.split(":")
            s.deadline_at = time(int(h), int(mi))
        except Exception:
            pass
    if data.days_of_week is not None:
        s.days_of_week = data.days_of_week
    if data.timezone is not None:
        s.timezone = data.timezone
    if data.reminder_minutes_before is not None:
        s.reminder_minutes_before = data.reminder_minutes_before
    if data.list_missed_publicly is not None:
        s.list_missed_publicly = data.list_missed_publicly
    db.commit()
    db.refresh(s)
    out = GroupCheckinSettingsOut(
        id=s.id,
        group_id=s.group_id,
        enabled=s.enabled,
        opens_at=s.opens_at.strftime("%H:%M") if s.opens_at else None,
        deadline_at=s.deadline_at.strftime("%H:%M") if s.deadline_at else None,
        days_of_week=s.days_of_week,
        timezone=s.timezone,
        reminder_minutes_before=s.reminder_minutes_before,
        list_missed_publicly=s.list_missed_publicly,
    )
    return out
