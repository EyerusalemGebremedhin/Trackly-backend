from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from dependency import get_current_user
from tracker.models.user import User
from tracker.models.membership import MembershipRole
from tracker.schemas.group import GroupCreate, GroupUpdate, GroupOut, MemberAdd, MembershipOut, TransferLead
from tracker.services.group_service import GroupService
from tracker.repositories.user_repository import UserRepository

router = APIRouter(prefix="/groups", tags=["groups"])


def _membership_out(membership, db: Session) -> MembershipOut:
    u = UserRepository(db).get_by_id(membership.user_id)
    return MembershipOut(
        id=membership.id,
        user_id=membership.user_id,
        group_id=membership.group_id,
        role=membership.role,
        created_at=membership.created_at,
        name=u.name if u else "Unknown",
        email=u.email if u else "unknown@example.com",
        skills=u.skills if u else None,
    )


def _group_out(group, role: MembershipRole) -> GroupOut:
    return GroupOut(
        id=group.id,
        name=group.name,
        description=group.description,
        created_by=group.created_by,
        checkin_cadence=group.checkin_cadence,
        is_archived=group.is_archived,
        created_at=group.created_at,
        my_role=role,
    )


@router.post("", response_model=GroupOut)
def create_group(data: GroupCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    group = GroupService(db).create(data, current_user)
    return _group_out(group, MembershipRole.lead)


@router.get("", response_model=List[GroupOut])
def my_groups(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pairs = GroupService(db).list_for_user(current_user, archived=False)
    return [_group_out(g, role) for g, role in pairs]


@router.get("/past", response_model=List[GroupOut])
def my_past_groups(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pairs = GroupService(db).list_for_user(current_user, archived=True)
    return [_group_out(g, role) for g, role in pairs]


@router.get("/{group_id}", response_model=GroupOut)
def get_group(group_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = GroupService(db)
    group = service.get(group_id, current_user)
    role = service.get_my_role(group_id, current_user.id)
    return _group_out(group, role)


@router.patch("/{group_id}", response_model=GroupOut)
def update_group(group_id: int, data: GroupUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = GroupService(db)
    group = service.update(group_id, data, current_user)
    role = service.get_my_role(group_id, current_user.id)
    return _group_out(group, role)


@router.post("/{group_id}/archive", response_model=GroupOut)
def archive_group(group_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = GroupService(db)
    group = service.archive(group_id, current_user, archived=True)
    role = service.get_my_role(group_id, current_user.id)
    return _group_out(group, role)


@router.post("/{group_id}/unarchive", response_model=GroupOut)
def unarchive_group(group_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = GroupService(db)
    group = service.archive(group_id, current_user, archived=False)
    role = service.get_my_role(group_id, current_user.id)
    return _group_out(group, role)


@router.get("/{group_id}/members", response_model=List[MembershipOut])
def list_members(group_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    members = GroupService(db).list_members(group_id, current_user)
    return [_membership_out(m, db) for m in members]


@router.post("/{group_id}/members", response_model=MembershipOut)
def add_member(group_id: int, data: MemberAdd, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    membership = GroupService(db).add_member(group_id, data, current_user)
    return _membership_out(membership, db)


@router.delete("/{group_id}/members/{member_user_id}", status_code=204)
def remove_member(group_id: int, member_user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    GroupService(db).remove_member(group_id, member_user_id, current_user)


@router.post("/{group_id}/transfer-lead", response_model=MembershipOut)
def transfer_lead(group_id: int, data: TransferLead, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    membership = GroupService(db).transfer_lead(group_id, data.new_lead_user_id, current_user)
    return _membership_out(membership, db)