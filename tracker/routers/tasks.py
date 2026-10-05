from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from dependency import get_current_user
from tracker.models.user import User
from tracker.models.task import TaskStatus
from tracker.schemas.task import TaskCreate, TaskUpdate, TaskOut, TaskReassign
from tracker.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskOut)
def create_task(data: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return TaskService(db).create(data, current_user)


@router.get("", response_model=List[TaskOut])
def list_tasks(
    group_id: Optional[int] = None,
    status_filter: Optional[TaskStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return TaskService(db).list_for_user(current_user, group_id=group_id, status=status_filter)


@router.get("/past", response_model=List[TaskOut])
def my_past_plans(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return TaskService(db).list_my_past_plans(current_user)
@router.get("/completed", response_model=List[TaskOut])
def completed_work(
    group_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return TaskService(db).list_completed(current_user, group_id=group_id)

@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return TaskService(db).get(task_id, current_user)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int, updates: TaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return TaskService(db).update(task_id, updates, current_user)


@router.post("/{task_id}/archive", response_model=TaskOut)
def archive_plan(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return TaskService(db).archive(task_id, current_user, archived=True)


@router.post("/{task_id}/unarchive", response_model=TaskOut)
def unarchive_plan(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return TaskService(db).archive(task_id, current_user, archived=False)


@router.post("/{task_id}/reassign", response_model=TaskOut)
def reassign_task(
    task_id: int, data: TaskReassign, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return TaskService(db).reassign(task_id, data, current_user)


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    TaskService(db).delete(task_id, current_user)
    return {"ok": True}