from fastapi import APIRouter, Depends, HTTPException
from fastapi import UploadFile, File
from sqlalchemy.orm import Session
import os, uuid, io, sys
try:
    sys.path.insert(0, '/usr/lib/python3/dist-packages')
    from PIL import Image
except Exception:
    Image = None

from database import get_db
from dependency import get_current_user
from tracker.models.user import User
from tracker.schemas.user import UserOut, ProfileUpdate
from tracker.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = UserService(db)
    return service.get_user(user_id)


@router.patch("/me", response_model=UserOut)
def update_profile(
    updates: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return UserService(db).update_profile(current_user, updates)

from fastapi import UploadFile, File
import os, uuid, io
try:
    from PIL import Image
except Exception:
    Image = None


@router.put("/me/avatar")
async def upload_avatar(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    content_type = file.content_type
    if content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Only JPEG, PNG and WebP allowed")
    data = await file.read()
    if len(data) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 2MB)")
    try:
        import base64, io
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        img = img.convert("RGB")
        img = img.resize((256, 256))
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=85)
        b64 = base64.b64encode(out.getvalue()).decode("ascii")
        url = f"data:image/jpeg;base64,{b64}"
        current_user.avatar_url = url
        db.commit()
        db.refresh(current_user)
        return {"avatar_url": url}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail="Invalid image")


@router.put("/me/skills")
def update_skills(data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if "job_title" in data:
        current_user.job_title = data.get("job_title") or None
    if "skills" in data and isinstance(data["skills"], list):
        from tracker.models.user_skill import UserSkill
        db.query(UserSkill).filter(UserSkill.user_id == current_user.id).delete()
        for s in data["skills"]:
            if not s:
                continue
            key = str(s).strip().lower()[:40]
            if not key:
                continue
            db.add(UserSkill(user_id=current_user.id, name=str(s).strip()[:40], key=key))
        current_user.skills = ",".join([str(s).strip()[:40] for s in data["skills"] if s])
    db.commit()
    db.refresh(current_user)
    return {"ok": True, "job_title": current_user.job_title, "skills": data.get("skills", [])}


@router.patch("/me/password")
def change_password(data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_password = data.get("current_password")
    password = data.get("password") or data.get("new_password")
    from tracker.services.security import verify_password, hash_password
    if not current_password or not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if not password or len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    current_user.hashed_password = hash_password(password)
    db.commit()
    db.refresh(current_user)
    return {"ok": True}
