from fastapi import HTTPException
from sqlalchemy.orm import Session

from tracker.models.user import User
from tracker.models.feedback import Feedback, FeedbackSource
from tracker.repositories.feedback_repository import FeedbackRepository
from tracker.schemas.feedback import FeedbackCreate


class FeedbackService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = FeedbackRepository(db)

    def give(self, data: FeedbackCreate, current_user: User) -> Feedback:
        feedback = Feedback(
            about_user_id=data.about_user_id,
            given_by_id=current_user.id,
            source=FeedbackSource.lead,
            content=data.content,
            task_id=data.task_id,
            checkin_id=data.checkin_id,
        )
        return self.repo.create(feedback)

    def for_user(self, about_user_id: int):
        return self.repo.get_for_user(about_user_id)

    def save_ai_feedback(self, about_user_id: int, content: str, checkin_id=None) -> Feedback:
        feedback = Feedback(
            about_user_id=about_user_id,
            given_by_id=None,
            source=FeedbackSource.ai,
            content=content,
            checkin_id=checkin_id,
        )
        return self.repo.create(feedback)
