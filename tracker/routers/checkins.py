from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from dependency import get_current_user
from tracker.models.user import User
from tracker.schemas.checkin import CheckinCreate, CheckinOut
from tracker.services.checkin_service import CheckinService

router = APIRouter(prefix="/checkins", tags=["checkins"])


@router.post("", response_model=CheckinOut)
def submit_checkin(data: CheckinCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return CheckinService(db).submit(data, current_user)


@router.get("/me", response_model=List[CheckinOut])
def my_checkins(
    group_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return CheckinService(db).history_for_user(current_user.id, group_id=group_id)


@router.get("/group/{group_id}", response_model=List[CheckinOut])
def group_checkins(group_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return CheckinService(db).history_for_group(group_id, current_user)
