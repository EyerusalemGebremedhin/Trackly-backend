from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db
from dependency import get_current_user
from tracker.models.user import User
from tracker.schemas.user import (
    UserCreate, UserOut, Token, ForgotPassword, ResetPassword,
    VerifyEmail, ResendVerification, ActivateAccount, TeamRegisterUser
)
from tracker.services.user_service import UserService
from tracker.services.auth_service import AuthService
from tracker.services.security import create_access_token, create_refresh_token, decode_refresh_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut)
def register(data: UserCreate, db: Session = Depends(get_db)):
    return AuthService(db).register(data)


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = AuthService(db).authenticate(form_data.username, form_data.password)
    access = create_access_token({"sub": str(user.id)})
    refresh = create_refresh_token({"sub": str(user.id)})
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


@router.post("/verify-email")
def verify_email(data: VerifyEmail, db: Session = Depends(get_db)):
    AuthService(db).verify_email(data.email, data.code)
    user = AuthService(db).repo.get_by_email(data.email)
    access = create_access_token({"sub": str(user.id)})
    refresh = create_refresh_token({"sub": str(user.id)})
    return {"message": "MFA verification successful", "verified": True, "access_token": access, "refresh_token": refresh, "token_type": "bearer"}


@router.post("/refresh", response_model=Token)
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    payload = decode_refresh_token(refresh_token)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    access = create_access_token({"sub": payload["sub"]})
    new_refresh = create_refresh_token({"sub": payload["sub"]})
    return {"access_token": access, "refresh_token": new_refresh, "token_type": "bearer"}


@router.post("/resend-verification")
def resend_verification(data: ResendVerification, db: Session = Depends(get_db)):
    return AuthService(db).resend_verification(data.email)


@router.post("/activate")
def activate(data: ActivateAccount, db: Session = Depends(get_db)):
    return AuthService(db).activate_account(data.token)


@router.post("/team/register", response_model=UserOut)
def team_register_user(
    data: TeamRegisterUser,
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return AuthService(db).create_team_user(current_user, group_id, data)


@router.post("/forgot-password")
def forgot_password(data: ForgotPassword, db: Session = Depends(get_db)):
    UserService(db).request_password_reset(data.email)
    return {"message": "If that email is registered, a reset link is on its way."}


@router.post("/reset-password")
def reset_password(data: ResetPassword, db: Session = Depends(get_db)):
    UserService(db).reset_password(data.token, data.new_password)
    return {"message": "Your password has been updated. You can log in now."}
