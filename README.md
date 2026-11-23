# Chanakya Research Commons

Research platform for Chanakya University — Data Mining and Warehousing course project.

| Member | Owns |
| --- | --- |
| Member 1 | App & UI — F1 accounts, F2 posts, F3 library, all React screens |
| Member 2 | Data platform — F4 ingestion, papers table, synthetic data, MinIO/Parquet/DuckDB, F9 analytics |
| Member 3 | Search & intelligence — F5 search, F6 recommendations, F7 trends, F8 research assistant |

## Stack

React (Vite) · FastAPI · PostgreSQL 16 · MinIO · Docker Compose

## Run it

Needs Docker Desktop (or Docker Engine + Compose).

```bash
cp .env.example .env        # then change the passwords in .env
docker compose up --build
```

| Service | URL |
| --- | --- |
| Website (React) | http://localhost:5173 |
| API (FastAPI) | http://localhost:8000/api/health |
| API docs | http://localhost:8000/docs |
| MinIO console | http://localhost:9001 |
| PostgreSQL | localhost:5432 |

The database schema loads automatically **on the first start only**:

| File | What it does | Owner |
| --- | --- | --- |
| `db/init/01_schema.sql` | App tables (users, posts, comments, saves, events…) | Member 1 |
| `db/init/02_papers.sql` | Papers table | Member 2 |
| `db/init/03_paper_links.sql` | Links app tables to `papers(id)` | shared |

After changing any file in `db/init/`, reset the database:

```bash
docker compose down -v      # -v deletes the database volume
docker compose up --build
```

## Project layout

```
db/init/            SQL that builds the database
backend/app/        FastAPI app (main.py, db.py, security.py, routers/)
frontend/src/       React app
```

Each member adds routes as a router file in `backend/app/routers/` under `/api`.

## Adding your routes (all members)

1. Create `backend/app/routers/<yours>.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlmodel import Session

from app.auth import get_current_user, get_current_user_optional, require_admin
from app.db import get_session
from app.models import User

router = APIRouter(tags=["intel"])

@router.get("/trends")
def trends(days: int = 7,
           session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):        # logged-in user
    rows = session.exec(text("""
        SELECT target_tag AS tag, COUNT(*) AS count
        FROM events
        WHERE target_type = 'topic' AND created_at >= now() - make_interval(days => :days)
        GROUP BY target_tag ORDER BY count DESC LIMIT 20
    """), params={"days": days}).all()
    return {"items": [{"tag": r.tag, "count": r.count, "change_pct": None, "is_spike": False} for r in rows]}
```

2. Register it in `backend/app/main.py`:

```python
from app.routers import intel
app.include_router(intel.router, prefix="/api")
```

| Dependency | Gives you |
| --- | --- |
| `Depends(get_session)` | Database session |
| `Depends(get_current_user)` | Logged-in `User` (401 if not logged in) |
| `Depends(get_current_user_optional)` | `User` or `None` |
| `Depends(require_admin)` | Logged-in admin (403 otherwise) |

Errors use the agreed format — raise
`HTTPException(404, detail={"code": "not_found", "message": "..."})`
and the API returns `{"error": {"code": ..., "message": ...}}`.

## Testing with a login token

1. Open http://localhost:8000/docs
2. `POST /api/auth/register` → create a user
3. Click **Authorize** (top right) → email in *username*, password → Authorize
4. Every protected route in /docs now sends the token automatically.

Fake users from the data generator log in with their email and `Demo@123`.

## Auth routes (Member 1)

| Route | Body | Returns |
| --- | --- | --- |
| `POST /api/auth/register` | JSON `{name, email, password, role?, department?}` | `{access_token, token_type, user}` |
| `POST /api/auth/login` | Form `username`=email, `password` | `{access_token, token_type, user}` |
| `GET /api/auth/me` | header `Authorization: Bearer <token>` | `user` |

## Rules

- Never commit `.env` or any password / API key.
- Use the agreed IDs (UUID) and response formats.
- Work on a branch and open a pull request into `main`.
