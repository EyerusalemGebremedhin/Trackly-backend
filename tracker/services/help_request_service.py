from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from tracker.models.help_request import HelpRequest, HelpRequestStatus
from tracker.repositories.help_request_repository import HelpRequestRepository
from tracker.repositories.membership_repository import MembershipRepository
from tracker.repositories.user_repository import UserRepository
from tracker.repositories.task_repository import TaskRepository
from tracker.schemas.help_request import HelpRequestCreate


class HelpRequestService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = HelpRequestRepository(db)
        self.memberships = MembershipRepository(db)
        self.users = UserRepository(db)
        self.tasks = TaskRepository(db)

    def _require_member(self, user_id: int, group_id: int):
        if not self.memberships.get(user_id, group_id):
            raise HTTPException(status_code=403, detail="Not a member of this group")

    def _require_lead(self, user_id: int, group_id: int):
        m = self.memberships.get(user_id, group_id)
        if not m or m.role != 'lead':
            raise HTTPException(status_code=403, detail="Only the group's lead can do this")
        return m

    def create(self, group_id: int, data: HelpRequestCreate, current_user):
        self._require_member(current_user.id, group_id)
        if data.task_id:
            task = self.tasks.get_by_id(data.task_id)
            if not task or task.group_id != group_id:
                raise HTTPException(status_code=404, detail="Task not found")
        hr = HelpRequest(
            group_id=group_id,
            task_id=data.task_id,
            requested_by=current_user.id,
            skill_needed=data.skill_needed,
            note=data.note,
            reason=data.reason,
            task_type=data.task_type,
        )
        return self.repo.create(hr)

    def list(self, group_id: int, current_user, open_only: bool = True):
        self._require_member(current_user.id, group_id)
        return self.repo.list(group_id=group_id, open_only=open_only)

    def resolve(self, group_id: int, request_id: int, current_user):
        self._require_lead(current_user.id, group_id)
        hr = self.repo.get_by_id(request_id)
        if not hr or hr.group_id != group_id:
            raise HTTPException(status_code=404, detail="Help request not found")
        return self.repo.update(hr, {"status": HelpRequestStatus.resolved, "resolved_by": current_user.id, "resolved_at": datetime.utcnow()})
