from fastapi import HTTPException
from sqlalchemy.orm import Session

from tracker.models.user import User
from tracker.models.help_request import HelpRequest, HelpRequestStatus
from tracker.repositories.help_request_repository import HelpRequestRepository
from tracker.repositories.membership_repository import MembershipRepository
from tracker.schemas.help_request import HelpRequestCreate


class HelpRequestService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = HelpRequestRepository(db)
        self.memberships = MembershipRepository(db)

    def create(self, group_id: int, data: HelpRequestCreate, current_user: User) -> HelpRequest:
        if not self.memberships.get(current_user.id, group_id):
            raise HTTPException(status_code=403, detail="Not a member of this group")
        return self.repo.create(HelpRequest(
            group_id=group_id,
            task_id=data.task_id,
            requested_by=current_user.id,
            skill_needed=data.skill_needed,
            note=data.note,
        ))

    def list_for_group(self, group_id: int, current_user: User, open_only: bool = False):
        if not self.memberships.get(current_user.id, group_id):
            raise HTTPException(status_code=403, detail="Not a member of this group")
        status = HelpRequestStatus.open if open_only else None
        return self.repo.list_for_group(group_id, status=status)

    def resolve(self, request_id: int, current_user: User) -> HelpRequest:
        request = self.repo.get_by_id(request_id)
        if not request:
            raise HTTPException(status_code=404, detail="Help request not found")
        if not self.memberships.get(current_user.id, request.group_id):
            raise HTTPException(status_code=403, detail="Not a member of this group")
        return self.repo.resolve(request, resolved_by=current_user.id)

    def matching_helpers(self, group_id: int, skill: str, current_user: User):
        """Members of the group whose listed skills mention the needed skill area."""
        if not self.memberships.get(current_user.id, group_id):
            raise HTTPException(status_code=403, detail="Not a member of this group")
        members = self.memberships.get_by_group(group_id)
        from tracker.repositories.user_repository import UserRepository
        users_repo = UserRepository(self.db)
        matches = []
        for m in members:
            u = users_repo.get_by_id(m.user_id)
            if u and u.skills and skill.lower() in u.skills.lower():
                matches.append(u)
        return matches
