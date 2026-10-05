from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from tracker.models import *  # noqa - ensures every model is registered before create_all
from tracker.core.config import settings

from tracker.routers import auth, users, groups, tasks, checkins, group_goals, feedback, ai_insights, dashboard, help_requests, quotes

Base.metadata.create_all(bind=engine)

app = FastAPI(title=f"{settings.APP_NAME} API")

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


@app.get("/")
def root():
    return {"status": f"{settings.APP_NAME} API running", "docs": "/docs"}
