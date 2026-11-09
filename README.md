# Trackly Backend

FastAPI backend for **Trackly** (task/group tracking, check-ins, group goals, discussions & DMs, help requests, notifications, and AI insights/chat).

## Stack
- Python, **FastAPI** + Uvicorn
- **SQLAlchemy** (SQLite locally by default; Postgres supported via `DATABASE_URL`)
- JWT auth (`python-jose`), password hashing (`bcrypt`/`passlib`)
- Email, Groq-powered AI features (optional, via env vars)

## Setup
```bash
cd backend  # or repo root if this is the standalone backend repo
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit values
```

## Run
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

## Environment (`.env`)
See `.env.example`. Key vars:
- `DATABASE_URL`: e.g. `sqlite:///./progress_tracker.db` or a Postgres URL
- `SECRET_KEY`: long random string (JWT signing)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: token lifetime
- `FRONTEND_URL`: allowed frontend origin / links
- `GROQ_API_KEY`: required for AI insight/chat features
- `APP_NAME`: display name

## Notes
- On startup the app runs `create_all` and lightweight column migrations for evolving tables (messages/users presence). For production, manage migrations deliberately.
- Media uploads are served from `uploads/` and avatars from `static/` (ensure writable/storage in your deploy).
- Do not commit secrets (`.env`) or local DB/uploads.

## Related
- Frontend: https://github.com/EyerusalemGebremedhin/Trackly-frontend
