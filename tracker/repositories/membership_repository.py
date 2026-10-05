from typing import List, Optional
from sqlalchemy.orm import Session

from tracker.models.membership import Membership


class MembershipRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, membership: Membership) -> Membership:
        self.db.add(membership)
        self.db.commit()
        self.db.refresh(membership)
        return membership

    def get(self, user_id: int, group_id: int) -> Optional[Membership]:
        return (
            self.db.query(Membership)
            .filter(Membership.user_id == user_id, Membership.group_id == group_id)
            .first()
        )

    def get_by_group(self, group_id: int) -> List[Membership]:
        return self.db.query(Membership).filter(Membership.group_id == group_id).all()

    def get_by_user(self, user_id: int) -> List[Membership]:
        return self.db.query(Membership).filter(Membership.user_id == user_id).all()

    def delete(self, membership: Membership) -> None:
        self.db.delete(membership)
        self.db.commit()

    def update_role(self, membership: Membership, role) -> Membership:
        membership.role = role
        self.db.commit()
        self.db.refresh(membership)
        return membership
