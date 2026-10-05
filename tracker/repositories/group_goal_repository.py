from typing import List, Optional
from sqlalchemy.orm import Session

from tracker.models.group_goal import GroupGoal


class GroupGoalRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, goal: GroupGoal) -> GroupGoal:
        self.db.add(goal)
        self.db.commit()
        self.db.refresh(goal)
        return goal

    def get_latest(self, group_id: int) -> Optional[GroupGoal]:
        return (
            self.db.query(GroupGoal)
            .filter(GroupGoal.group_id == group_id)
            .order_by(GroupGoal.period_start.desc())
            .first()
        )

    def get_by_group(self, group_id: int) -> List[GroupGoal]:
        return (
            self.db.query(GroupGoal)
            .filter(GroupGoal.group_id == group_id)
            .order_by(GroupGoal.period_start.desc())
            .all()
        )
