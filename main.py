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

def _pg_type(col):
    try:
        return col.type.compile(dialect=engine.dialect)
    except Exception:
        return "TEXT"

def _ensure_columns():
    targets = []
    try:
        from tracker.models.dm import DirectMessage
        targets.append(DirectMessage.__table__)
    except Exception:
        pass
    try:
        from tracker.models.group_message import GroupMessage
        targets.append(GroupMessage.__table__)
    except Exception:
        pass

    with engine.connect() as conn:
        insp = inspect(conn)
        tables = set(insp.get_table_names())
        for table in targets:
            if table.name not in tables:
                continue
            existing = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in existing or col.primary_key:
                    continue
                ddl = _pg_type(col)
                if not col.nullable and col.server_default is None and col.default is None:
                    ddl += " NULL"
                try:
                    conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {ddl}'))
                    conn.commit()
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass

_ensure_columns()

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
