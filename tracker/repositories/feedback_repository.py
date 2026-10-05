from typing import List
from sqlalchemy.orm import Session

from tracker.models.feedback import Feedback


class FeedbackRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, feedback: Feedback) -> Feedback:
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    def get_for_user(self, about_user_id: int) -> List[Feedback]:
        return (
            self.db.query(Feedback)
            .filter(Feedback.about_user_id == about_user_id)
            .order_by(Feedback.created_at.desc())
            .all()
        )
