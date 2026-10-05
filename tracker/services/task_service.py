from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session

from tracker.models.user import User
from tracker.models.task import Task, TaskStatus, TaskReassignment
from tracker.models.membership import MembershipRole
from tracker.repositories.task_repository import TaskRepository
from tracker.repositories.user_repository import UserRepository
from tracker.repositories.membership_repository import MembershipRepository
from tracker.repositories.group_repository import GroupRepository
from tracker.schemas.task import TaskCreate, TaskUpdate, TaskReassign


class TaskService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = TaskRepository(db)
        self.users = UserRepository(db)
        self.memberships = MembershipRepository(db)
        self.groups = GroupRepository(db)

    def _is_lead_of(self, user_id: int, group_id: int) -> bool:
        m = self.memberships.get(user_id, group_id)
        return bool(m and m.role == MembershipRole.lead)

    def create(self, data: TaskCreate, creator: User) -> Task:
        assignee = self.users.get_by_id(data.assignee_id)
        if not assignee:
            raise HTTPException(status_code=404, detail="Assignee not found")

        if data.group_id:
            # only a lead of the group can assign a group task
            if not self._is_lead_of(creator.id, data.group_id):
                raise HTTPException(status_code=403, detail="Only a lead of this group can assign tasks in it")
            group = self.groups.get_by_id(data.group_id)
            if group and group.is_archived:
                raise HTTPException(status_code=400, detail="This group is stopped - no new work can be assigned")
        elif data.assignee_id != creator.id:
            raise HTTPException(status_code=403, detail="You can only create personal tasks for yourself")

        task = Task(
            title=data.title,
            description=data.description,
            assignee_id=data.assignee_id,
            assigned_by_id=creator.id,
            group_id=data.group_id,
            priority=data.priority,
            estimated_hours=data.estimated_hours,
            deadline=data.deadline,
            is_management_duty=data.is_management_duty,
            period_type=data.period_type,
        )
        return self.repo.create(task)

    def list_for_user(self, current_user: User, group_id=None, status=None):
        """
        - No group_id: return the user's own active (non-archived) tasks, personal + group.
        - group_id given + user leads that group: return the whole group's tasks.
        - group_id given + user is just a member: return only their own tasks in that group.
        """
        if group_id and self._is_lead_of(current_user.id, group_id):
            return self.repo.list(group_id=group_id, status=status, is_archived=False)
        return self.repo.list(assignee_id=current_user.id, group_id=group_id, status=status, is_archived=False)

    def list_my_past_plans(self, current_user: User):
        """A person's own archived personal plans - never group tasks, those are archived via the group instead."""
        return self.repo.list(assignee_id=current_user.id, is_archived=True, personal_only=True)

    def get(self, task_id: int, current_user: User) -> Task:
        task = self.repo.get_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        is_owner = task.assignee_id == current_user.id
        is_lead = task.group_id and self._is_lead_of(current_user.id, task.group_id)
        if not (is_owner or is_lead):
            raise HTTPException(status_code=403, detail="Not your task")
        return task

    def update(self, task_id: int, updates: TaskUpdate, current_user: User) -> Task:
        task = self.repo.get_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        is_owner = task.assignee_id == current_user.id
        is_lead = task.group_id and self._is_lead_of(current_user.id, task.group_id)
        if not (is_owner or is_lead):
            raise HTTPException(status_code=403, detail="Not allowed to edit this task")

        data = updates.model_dump(exclude_unset=True)
        task = self.repo.update(task, data)

        if updates.status == TaskStatus.done and task.completed_at is None:
            task = self.repo.update(task, {
                "completed_at": datetime.utcnow(),
                "percent_complete": 100,
            })
        elif updates.status is not None and updates.status != TaskStatus.done and task.completed_at is not None:
                task = self.repo.update(task, {
                "completed_at": None,
                "percent_complete": 0,
                "is_archived": False,
            })
        return task

    def reassign(self, task_id: int, data: TaskReassign, current_user: User) -> Task:
        task = self.repo.get_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if not task.group_id or not self._is_lead_of(current_user.id, task.group_id):
            raise HTTPException(status_code=403, detail="Only the group's lead can reassign work")

        new_assignee = self.users.get_by_id(data.new_assignee_id)
        if not new_assignee:
            raise HTTPException(status_code=404, detail="New assignee not found")
        if not self.memberships.get(new_assignee.id, task.group_id):
            raise HTTPException(status_code=400, detail="New assignee isn't a member of this group")

        old_assignee_id = task.assignee_id
        self.repo.create_reassignment(TaskReassignment(
            task_id=task.id,
            from_user_id=old_assignee_id,
            to_user_id=new_assignee.id,
            reassigned_by=current_user.id,
            reason=data.reason,
        ))
        changes = {"assignee_id": new_assignee.id}
        if task.status == TaskStatus.done:
            changes.update({
                "status": TaskStatus.todo,
                "completed_at": None,
                "percent_complete": 0,
                "is_archived": False,
            })
        return self.repo.update(task, changes)

    def delete(self, task_id: int, current_user: User) -> None:
        task = self.repo.get_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.status == TaskStatus.done:
            raise HTTPException(status_code=400, detail="Completed work can't be deleted - it's kept as history")
        is_owner = task.assignee_id == current_user.id
        is_lead = task.group_id and self._is_lead_of(current_user.id, task.group_id)
        if not (is_owner or is_lead):
            raise HTTPException(status_code=403, detail="Not allowed to delete this task")
        self.repo.delete(task)

    def archive(self, task_id: int, current_user: User, archived: bool = True) -> Task:
        """Move a personal plan to/from Past Plans. Only the task's own owner can do this,
        and only for personal (non-group) tasks - group tasks archive via the group itself."""
        task = self.repo.get_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.assignee_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only the owner of this plan can do that")
        if task.group_id:
            raise HTTPException(status_code=400, detail="Group tasks are archived by stopping the group, not individually")
        return self.repo.update(task, {"is_archived": archived})
    def list_completed(self, current_user: User, group_id=None):
        """Finished work. A lead sees the whole group's; everyone else sees only their own."""
        if group_id and self._is_lead_of(current_user.id, group_id):
            tasks = self.repo.list(group_id=group_id, status=TaskStatus.done)
        elif group_id:
            tasks = self.repo.list(assignee_id=current_user.id, group_id=group_id, status=TaskStatus.done)
        else:
            tasks = self.repo.list(assignee_id=current_user.id, status=TaskStatus.done)
        return sorted(tasks, key=lambda t: t.completed_at or t.created_at, reverse=True)