from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from dependency import get_current_user
from tracker.models.user import User
from tracker.schemas.group_goal import GroupGoalCreate, GroupGoalOut
from tracker.services.group_goal_service import GroupGoalService

router = APIRouter(prefix="/groups/{group_id}/goals", tags=["group_goals"])


@router.post("", response_model=GroupGoalOut)
def set_goal(
    group_id: int, data: GroupGoalCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return GroupGoalService(db).create(group_id, data, current_user)


@router.get("/latest", response_model=GroupGoalOut)
def latest_goal(group_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return GroupGoalService(db).latest(group_id)


@router.get("", response_model=List[GroupGoalOut])
def goal_history(group_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return GroupGoalService(db).history(group_id)
