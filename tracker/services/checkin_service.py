from datetime import date, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session

from tracker.models.user import User
from tracker.models.checkin import Checkin, PeriodType
from tracker.models.membership import MembershipRole
from tracker.repositories.checkin_repository import CheckinRepository
from tracker.repositories.membership_repository import MembershipRepository
from tracker.schemas.checkin import CheckinCreate


def period_start_for(period_type: PeriodType, on: date = None) -> date:
    """
    Normalizes 'today' to the start of its period, so two check-ins in the
    same week (or sprint) land on the same period_date and can be matched
    against each other (e.g. for the "has this person checked in yet" alert).
    """
    on = on or date.today()
    if period_type in (PeriodType.weekly, PeriodType.sprint):
        return on - timedelta(days=on.weekday())  # Monday of that week
    return on  # daily: the day itself


class CheckinService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CheckinRepository(db)
        self.memberships = MembershipRepository(db)

    def submit(self, data: CheckinCreate, current_user: User) -> Checkin:
        if data.group_id:
            membership = self.memberships.get(current_user.id, data.group_id)
            if not membership:
                raise HTTPException(status_code=403, detail="You're not a member of that group")

        period_date = data.period_date or period_start_for(data.period_type)

        checkin = Checkin(
            user_id=current_user.id,
            group_id=data.group_id,
            task_id=data.task_id,
            goal=data.goal,
            achieved=data.achieved,
            went_well=data.went_well,
            didnt_go_well=data.didnt_go_well,
            improve=data.improve,
            blocker=data.blocker,
            period_type=data.period_type,
            period_date=period_date,
        )
        return self.repo.create(checkin)

    def history_for_user(self, user_id: int, group_id=None):
        return self.repo.get_by_user(user_id, group_id=group_id)

    def history_for_group(self, group_id: int, current_user: User):
        membership = self.memberships.get(current_user.id, group_id)
        if not membership or membership.role != MembershipRole.lead:
            raise HTTPException(status_code=403, detail="Only a lead can view the group's check-in history")
        return self.repo.get_by_group(group_id)
