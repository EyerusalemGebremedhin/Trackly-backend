from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from dependency import get_current_user
from tracker.models.user import User
from tracker.schemas.feedback import FeedbackCreate, FeedbackOut
from tracker.services.feedback_service import FeedbackService

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackOut)
def give_feedback(data: FeedbackCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return FeedbackService(db).give(data, current_user)


@router.get("/user/{user_id}", response_model=List[FeedbackOut])
def feedback_for_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return FeedbackService(db).for_user(user_id)
