from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from tracker.core.config import settings
from tracker.models.user import User
from tracker.repositories.user_repository import UserRepository
from tracker.schemas.user import UserCreate, TeamRegisterUser
from tracker.services.email_service import send_email
from tracker.services.security import (
    hash_password,
    verify_password,
    generate_verification_code,
    create_verification_token,
    decode_verification_token,
    create_activation_token,
    decode_activation_token,
    generate_secure_token,
)


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)

    def register(self, data: UserCreate) -> User:
        if self.repo.get_by_email(data.email):
            raise HTTPException(status_code=400, detail="Email already registered")
        code = generate_verification_code()
        user = User(
            name=data.name,
            email=data.email,
            hashed_password=hash_password(data.password),
            skills=data.skills,
            is_verified=False,
            is_active=True,
            verification_code=code,
            verification_expires_at=datetime.utcnow() + timedelta(minutes=15),
            mfa_enabled=True,
        )
        user = self.repo.create(user)
        self._send_verification_email(user, code)
        return user

    def _send_verification_email(self, user: User, code: str) -> None:
        verify_link = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/verify-email?email={user.email}&code={code}"
        body = (
            f"Hi {user.name},\n\n"
            f"Thank you for signing up to Trackly. To complete your registration, please verify your email address.\n\n"
            f"Your verification code is: {code}\n\n"
            f"Click here to verify: {verify_link}\n\n"
            f"\"Start where you are. Use what you have. Do what you can.\"\n\n"
            f"This code expires in 15 minutes.\n\n"
            f"Trackly"
        )
        html_body = f"""
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
          </head>
          <body style="margin: 0; padding: 0; background-color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #ffffff;">
              <tr>
                <td align="center">
                  <table role="presentation" width="600" cellspacing="0" cellpadding="0">
                    <tr>
                      <td style="background-color: #3C050F; padding: 25px 40px; text-align: center;">
                        <h1 style="color: #ffffff; margin: 0; font-size: 26px; font-weight: 700;">Trackly</h1>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding: 40px 40px;">
                        <h2 style="color: #111827; margin: 0 0 16px 0; font-size: 22px; font-weight: 600;">Complete Your Registration</h2>
                        <p style="color: #374151; margin: 0 0 20px 0; font-size: 15px; line-height: 24px;">Hi {user.name},</p>
                        <p style="color: #374151; margin: 0 0 28px 0; font-size: 15px; line-height: 24px;">Thank you for signing up to Trackly. Please verify your email address to activate your account.</p>
                        <p style="color: #374151; margin: 0 0 16px 0; font-size: 15px; line-height: 24px;">Your verification code:</p>
                        <div style="text-align: center; margin: 24px 0;">
                          <div style="display: inline-block; background-color: #ffffff; border: 1.5px solid #3C050F; border-radius: 6px; padding: 14px 36px;">
                            <span style="font-size: 28px; font-weight: 700; letter-spacing: 10px; color: #3C050F; font-family: 'Courier New', monospace;">{code}</span>
                          </div>
                        </div>
                        <div style="text-align: center; margin: 28px 0;">
                          <a href="{verify_link}" style="display: inline-block; background-color: #3C050F; color: #ffffff; text-decoration: none; padding: 12px 38px; border-radius: 6px; font-size: 15px; font-weight: 600;">Verify Email</a>
                        </div>
                        <p style="color: #6b7280; margin: 28px 0 12px 0; font-size: 13px; line-height: 20px; font-style: italic;">"Start where you are. Use what you have. Do what you can." - Arthur Ashe</p>
                        <p style="color: #9ca3af; margin: 12px 0 0 0; font-size: 12px; line-height: 18px;">This code expires in 15 minutes.</p>
                      </td>
                    </tr>
                    <tr>
                      <td style="background-color: #ffffff; padding: 24px 40px; text-align: center; border-top: 1px solid #f3f4f6;">
                        <p style="color: #9ca3af; margin: 0; font-size: 12px;">© 2026 Trackly</p>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </body>
        </html>
        """
        try:
            send_email(user.email, "Trackly - Complete Your Registration", body, html_body)
        except Exception as exc:
            print(f"Could not send verification email: {exc}", flush=True)

    def verify_email(self, email: str, code: str) -> dict:
        user = self.repo.get_by_email(email)
        if not user:
            raise HTTPException(status_code=400, detail="Invalid verification request")
        if user.verification_code != code:
            raise HTTPException(status_code=400, detail="Invalid verification code")
        if user.verification_expires_at and user.verification_expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Verification code expired")
        user.is_verified = True
        user.verification_code = None
        user.verification_expires_at = None
        user.last_login_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        return {"message": "MFA verification successful", "verified": True}

    def resend_verification(self, email: str) -> dict:
        user = self.repo.get_by_email(email)
        if not user:
            raise HTTPException(status_code=400, detail="Invalid request")
        code = generate_verification_code()
        user.verification_code = code
        user.verification_expires_at = datetime.utcnow() + timedelta(minutes=15)
        self.db.commit()
        self._send_verification_email(user, code)
        return {"message": "New verification code sent"}

    def authenticate(self, email: str, password: str) -> User:
        user = self.repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is not activated")
        code = generate_verification_code()
        user.verification_code = code
        user.verification_expires_at = datetime.utcnow() + timedelta(minutes=15)
        self.db.commit()
        self._send_login_verification_email(user, code)
        raise HTTPException(status_code=403, detail="MFA required. Verification code sent to your email.")

    def _send_login_verification_email(self, user: User, code: str) -> None:
        verify_link = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/verify-email?email={user.email}&code={code}"
        body = (
            f"Hi {user.name},\n\n"
            f"We received a sign in request to your Trackly account. Please verify it's you by entering the code below:\n\n"
            f"Your verification code is: {code}\n\n"
            f"Sign in automatically: {verify_link}\n\n"
            f"\"Time is the most valuable thing a man can spend.\" - Theophrastus\n\n"
            f"This code expires in 15 minutes and is only valid for this sign in attempt.\n\n"
            f"If you didn't attempt to sign in, please ignore this email or change your password.\n\n"
            f"Trackly"
        )
        html_body = f"""
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
          </head>
          <body style="margin: 0; padding: 0; background-color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #ffffff;">
              <tr>
                <td align="center">
                  <table role="presentation" width="600" cellspacing="0" cellpadding="0">
                    <tr>
                      <td style="background-color: #3C050F; padding: 25px 40px; text-align: center;">
                        <h1 style="color: #ffffff; margin: 0; font-size: 26px; font-weight: 700;">Trackly</h1>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding: 40px 40px;">
                        <h2 style="color: #111827; margin: 0 0 16px 0; font-size: 22px; font-weight: 600;">Sign In Request</h2>
                        <p style="color: #374151; margin: 0 0 20px 0; font-size: 15px; line-height: 24px;">Hi {user.name},</p>
                        <p style="color: #374151; margin: 0 0 28px 0; font-size: 15px; line-height: 24px;">We received a sign in request to your Trackly account. Please verify it's you by entering the code below:</p>
                        <p style="color: #374151; margin: 0 0 16px 0; font-size: 15px; line-height: 24px;">Your verification code:</p>
                        <div style="text-align: center; margin: 24px 0;">
                          <div style="display: inline-block; background-color: #ffffff; border: 1.5px solid #3C050F; border-radius: 6px; padding: 14px 36px;">
                            <span style="font-size: 28px; font-weight: 700; letter-spacing: 10px; color: #3C050F; font-family: 'Courier New', monospace;">{code}</span>
                          </div>
                        </div>
                        <div style="text-align: center; margin: 28px 0;">
                          <a href="{verify_link}" style="display: inline-block; background-color: #3C050F; color: #ffffff; text-decoration: none; padding: 12px 38px; border-radius: 6px; font-size: 15px; font-weight: 600;">Sign in automatically</a>
                        </div>
                        <p style="color: #6b7280; margin: 28px 0 12px 0; font-size: 13px; line-height: 20px; font-style: italic;">"Time is the most valuable thing a man can spend." - Theophrastus</p>
                        <p style="color: #6b7280; margin: 12px 0 8px 0; font-size: 13px; line-height: 20px;">This code expires in 15 minutes and is only valid for this sign in attempt.</p>
                        <p style="color: #6b7280; margin: 8px 0 0 0; font-size: 13px; line-height: 20px;">If you didn't attempt to sign in, please ignore this email or change your password.</p>
                      </td>
                    </tr>
                    <tr>
                      <td style="background-color: #ffffff; padding: 24px 40px; text-align: center; border-top: 1px solid #f3f4f6;">
                        <p style="color: #9ca3af; margin: 0; font-size: 12px;">© 2026 Trackly</p>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </body>
        </html>
        """
        try:
            send_email(user.email, "Trackly - Sign In Verification", body, html_body)
        except Exception as exc:
            print(f"Could not send login verification email: {exc}", flush=True)

    def create_team_user(self, team_lead: User, group_id: int, data: TeamRegisterUser) -> User:
        from tracker.repositories.membership_repository import MembershipRepository
        
        memberships = MembershipRepository(self.db)
        m = memberships.get(team_lead.id, group_id)
        if not m or str(m.role).lower() != 'lead':
            raise HTTPException(status_code=403, detail="Only team leads can register users")

        if self.repo.get_by_email(data.email):
            raise HTTPException(status_code=400, detail="Email already registered")

        code = generate_verification_code()
        user = User(
            name=data.name,
            email=data.email,
            hashed_password=hash_password(data.password),
            skills=data.skills,
            is_verified=True,
            is_active=False,
            activation_token=code,
            activation_expires_at=datetime.utcnow() + timedelta(minutes=15),
        )
        user = self.repo.create(user)
        self._send_activation_email(user, code)
        return user

    def _send_activation_email(self, user: User, token: str) -> None:
        link = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/activate?email={user.email}&code={token}"
        body = (
            f"Hi {user.name},\n\n"
            f"You have been registered by a team leader on {settings.APP_NAME}.\n\n"
            f"Activate your account using this link (expires in 15 minutes):\n\n"
            f"{link}\n\n"
            "If you did not expect this, you can ignore this email."
        )
        html_body = f"""
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
          </head>
          <body style="margin: 0; padding: 0; background-color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #ffffff;">
              <tr>
                <td align="center">
                  <table role="presentation" width="600" cellspacing="0" cellpadding="0">
                    <tr>
                      <td style="background-color: #3C050F; padding: 25px 40px; text-align: center;">
                        <h1 style="color: #ffffff; margin: 0; font-size: 26px; font-weight: 700;">Trackly</h1>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding: 40px 40px;">
                        <h2 style="color: #111827; margin: 0 0 16px 0; font-size: 22px; font-weight: 600;">Account Activation</h2>
                        <p style="color: #374151; margin: 0 0 24px 0; font-size: 15px; line-height: 24px;">Hi {user.name},</p>
                        <p style="color: #374151; margin: 0 0 24px 0; font-size: 15px; line-height: 24px;">A team leader has invited you to Trackly. Use the activation code below to activate your account:</p>
                        <p style="color: #374151; margin: 0 0 16px 0; font-size: 15px; line-height: 24px;">Your activation code:</p>
                        <div style="text-align: center; margin: 24px 0;">
                          <div style="display: inline-block; background-color: #ffffff; border: 1.5px solid #3C050F; border-radius: 6px; padding: 14px 36px;">
                            <span style="font-size: 28px; font-weight: 700; letter-spacing: 10px; color: #3C050F; font-family: 'Courier New', monospace;">{token}</span>
                          </div>
                        </div>
                        <div style="text-align: center; margin: 28px 0;">
                          <a href="{link}" style="display: inline-block; background-color: #3C050F; color: #ffffff; text-decoration: none; padding: 12px 38px; border-radius: 6px; font-size: 15px; font-weight: 600;">Activate Account</a>
                        </div>
                        <p style="color: #6b7280; margin: 24px 0 0 0; font-size: 13px; line-height: 20px;">This code expires in 15 minutes.</p>
                      </td>
                    </tr>
                    <tr>
                      <td style="background-color: #ffffff; padding: 24px 40px; text-align: center; border-top: 1px solid #f3f4f6;">
                        <p style="color: #9ca3af; margin: 0; font-size: 12px;">© 2026 Trackly</p>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </body>
        </html>
        """
        try:
            send_email(user.email, "Trackly - Activate Account", body, html_body)
        except Exception as exc:
            print(f"Could not send activation email: {exc}", flush=True)

    def activate_account(self, token: str = None, email: str = None, code: str = None, password: str = None) -> dict:
        if email and code:
            user = self.repo.get_by_email(email)
            if not user or user.activation_token != code:
                raise HTTPException(status_code=400, detail="Invalid or expired activation code")
        else:
            user = self.db.query(User).filter(User.activation_token == token).first()
            if not user:
                raise HTTPException(status_code=400, detail="Invalid or expired activation token")
        if user.activation_expires_at and user.activation_expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Activation code expired")
        if password:
            user.hashed_password = hash_password(password)
        user.is_active = True
        user.activation_token = None
        user.activation_expires_at = None
        self.db.commit()
        self.db.refresh(user)
        return {"message": "Account activated successfully"}

    def get_activation_email(self, token: str) -> str:
        user = self.db.query(User).filter(User.activation_token == token).first()
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired activation token")
        return user.email

    def resend_activation(self, email: str) -> dict:
        user = self.repo.get_by_email(email)
        if not user:
            raise HTTPException(status_code=400, detail="Invalid request")
        code = generate_verification_code()
        user.activation_token = code
        user.activation_expires_at = datetime.utcnow() + timedelta(minutes=15)
        self.db.commit()
        self._send_activation_email(user, code)
        return {"message": "New activation code sent"}
