from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from dependency import get_current_user
from tracker.models.user import User
from tracker.schemas.help_request import HelpRequestCreate, HelpRequestOut
from tracker.services.help_request_service import HelpRequestService

router = APIRouter(prefix="/groups/{group_id}/help-requests", tags=["help-requests"])


@router.get("", response_model=List[HelpRequestOut])
def list_help_requests(
    group_id: int,
    open_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return HelpRequestService(db).list(group_id, current_user, open_only=open_only)


@router.post("", response_model=HelpRequestOut)
def create_help_request(
    group_id: int,
    data: HelpRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return HelpRequestService(db).create(group_id, data, current_user)


@router.post("/{request_id}/resolve", response_model=HelpRequestOut)
def resolve_help_request(
    group_id: int,
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return HelpRequestService(db).resolve(group_id, request_id, current_user)
