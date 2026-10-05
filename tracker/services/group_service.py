from fastapi import HTTPException
from sqlalchemy.orm import Session

from tracker.models.user import User
from tracker.models.group import Group
from tracker.models.membership import Membership, MembershipRole
from tracker.repositories.group_repository import GroupRepository
from tracker.repositories.membership_repository import MembershipRepository
from tracker.repositories.user_repository import UserRepository
from tracker.schemas.group import GroupCreate, GroupUpdate, MemberAdd


class GroupService:
    def __init__(self, db: Session):
        self.db = db
        self.groups = GroupRepository(db)
        self.memberships = MembershipRepository(db)
        self.users = UserRepository(db)

    def _require_lead(self, user_id: int, group_id: int) -> Membership:
        m = self.memberships.get(user_id, group_id)
        if not m or m.role != MembershipRole.lead:
            raise HTTPException(status_code=403, detail="Only the group's lead can do this")
        return m

    def create(self, data: GroupCreate, creator: User) -> Group:
        group = self.groups.create(Group(
            name=data.name,
            description=data.description,
            created_by=creator.id,
            checkin_cadence=data.checkin_cadence,
            is_archived=False,
        ))
        self.memberships.create(Membership(user_id=creator.id, group_id=group.id, role=MembershipRole.lead))
        return group

    def get(self, group_id: int, current_user: User) -> Group:
        group = self.groups.get_by_id(group_id)
        if not group or not self.memberships.get(current_user.id, group_id):
            raise HTTPException(status_code=404, detail="Group not found")
        return group

    def list_for_user(self, current_user: User, archived: bool = False):
        memberships = self.memberships.get_by_user(current_user.id)
        role_by_group = {m.group_id: m.role for m in memberships}
        if not role_by_group:
            return []
        groups = self.groups.list_by_ids(list(role_by_group.keys()), archived=archived)
        return [(g, role_by_group[g.id]) for g in groups]

    def get_my_role(self, group_id: int, user_id: int) -> MembershipRole:
        m = self.memberships.get(user_id, group_id)
        if not m:
            raise HTTPException(status_code=404, detail="Group not found")
        return m.role

    def update(self, group_id: int, data: GroupUpdate, current_user: User) -> Group:
        self._require_lead(current_user.id, group_id)
        group = self.groups.get_by_id(group_id)
        return self.groups.update(group, data.model_dump(exclude_unset=True))

    def archive(self, group_id: int, current_user: User, archived: bool = True) -> Group:
        self._require_lead(current_user.id, group_id)
        group = self.groups.get_by_id(group_id)
        return self.groups.update(group, {"is_archived": archived})

    def add_member(self, group_id: int, data: MemberAdd, current_user: User) -> Membership:
        self._require_lead(current_user.id, group_id)
        member_user = self.users.get_by_email(data.email)
        if not member_user:
            raise HTTPException(status_code=404, detail=f"No user found with email {data.email}")
        if self.memberships.get(member_user.id, group_id):
            raise HTTPException(status_code=400, detail="Already a member of this group")
        return self.memberships.create(Membership(user_id=member_user.id, group_id=group_id, role=data.role))

    def remove_member(self, group_id: int, member_user_id: int, current_user: User) -> None:
        self._require_lead(current_user.id, group_id)
        if member_user_id == current_user.id:
            raise HTTPException(status_code=400, detail="Use transfer-lead before removing yourself")
        membership = self.memberships.get(member_user_id, group_id)
        if not membership:
            raise HTTPException(status_code=404, detail="That person isn't a member of this group")
        self.memberships.delete(membership)

    def transfer_lead(self, group_id: int, new_lead_user_id: int, current_user: User) -> Membership:
        current_lead_membership = self._require_lead(current_user.id, group_id)
        new_lead_membership = self.memberships.get(new_lead_user_id, group_id)
        if not new_lead_membership:
            raise HTTPException(status_code=404, detail="That person isn't a member of this group")
        self.memberships.update_role(current_lead_membership, MembershipRole.member)
        return self.memberships.update_role(new_lead_membership, MembershipRole.lead)

    def list_members(self, group_id: int, current_user: User):
        if not self.memberships.get(current_user.id, group_id):
            raise HTTPException(status_code=403, detail="Not a member of this group")
        return self.memberships.get_by_group(group_id)