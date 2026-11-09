from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from tracker.models.user import User
from tracker.services.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

_last_seen_touch: dict[int, datetime] = {}

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None or payload.get("sub") is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if user is None:
        raise credentials_exception
    now = datetime.now(timezone.utc)
    prev = _last_seen_touch.get(user.id)
    if prev is None or (now - prev).total_seconds() > 60:
        try:
            user.last_seen_at = now
            db.add(user)
            db.commit()
            _last_seen_touch[user.id] = now
        except Exception:
            db.rollback()
    return user
