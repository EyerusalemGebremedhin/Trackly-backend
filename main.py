from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path

from database import engine, Base
from tracker.models import *  # noqa
from tracker.core.config import settings

from tracker.routers import auth, users, groups, tasks, checkins, group_goals, feedback, ai_insights, dashboard, help_requests, quotes, chat, notifications, group_checkins, group_messages, dm

Base.metadata.create_all(bind=engine)

# lightweight migration for added columns (SQLite/Postgres)
from sqlalchemy import inspect, text
def _ensure_columns():
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, col, ddl in [
            ("direct_messages", "hidden_for_user_id", "INTEGER"),
            ("group_messages", "hidden_for_user_id", "INTEGER"),
        ]:
            if table in insp.get_table_names() and col not in [c["name"] for c in insp.get_columns(table)]:
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {col} {ddl}'))
try:
    _ensure_columns()
except Exception:
    pass

app = FastAPI(title=f"{settings.APP_NAME} API", version="2.0.0")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

os.makedirs("/tmp/trackly_uploads", exist_ok=True)
os.makedirs("/home/Student/Downloads/trackly/backend/static/avatars", exist_ok=True)
try:
    app.mount("/static", StaticFiles(directory="/home/Student/Downloads/trackly/backend/static"), name="static")
except Exception:
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL] if settings.FRONTEND_URL != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(groups.router)
app.include_router(tasks.router)
app.include_router(checkins.router)
app.include_router(group_goals.router)
app.include_router(feedback.router)
app.include_router(ai_insights.router)
app.include_router(dashboard.router)
app.include_router(help_requests.router)
app.include_router(quotes.router)
app.include_router(chat.router)
app.include_router(notifications.router)
app.include_router(group_checkins.router)
app.include_router(group_messages.router)
app.include_router(dm.router)


@app.get("/")
def root():
    return {"status": f"{settings.APP_NAME} API running", "docs": "/docs", "version": "2.0.0"}
