from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from dependency import get_current_user
from tracker.models.user import User
from tracker.schemas.help_request import HelpRequestCreate, HelpRequestOut
from tracker.services.help_request_service import HelpRequestService
from tracker.repositories.user_repository import UserRepository

router = APIRouter(prefix="/groups/{group_id}/help-requests", tags=["help-requests"])


def _to_out(request, db: Session) -> HelpRequestOut:
    requester = UserRepository(db).get_by_id(request.requested_by)
    return HelpRequestOut(
        id=request.id,
        group_id=request.group_id,
        task_id=request.task_id,
        requested_by=request.requested_by,
        requested_by_name=requester.name if requester else "Unknown",
        skill_needed=request.skill_needed,
        note=request.note,
        status=request.status,
        resolved_by=request.resolved_by,
        created_at=request.created_at,
        resolved_at=request.resolved_at,
    )


@router.post("", response_model=HelpRequestOut)
def create_help_request(
    group_id: int, data: HelpRequestCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    request = HelpRequestService(db).create(group_id, data, current_user)
    return _to_out(request, db)


@router.get("", response_model=List[HelpRequestOut])
def list_help_requests(
    group_id: int, open_only: bool = False, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    requests = HelpRequestService(db).list_for_group(group_id, current_user, open_only=open_only)
    return [_to_out(r, db) for r in requests]


@router.post("/{request_id}/resolve", response_model=HelpRequestOut)
def resolve_help_request(
    group_id: int, request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    request = HelpRequestService(db).resolve(request_id, current_user)
    return _to_out(request, db)
