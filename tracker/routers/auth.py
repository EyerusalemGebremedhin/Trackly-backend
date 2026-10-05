from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db
from dependency import get_current_user
from tracker.models.user import User
from tracker.schemas.user import UserCreate, UserOut, Token, ForgotPassword, ResetPassword
from tracker.services.user_service import UserService
from tracker.services.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut)
def register(data: UserCreate, db: Session = Depends(get_db)):
    return UserService(db).register(data)


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = UserService(db).authenticate(form_data.username, form_data.password)
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}
@router.post("/forgot-password")
def forgot_password(data: ForgotPassword, db: Session = Depends(get_db)):
    UserService(db).request_password_reset(data.email)
    return {"message": "If that email is registered, a reset link is on its way."}


@router.post("/reset-password")
def reset_password(data: ResetPassword, db: Session = Depends(get_db)):
    UserService(db).reset_password(data.token, data.new_password)
    return {"message": "Your password has been updated. You can log in now."}