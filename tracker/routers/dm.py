from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from datetime import datetime, timezone
from sqlalchemy import or_
from typing import Optional
import uuid
from pathlib import Path

from database import get_db
from dependency import get_current_user
from tracker.models.user import User
from tracker.models.dm import DirectConversation, DirectMessage
from tracker.models.membership import Membership

router = APIRouter(prefix="/dm", tags=["dm"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

def _iso(dt):
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

def _save_upload(file: UploadFile, subdir: str) -> str:
    ext = Path(file.filename).suffix if file.filename else ""
    unique = f"{uuid.uuid4().hex}{ext}"
    target = UPLOAD_DIR / subdir / unique
    target.parent.mkdir(parents=True, exist_ok=True)
    content = file.file.read()
    target.write_bytes(content)
    return f"/uploads/{subdir}/{unique}"

@router.get("/contacts")
def dm_contacts(q: str | None = None, db=Depends(get_db), me=Depends(get_current_user)):
    my_group_ids = db.query(Membership.group_id).filter(Membership.user_id == me.id)

    query = (
        db.query(User)
        .join(Membership, Membership.user_id == User.id)
        .filter(Membership.group_id.in_(my_group_ids), User.id != me.id)
        .distinct()
    )

    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                User.name.ilike(like),
                User.email.ilike(like),
            )
        )

    rows = query.order_by(User.name).all()
    return [{"id": u.id, "name": u.name, "email": u.email, "avatar_url": getattr(u, "avatar_url", None), "is_active": getattr(u, "is_active", True)} for u in rows]


class OpenDm(BaseModel):
    user_id: int

class SendDm(BaseModel):
    body: str

class EditDm(BaseModel):
    body: str

def get_convo_or_404(db, convo_id: int, me):
    convo = db.get(DirectConversation, convo_id)
    if not convo or me.id not in (convo.user_low_id, convo.user_high_id):
        raise HTTPException(404, "Conversation not found")
    return convo

@router.post("/open")
def open_dm(payload: OpenDm, db=Depends(get_db), me=Depends(get_current_user)):
    if not db.get(User, payload.user_id):
        raise HTTPException(404, "User not found")
    low, high = sorted([me.id, payload.user_id])
    convo = db.query(DirectConversation).filter_by(user_low_id=low, user_high_id=high).first()
    if not convo:
        convo = DirectConversation(user_low_id=low, user_high_id=high)
        db.add(convo); db.commit(); db.refresh(convo)
    return {"conversation_id": convo.id}

@router.get("/{convo_id}/messages")
def list_messages(convo_id: int, after_id: int = 0, db=Depends(get_db), me=Depends(get_current_user)):
    get_convo_or_404(db, convo_id, me)
    rows = (db.query(DirectMessage)
              .filter(
                  DirectMessage.conversation_id == convo_id,
                  DirectMessage.id > after_id,
                  DirectMessage.deleted_at.is_(None),
                  or_(DirectMessage.hidden_for_user_id.is_(None), DirectMessage.hidden_for_user_id != me.id),
              )
              .order_by(DirectMessage.id).limit(200).all())
    return [{
        "id": m.id,
        "sender_id": m.sender_id,
        "body": m.body,
        "image_url": m.image_url,
        "audio_url": m.audio_url,
        "created_at": _iso(m.created_at) or datetime.now(timezone.utc).isoformat(),
        "edited_at": _iso(m.edited_at),
        "read_at": _iso(m.read_at),
    } for m in rows]

