from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from tracker.core.config import settings
from tracker.models.user import User
from tracker.repositories.user_repository import UserRepository
from tracker.schemas.user import UserCreate, ProfileUpdate
from tracker.services.email_service import send_email
from tracker.services.security import (
    hash_password,
    verify_password,
    create_password_reset_token,
    decode_password_reset_token,
    password_fingerprint,
)

class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)

    def register(self, data: UserCreate) -> User:
        if self.repo.get_by_email(data.email):
            raise HTTPException(status_code=400, detail="Email already registered")
        user = User(
            name=data.name,
            email=data.email,
            hashed_password=hash_password(data.password),
            skills=data.skills,
        )
        return self.repo.create(user)

    def authenticate(self, email: str, password: str) -> User:
        user = self.repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Incorrect email or password")
        return user
    def update_profile(self, user: User, data: ProfileUpdate) -> User:
        changes = {}
        if data.name is not None:
            changes["name"] = data.name
        if data.skills is not None:
            changes["skills"] = data.skills
        if data.email is not None and data.email != user.email:
            if self.repo.get_by_email(data.email):
                raise HTTPException(status_code=400, detail="That email is already used by another account")
            changes["email"] = data.email
        if data.password:
            changes["hashed_password"] = hash_password(data.password)
        return self.repo.update(user, changes)

    def request_password_reset(self, email: str) -> None:
        user = self.repo.get_by_email(email)
        if not user:
            return
        token = create_password_reset_token(user.id, user.hashed_password)
        link = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/reset-password?token={token}"
        body = (
            f"Hi {user.name},\n\n"
            f"Use this link to choose a new {settings.APP_NAME} password. "
            f"It works for {settings.RESET_TOKEN_EXPIRE_MINUTES} minutes and only once:\n\n"
            f"{link}\n\n"
            "If you did not ask for this, you can ignore this email. Your password stays the same."
        )
        try:
            send_email(user.email, f"Reset your {settings.APP_NAME} password", body)
        except Exception as exc:
            print(f"Could not send the reset email to {user.email}: {exc}", flush=True)

    def reset_password(self, token: str, new_password: str) -> None:
        invalid = HTTPException(
            status_code=400,
            detail="This reset link is invalid or has expired. Please request a new one.",
        )
        payload = decode_password_reset_token(token)
        if payload is None:
            raise invalid
        user = self.repo.get_by_id(int(payload["uid"]))
        if user is None or payload.get("fp") != password_fingerprint(user.hashed_password):
            raise invalid
        self.repo.update(user, {"hashed_password": hash_password(new_password)})
