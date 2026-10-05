import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./progress_tracker.db")
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 12))
    FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "*")
    GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
    APP_NAME: str = os.environ.get("APP_NAME", "Ember")
    FRONTEND_BASE_URL: str = os.environ.get("FRONTEND_BASE_URL", "http://localhost:3000")
    RESET_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("RESET_TOKEN_EXPIRE_MINUTES", 30))
    SMTP_HOST: str = os.environ.get("SMTP_HOST", "")
    SMTP_PORT: int = int(os.environ.get("SMTP_PORT", 587))
    SMTP_USER: str = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD: str = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.environ.get("SMTP_FROM", "")


settings = Settings()