@router.post("/{convo_id}/messages")
async def send_message(
    convo_id: int,
    body: str = Form(""),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
    db=Depends(get_db),
    me=Depends(get_current_user)
):
    get_convo_or_404(db, convo_id, me)
    text = body.strip()
    if not text and not image and not audio:
        raise HTTPException(400, "Invalid message")
    
    image_url = None
    audio_url = None
    
    if image and image.content_type and image.content_type.startswith("image/"):
        image_url = _save_upload(image, "images")
    
    if audio and audio.content_type and audio.content_type.startswith("audio/"):
        audio_url = _save_upload(audio, "audio")
    
    msg = DirectMessage(
        conversation_id=convo_id,
        sender_id=me.id,
        body=text,
        image_url=image_url,
        audio_url=audio_url
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {
        "id": msg.id,
        "sender_id": msg.sender_id,
        "body": msg.body,
        "image_url": msg.image_url,
        "audio_url": msg.audio_url,
        "created_at": _iso(msg.created_at) or datetime.now(timezone.utc).isoformat(),
        "edited_at": _iso(msg.edited_at),
        "deleted_at": _iso(msg.deleted_at),
        "read_at": _iso(msg.read_at),
    }

@router.get("/unread-count")
def unread_count(db=Depends(get_db), me=Depends(get_current_user)):
    convos = db.query(DirectConversation).filter(or_(DirectConversation.user_low_id == me.id, DirectConversation.user_high_id == me.id)).all()
    total = 0
    for c in convos:
        total += db.query(DirectMessage).filter(DirectMessage.conversation_id == c.id, DirectMessage.sender_id != me.id, DirectMessage.read_at == None).count()
    return {"count": total}

@router.get("")
def inbox(db=Depends(get_db), me=Depends(get_current_user)):
    self_convo = db.query(DirectConversation).filter_by(user_low_id=me.id, user_high_id=me.id).first()
    if not self_convo:
        self_convo = DirectConversation(user_low_id=me.id, user_high_id=me.id)
        db.add(self_convo); db.commit(); db.refresh(self_convo)
    convos = db.query(DirectConversation).filter(or_(DirectConversation.user_low_id == me.id, DirectConversation.user_high_id == me.id)).all()
    out = []
    for c in convos:
        is_self = c.user_low_id == c.user_high_id
        if is_self:
            other = me
        else:
            other_id = c.user_high_id if c.user_low_id == me.id else c.user_low_id
            other = db.get(User, other_id)
        last = db.query(DirectMessage).filter(DirectMessage.conversation_id == c.id).order_by(DirectMessage.id.desc()).first()
        unread = db.query(DirectMessage).filter(DirectMessage.conversation_id == c.id, DirectMessage.sender_id != me.id, DirectMessage.read_at == None).count()
        out.append({
            "id": c.id,
            "other": {"id": other.id, "name": other.name, "avatar_url": getattr(other, "avatar_url", None), "is_active": getattr(other, "is_active", True)},
            "last_message": last.body if last else None,
            "last_at": last.created_at.isoformat() if last else None,
            "unread": unread,
            "is_self": is_self,
        })
    out.sort(key=lambda x: (not x["is_self"], -(datetime.fromisoformat(x["last_at"]).timestamp() if x["last_at"] else 0)))
    return out

@router.get("/{convo_id}")
def get_convo(convo_id: int, db=Depends(get_db), me=Depends(get_current_user)):
    c = get_convo_or_404(db, convo_id, me)
    other_id = c.user_high_id if c.user_low_id == me.id else c.user_low_id
    other = db.get(User, other_id)
    return {"id": c.id, "other": {"id": other.id, "name": other.name, "avatar_url": getattr(other, "avatar_url", None), "is_active": getattr(other, "is_active", True)}, "is_self": c.user_low_id == c.user_high_id}

@router.post("/{convo_id}/read")
def mark_read(convo_id: int, db=Depends(get_db), me=Depends(get_current_user)):
    get_convo_or_404(db, convo_id, me)
    db.query(DirectMessage).filter(DirectMessage.conversation_id == convo_id, DirectMessage.sender_id != me.id, DirectMessage.read_at == None).update({"read_at": datetime.utcnow()})
    db.commit()
    return {"ok": True}

@router.post("/{convo_id}/clear")
def clear_chat(convo_id: int, db=Depends(get_db), me=Depends(get_current_user)):
    get_convo_or_404(db, convo_id, me)
    db.query(DirectMessage).filter(DirectMessage.conversation_id == convo_id).delete()
    db.commit()
    return {"ok": True}

@router.delete("/{convo_id}")
def delete_chat(convo_id: int, everyone: bool = False, db=Depends(get_db), me=Depends(get_current_user)):
    c = get_convo_or_404(db, convo_id, me)
    db.query(DirectMessage).filter(DirectMessage.conversation_id == convo_id).delete()
    db.delete(c)
    db.commit()
    return {"ok": True}

@router.delete("/{convo_id}/messages/{message_id}")
def delete_message(convo_id: int, message_id: int, scope: str = "everyone", db=Depends(get_db), me=Depends(get_current_user)):
    get_convo_or_404(db, convo_id, me)
    m = db.get(DirectMessage, message_id)
    if not m or m.conversation_id != convo_id or m.sender_id != me.id:
        raise HTTPException(404, "Message not found")
    if m.deleted_at or m.hidden_for_user_id == me.id:
        raise HTTPException(400, "Already deleted")
    if scope == "me":
        m.hidden_for_user_id = me.id
        db.commit()
        return {"ok": True}
    replied = db.query(DirectMessage).filter(DirectMessage.conversation_id == convo_id, DirectMessage.sender_id != me.id, DirectMessage.id > m.id).first()
    if replied:
        raise HTTPException(409, "Can't delete after someone replied")
    m.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}

@router.patch("/{convo_id}/messages/{message_id}")
def edit_message(convo_id: int, message_id: int, payload: EditDm, db=Depends(get_db), me=Depends(get_current_user)):
    get_convo_or_404(db, convo_id, me)
    body = payload.body.strip()
    if not body:
        raise HTTPException(400, "Message cannot be empty")
    msg = db.get(DirectMessage, message_id)
    if not msg or msg.conversation_id != convo_id:
        raise HTTPException(404, "Message not found")
    if msg.sender_id != me.id:
        raise HTTPException(403, "You can only edit your own messages")
    if msg.deleted_at:
        raise HTTPException(400, "Message was deleted")
    age = (datetime.now(timezone.utc) - (msg.created_at.replace(tzinfo=timezone.utc) if msg.created_at.tzinfo is None else msg.created_at)).total_seconds()
    if age > 24 * 3600:
        raise HTTPException(403, "Edit window (24h) expired")
    msg.body = body
    msg.edited_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(msg)
    return {"id": msg.id, "sender_id": msg.sender_id, "body": msg.body, "created_at": _iso(msg.created_at), "edited_at": _iso(msg.edited_at), "deleted_at": _iso(msg.deleted_at)}

from sqlalchemy import or_ as _or
