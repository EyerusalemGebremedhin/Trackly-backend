import os
from dotenv import load_dotenv

load_dotenv()


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "sqlite:///./progress_tracker.db")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def _frontend_base_url() -> str:
    explicit = os.environ.get("FRONTEND_BASE_URL")
    if explicit:
        return explicit
    configured = os.environ.get("FRONTEND_URL", "*")
    return configured if configured != "*" else "http://localhost:3000"


class Settings:
    DATABASE_URL: str = _database_url()
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
    FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "*")
    FRONTEND_BASE_URL: str = _frontend_base_url()
    GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
    APP_NAME: str = os.environ.get("APP_NAME", "Trackly")
    RESET_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("RESET_TOKEN_EXPIRE_MINUTES", 30))
    BREVO_API_KEY: str = os.environ.get("BREVO_API_KEY", "")
    MAIL_FROM: str = os.environ.get("MAIL_FROM") or os.environ.get("RESEND_FROM") or os.environ.get("SMTP_FROM") or "onboarding@resend.dev"
    SMTP_HOST: str = os.environ.get("SMTP_HOST", "")
    SMTP_PORT: int = int(os.environ.get("SMTP_PORT", 587))
    SMTP_USER: str = os.environ.get("SMTP_USER") or ""
    SMTP_PASSWORD: str = os.environ.get("SMTP_PASSWORD") or ""
    SMTP_FROM: str = os.environ.get("SMTP_FROM") or os.environ.get("MAIL_FROM") or os.environ.get("RESEND_FROM") or "onboarding@resend.dev"
    RESEND_API_KEY: str = os.environ.get("RESEND_API_KEY", "")


settings = Settings()
