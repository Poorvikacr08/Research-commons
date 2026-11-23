"""
Chanakya Research Commons - FastAPI back end.

Each member adds their own router file in app/routers/ and registers it here:
  - Member 1: accounts, posts, library   (routers/accounts.py, posts.py, library.py)
  - Member 2: analytics                   (routers/analytics.py)
  - Member 3: search, recs, trends, ask   (routers/intel.py)
All routes live under /api.
"""
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlmodel import Session

from app.db import get_session

app = FastAPI(title="Chanakya Research Commons API")


# ---- Agreed error format: { "error": { "code": ..., "message": ... } } ----
# Raise errors like: HTTPException(404, detail={"code": "not_found", "message": "Paper not found."})
@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        error = exc.detail
    else:
        error = {"code": f"http_{exc.status_code}", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={"error": error}, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first.get("loc", [])[1:])
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "invalid_input", "message": f"{field}: {first.get('msg', 'invalid')}"}},
    )


@app.get("/api/health")
def health(session: Session = Depends(get_session)):
    """Quick check that the API is up and can read the database."""
    tables = session.exec(text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' ORDER BY table_name"
    )).all()
    counts = {}
    for t in ("users", "posts", "comments", "saves", "events", "papers"):
        if (t,) in tables:
            counts[t] = session.exec(text(f"SELECT COUNT(*) FROM {t}")).one()[0]
    return {"status": "ok", "tables": [t[0] for t in tables], "row_counts": counts}


# ---- Routers (each member registers theirs here) ----
from app.routers import auth, library, posts, users  # noqa: E402  Member 1

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(posts.router, prefix="/api")
app.include_router(library.router, prefix="/api")
# from app.routers import intel        # Member 3
# app.include_router(intel.router, prefix="/api")
