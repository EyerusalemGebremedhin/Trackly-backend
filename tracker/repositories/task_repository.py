from typing import List, Optional
from sqlalchemy.orm import Session

from tracker.models.task import Task, TaskStatus, TaskReassignment


class TaskRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, task: Task) -> Task:
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_by_id(self, task_id: int) -> Optional[Task]:
        return self.db.query(Task).filter(Task.id == task_id).first()

    def list(
        self,
        assignee_id: Optional[int] = None,
        group_id: Optional[int] = None,
        status: Optional[TaskStatus] = None,
        is_archived: Optional[bool] = None,
        personal_only: bool = False,
    ) -> List[Task]:
        query = self.db.query(Task)
        if assignee_id is not None:
            query = query.filter(Task.assignee_id == assignee_id)
        if group_id is not None:
            query = query.filter(Task.group_id == group_id)
        if status is not None:
            query = query.filter(Task.status == status)
        if is_archived is not None:
            query = query.filter(Task.is_archived == is_archived)
        if personal_only:
            query = query.filter(Task.group_id.is_(None))
        return query.order_by(Task.deadline.asc().nullslast()).all()

    def update(self, task: Task, data: dict) -> Task:
        for field, value in data.items():
            setattr(task, field, value)
        self.db.commit()
        self.db.refresh(task)
        return task

    def delete(self, task: Task) -> None:
        self.db.delete(task)
        self.db.commit()

    def create_reassignment(self, reassignment: TaskReassignment) -> TaskReassignment:
        self.db.add(reassignment)
        self.db.commit()
        self.db.refresh(reassignment)
        return reassignment

    def get_reassignments(self, task_id: int) -> List[TaskReassignment]:
        return (
            self.db.query(TaskReassignment)
            .filter(TaskReassignment.task_id == task_id)
            .order_by(TaskReassignment.created_at.asc())
            .all()
        )