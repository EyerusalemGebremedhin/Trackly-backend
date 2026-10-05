from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from tracker.models.help_request import HelpRequest, HelpRequestStatus


class HelpRequestRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, request: HelpRequest) -> HelpRequest:
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        return request

    def get_by_id(self, request_id: int) -> Optional[HelpRequest]:
        return self.db.query(HelpRequest).filter(HelpRequest.id == request_id).first()

    def list_for_group(self, group_id: int, status: Optional[HelpRequestStatus] = None) -> List[HelpRequest]:
        query = self.db.query(HelpRequest).filter(HelpRequest.group_id == group_id)
        if status is not None:
            query = query.filter(HelpRequest.status == status)
        return query.order_by(HelpRequest.created_at.desc()).all()

    def resolve(self, request: HelpRequest, resolved_by: int) -> HelpRequest:
        request.status = HelpRequestStatus.resolved
        request.resolved_by = resolved_by
        request.resolved_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(request)
        return request
