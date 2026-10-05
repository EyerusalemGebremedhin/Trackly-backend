from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session

from tracker.models.checkin import Checkin


class CheckinRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, checkin: Checkin) -> Checkin:
        self.db.add(checkin)
        self.db.commit()
        self.db.refresh(checkin)
        return checkin

    def get_by_user(self, user_id: int, group_id: Optional[int] = None, limit: int = 100) -> List[Checkin]:
        query = self.db.query(Checkin).filter(Checkin.user_id == user_id)
        if group_id is not None:
            query = query.filter(Checkin.group_id == group_id)
        return query.order_by(Checkin.period_date.desc()).limit(limit).all()

    def get_by_group(self, group_id: int, limit: int = 200) -> List[Checkin]:
        return (
            self.db.query(Checkin)
            .filter(Checkin.group_id == group_id)
            .order_by(Checkin.period_date.desc())
            .limit(limit)
            .all()
        )

    def get_for_period(self, user_id: int, group_id: Optional[int], period_date: date) -> Optional[Checkin]:
        query = self.db.query(Checkin).filter(
            Checkin.user_id == user_id,
            Checkin.group_id == group_id,
            Checkin.period_date == period_date,
        )
        return query.first()
