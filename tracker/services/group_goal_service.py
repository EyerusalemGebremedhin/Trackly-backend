from datetime import date
from fastapi import HTTPException
from sqlalchemy.orm import Session

from tracker.models.user import User
from tracker.models.group_goal import GroupGoal
from tracker.models.membership import MembershipRole
from tracker.repositories.group_goal_repository import GroupGoalRepository
from tracker.repositories.membership_repository import MembershipRepository
from tracker.schemas.group_goal import GroupGoalCreate


class GroupGoalService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = GroupGoalRepository(db)
        self.memberships = MembershipRepository(db)

    def create(self, group_id: int, data: GroupGoalCreate, current_user: User) -> GroupGoal:
        membership = self.memberships.get(current_user.id, group_id)
        if not membership or membership.role != MembershipRole.lead:
            raise HTTPException(status_code=403, detail="Only a lead can set the group's goal")

        goal = GroupGoal(
            group_id=group_id,
            created_by=current_user.id,
            goal_text=data.goal_text,
            period_type=data.period_type,
            period_start=data.period_start or date.today(),
            period_end=data.period_end,
        )
        return self.repo.create(goal)

    def latest(self, group_id: int):
        return self.repo.get_latest(group_id)

    def history(self, group_id: int):
        return self.repo.get_by_group(group_id)