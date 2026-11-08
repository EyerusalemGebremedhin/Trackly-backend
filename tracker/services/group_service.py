from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from tracker.models.user import User
from tracker.models.group import Group
from tracker.models.membership import Membership
from tracker.models.group_activity import GroupActivity
from tracker.repositories.group_repository import GroupRepository
from tracker.repositories.membership_repository import MembershipRepository
from tracker.repositories.user_repository import UserRepository
from tracker.schemas.group import GroupCreate, GroupUpdate, MemberAdd
from tracker.services.security import hash_password, generate_verification_code, generate_secure_token
from tracker.services.auth_service import AuthService
from tracker.services.notification_service import NotificationService


class GroupService:
    def __init__(self, db: Session):
        self.db = db
        self.groups = GroupRepository(db)
        self.memberships = MembershipRepository(db)
        self.users = UserRepository(db)

    def _require_lead(self, user_id: int, group_id: int) -> Membership:
        m = self.memberships.get(user_id, group_id)
        if not m or str(m.role).lower() != 'lead':
            raise HTTPException(status_code=403, detail="Only the group's lead can do this")
        return m

    def create(self, data: GroupCreate, creator: User) -> Group:
        existing = self.groups.get_by_name_for_user(creator.id, data.name)
        if existing:
            raise HTTPException(status_code=400, detail="Group with this name already exists")
        group = self.groups.create(Group(
            name=data.name,
            description=data.description,
            created_by=creator.id,
            checkin_cadence=data.checkin_cadence,
            is_archived=False,
        ))
        self.memberships.create(Membership(user_id=creator.id, group_id=group.id, role="lead"))
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

    def get_my_role(self, group_id: int, user_id: int):
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

    def _log_activity(self, group_id: int, actor: User, action: str, reason: str = None, target_user: User = None):
        try:
            log = GroupActivity(
                group_id=group_id,
                actor_id=actor.id,
                target_user_id=target_user.id if target_user else None,
                action=action,
                reason=reason,
                actor_name=actor.name,
                target_name=target_user.name if target_user else None,
            )
            self.db.add(log)
            self.db.commit()
        except Exception:
            self.db.rollback()

    def add_member(self, group_id: int, data: MemberAdd, current_user: User) -> Membership:
        self._require_lead(current_user.id, group_id)
        member_user = self.users.get_by_email(data.email)
        reason = getattr(data, 'reason', None) or getattr(data, 'added_reason', None)
        role = getattr(data, 'role', None) or "member"
        if not member_user:
            name = data.email.split("@")[0]
            activation_token = generate_verification_code()
            user = User(
                name=name,
                email=data.email,
                hashed_password=hash_password(generate_secure_token()),
                skills=None,
                is_verified=True,
                is_active=False,
                activation_token=activation_token,
                activation_expires_at=datetime.utcnow() + timedelta(minutes=15),
            )
            user = self.users.create(user)
            self.db.commit()
            self.db.refresh(user)
            membership = self.memberships.create(Membership(user_id=user.id, group_id=group_id, role=str(role), added_reason=reason))
            auth_service = AuthService(self.db)
            auth_service._send_activation_email(user, activation_token)
            self._log_activity(group_id, current_user, "MEMBER_INVITED", reason, user)
            return membership
        if self.memberships.get(member_user.id, group_id):
            raise HTTPException(status_code=400, detail="Already a member of this group")
        membership = self.memberships.create(Membership(user_id=member_user.id, group_id=group_id, role=str(role), added_reason=reason))
        self._log_activity(group_id, current_user, "MEMBER_ADDED", reason, member_user)
        return membership

    def remove_member(self, group_id: int, member_user_id: int, current_user: User, reason: str = None) -> None:
        self._require_lead(current_user.id, group_id)
        if member_user_id == current_user.id:
            raise HTTPException(status_code=400, detail="Use transfer-lead before removing yourself")
        membership = self.memberships.get(member_user_id, group_id)
        if not membership:
            raise HTTPException(status_code=404, detail="That person isn't a member of this group")
        target = self.users.get_by_id(member_user_id)
        self.memberships.delete(membership)
        self._log_activity(group_id, current_user, "MEMBER_REMOVED", reason, target)

    def transfer_lead(self, group_id: int, new_lead_user_id: int, current_user: User, reason: str = None) -> Membership:
        if not reason or len(reason.strip()) < 10:
            raise HTTPException(status_code=400, detail="Reason is required and must be at least 10 characters")
        current_lead_membership = self._require_lead(current_user.id, group_id)
        new_lead_membership = self.memberships.get(new_lead_user_id, group_id)
        if not new_lead_membership:
            raise HTTPException(status_code=404, detail="That person isn't a member of this group")
        if new_lead_user_id == current_user.id:
            raise HTTPException(status_code=400, detail="You are already the lead")
        target = self.users.get_by_id(new_lead_user_id)
        self.memberships.update_role(current_lead_membership, 'member')
        result = self.memberships.update_role(new_lead_membership, 'lead')
        self._log_activity(group_id, current_user, "LEADERSHIP_TRANSFERRED", reason, target)
        members = self.memberships.get_by_group(group_id)
        ns = NotificationService(self.db)
        for m in members:
            if m.user_id != current_user.id:
                ns.notify(m.user_id, "Leadership transferred", f"{current_user.name} transferred leadership to {target.name if target else new_lead_user_id}.", type="info", group_id=group_id)
        return result

    def add_co_lead(self, group_id: int, user_id: int, current_user: User, reason: str = None) -> Membership:
        if not reason or len(reason.strip()) < 10:
            raise HTTPException(status_code=400, detail="Reason is required and must be at least 10 characters")
        self._require_lead(current_user.id, group_id)
        membership = self.memberships.get(user_id, group_id)
        if not membership:
            raise HTTPException(status_code=404, detail="That person isn't a member of this group")
        target = self.users.get_by_id(user_id)
        result = self.memberships.update_role(membership, 'lead')
        self._log_activity(group_id, current_user, "CO_LEAD_ADDED", reason, target)
        members = self.memberships.get_by_group(group_id)
        ns = NotificationService(self.db)
        for m in members:
            if m.user_id != current_user.id:
                ns.notify(m.user_id, "Co-lead added", f"{current_user.name} added {target.name if target else user_id} as a co-lead.", type="info", group_id=group_id)
        return result

    def update_member_role(self, group_id: int, member_user_id: int, new_role: str, current_user: User, reason: str = None) -> Membership:
        self._require_lead(current_user.id, group_id)
        if not reason or len(reason.strip()) < 10:
            raise HTTPException(status_code=400, detail="Reason is required and must be at least 10 characters")
        membership = self.memberships.get(member_user_id, group_id)
        if not membership:
            raise HTTPException(status_code=404, detail="That person isn't a member of this group")
        target = self.users.get_by_id(member_user_id)
        old_role = membership.role
        result = self.memberships.update_role(membership, new_role)
        self._log_activity(group_id, current_user, "ROLE_CHANGED", reason, target)
        members = self.memberships.get_by_group(group_id)
        ns = NotificationService(self.db)
        for m in members:
            if m.user_id != current_user.id:
                ns.notify(m.user_id, "Role updated", f"{current_user.name} changed {target.name if target else member_user_id}'s role from {old_role} to {new_role}.", type="info", group_id=group_id)
        return result

    def list_members(self, group_id: int, current_user: User):
        if not self.memberships.get(current_user.id, group_id):
            raise HTTPException(status_code=403, detail="Not a member of this group")
        return self.memberships.get_by_group(group_id)

    def delete(self, group_id: int, user: User, reason: str = None):
        self._require_lead(user.id, group_id)
        if not reason or len(reason.strip()) < 10:
            raise HTTPException(status_code=400, detail="Reason is required and must be at least 10 characters")
        group = self.groups.get_by_id(group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        self._log_activity(group_id, user, "GROUP_DELETED", reason)
        try:
            self.groups.delete(group)
            self.db.commit()
        except Exception:
            self.db.delete(group)
            self.db.commit()

    def invite_member(self, group_id: int, email: str, current_user: User, first_name: str = None, last_name: str = None, role: str = None, reason: str = None):
        self._require_lead(current_user.id, group_id)
        existing_user = self.users.get_by_email(email)
        if existing_user:
            if self.memberships.get(existing_user.id, group_id):
                raise HTTPException(status_code=400, detail="Already a member of this group")
            self.memberships.create(Membership(user_id=existing_user.id, group_id=group_id, role='member'))
            return {"message": "Member added successfully"}
        name = " ".join(filter(None, [first_name, last_name])) if (first_name or last_name) else email.split("@")[0]
        activation_token = generate_verification_code()
        user = User(
            name=name,
            email=email,
            hashed_password=hash_password(generate_secure_token()),  # random password, will be set on activation if needed
            skills=None,
            is_verified=True,
            is_active=False,
            activation_token=activation_token,
            activation_expires_at=datetime.utcnow() + timedelta(minutes=15),
        )
        user = self.users.create(user)
        self.db.commit()
        self.db.refresh(user)
        self.memberships.create(Membership(user_id=user.id, group_id=group_id, role='member'))
        auth_service = AuthService(self.db)
        auth_service._send_activation_email(user, activation_token)
        return {"message": "Invitation email sent successfully"}
