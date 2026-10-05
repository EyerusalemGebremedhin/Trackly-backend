from typing import List, Optional
from sqlalchemy.orm import Session

from tracker.models.group import Group


class GroupRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, group: Group) -> Group:
        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)
        return group

    def get_by_id(self, group_id: int) -> Optional[Group]:
        return self.db.query(Group).filter(Group.id == group_id).first()

    def get_all(self) -> List[Group]:
        return self.db.query(Group).all()

    def update(self, group: Group, data: dict) -> Group:
        for field, value in data.items():
            setattr(group, field, value)
        self.db.commit()
        self.db.refresh(group)
        return group

    def list_by_ids(self, ids: List[int], archived: Optional[bool] = None) -> List[Group]:
        query = self.db.query(Group).filter(Group.id.in_(ids))
        if archived is not None:
            query = query.filter(Group.is_archived == archived)
        return query.all()
