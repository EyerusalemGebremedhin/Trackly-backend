from datetime import datetime, timezone, timedelta
from typing import Optional
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from database import get_db
from dependency import get_current_user
from tracker.models.user import User
from tracker.models.group_message import GroupMessage
from tracker.models.membership import Membership


class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


router = APIRouter()


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def _save_upload(file: UploadFile, subdir: str) -> str:
    ext = Path(file.filename).suffix if file.filename else ""
    unique = f"{uuid.uuid4().hex}{ext}"
    target = UPLOAD_DIR / subdir / unique
    target.parent.mkdir(parents=True, exist_ok=True)
    content = file.file.read()
    target.write_bytes(content)
    return f"/uploads/{subdir}/{unique}"


def _require_member(db: Session, group_id: int, user: User):
    if not db.query(Membership).filter(Membership.group_id == group_id, Membership.user_id == user.id).first():
        raise HTTPException(403, "You are not a member of this group")


def _iso(dt):
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _out(m: GroupMessage):
    return {
        "id": m.id,
        "kind": m.kind,
        "body": m.body,
        "image_url": m.image_url,
        "audio_url": m.audio_url,
        "author_id": m.author_id,
        "author_name": m.author_name,
        "created_at": _iso(m.created_at) or datetime.now(timezone.utc).isoformat(),
        "edited_at": _iso(m.edited_at),
        "pinned": m.pinned_at is not None,
    }


@router.get("/groups/{group_id}/messages")
def list_messages(
    group_id: int,
    kind: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    before_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_member(db, group_id, user)
    q = select(GroupMessage).where(
        GroupMessage.group_id == group_id,
        GroupMessage.deleted_at.is_(None),
        or_(GroupMessage.hidden_for_user_id.is_(None), GroupMessage.hidden_for_user_id != user.id),
    )
    if kind:
        q = q.where(GroupMessage.kind == kind)
    if search:
        q = q.where(GroupMessage.body.ilike(f"%{search}%"))
    if before_id:
        q = q.where(GroupMessage.id < before_id)
    rows = db.execute(q.order_by(GroupMessage.id.desc()).limit(limit)).scalars().all()
    return [_out(m) for m in reversed(rows)]


@router.patch("/groups/{group_id}/messages/{message_id}")
def edit_message(group_id: int, message_id: int, body: MessageIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_member(db, group_id, user)
    m = db.get(GroupMessage, message_id)
    if not m or m.group_id != group_id or m.deleted_at is not None:
        raise HTTPException(404, "Message not found")
    if m.author_id != user.id:
        raise HTTPException(403, "Not allowed")
    created = m.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - created > timedelta(hours=24):
        raise HTTPException(409, "Messages can only be edited within 24 hours")
    m.body = body.body.strip()
    m.edited_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(m)
    return _out(m)


@router.delete("/groups/{group_id}/messages/{message_id}", status_code=204)
def delete_message(group_id: int, message_id: int, scope: str = Query("everyone"), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_member(db, group_id, user)
    m = db.get(GroupMessage, message_id)
    if not m or m.group_id != group_id or m.deleted_at is not None:
        raise HTTPException(404, "Message not found")
    mem = db.query(Membership).filter(Membership.group_id == group_id, Membership.user_id == user.id).first()
    is_admin = bool(mem and getattr(mem, "role", "member") == "admin")
    if m.author_id != user.id and not is_admin:
        raise HTTPException(403, "Not allowed")
    if scope == "me":
        m.hidden_for_user_id = user.id
        db.commit()
        return
    if m.author_id == user.id:
        replied = db.query(GroupMessage).filter(GroupMessage.group_id == group_id, GroupMessage.author_id != user.id, GroupMessage.id > m.id, GroupMessage.deleted_at.is_(None)).first()
        if replied:
            raise HTTPException(409, "Can't delete after someone replied")
    m.deleted_at = datetime.now(timezone.utc)
    db.commit()
@router.post("/groups/{group_id}/messages/{message_id}/pin", status_code=204)
def pin_message(group_id: int, message_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_member(db, group_id, user)
    m = db.get(GroupMessage, message_id)
    if not m or m.group_id != group_id or m.deleted_at is not None:
        raise HTTPException(404, "Message not found")
    m.pinned_at = datetime.now(timezone.utc)
    db.commit()

@router.delete("/groups/{group_id}/messages/{message_id}/pin", status_code=204)
def unpin_message(group_id: int, message_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_member(db, group_id, user)
    m = db.get(GroupMessage, message_id)
    if not m or m.group_id != group_id or m.deleted_at is not None:
        raise HTTPException(404, "Message not found")
    m.pinned_at = None
    db.commit()

@router.post("/groups/{group_id}/messages", status_code=201)
async def post_message(
    group_id: int,
    body: str = Form(""),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_member(db, group_id, user)
    text = body.strip()
    if not text and not image and not audio:
        raise HTTPException(422, "Message is empty")
    
    image_url = None
    audio_url = None
    
    if image and image.content_type and image.content_type.startswith("image/"):
        image_url = _save_upload(image, "images")
    
    if audio and audio.content_type and audio.content_type.startswith("audio/"):
        audio_url = _save_upload(audio, "audio")
    
    m = GroupMessage(
        group_id=group_id,
        author_id=user.id,
        author_name=user.name,
        kind="message",
        body=text,
        image_url=image_url,
        audio_url=audio_url
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return _out(m)
