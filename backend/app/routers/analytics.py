"""
F9 analytics - MEMBER 2.
The admin dashboard (frontend/src/components/Dashboard.jsx) calls these two routes.
Keep the URLs and JSON shapes exactly as below; fill in the TODO queries
(PostgreSQL directly, or DuckDB/Parquet - your choice, same output).
Spec: docs/ANALYTICS_SPEC.md
"""
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.auth import require_admin
from app.db import get_session
from app.models import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ---------- response shapes (do not rename fields) ----------
class Kpis(BaseModel):
    members: int
    papers: int
    posts: int
    comments: int
    saves_30d: int


class TopSaved(BaseModel):
    paper_id: str
    title: str
    save_count: int


class CrossDept(BaseModel):
    from_department: str
    to_department: str
    count: int


class OverviewOut(BaseModel):
    kpis: Kpis
    top_saved: List[TopSaved]
    cross_department: List[CrossDept]


class Series(BaseModel):
    key: str
    label: str
    counts: List[int]          # same length and order as periods


class BreakdownItem(BaseModel):
    key: str                   # department name | tag | user UUID
    label: str                 # what to display
    count: int


class Breakdown(BaseModel):
    dimension: Literal["department", "topic", "member"]
    items: List[BreakdownItem]


class TopicsOut(BaseModel):
    periods: List[str]         # ["2026-06", ..., "2026-11"] oldest -> newest
    series: List[Series]       # top 4 topics in this scope
    breakdown: Breakdown


# ---------- routes ----------
@router.get("/overview", response_model=OverviewOut)
def overview(session: Session = Depends(get_session), admin: User = Depends(require_admin)):
    # TODO (Member 2): real queries - see docs/ANALYTICS_SPEC.md section 1
    return OverviewOut(
        kpis=Kpis(members=0, papers=0, posts=0, comments=0, saves_30d=0),
        top_saved=[],
        cross_department=[],
    )


@router.get("/topics", response_model=TopicsOut)
def topics(
    months: int = 6,
    department: Optional[str] = None,
    tag: Optional[str] = None,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin),
):
    # TODO (Member 2): real queries - see docs/ANALYTICS_SPEC.md section 2
    dimension = "member" if tag else "topic" if department else "department"
    return TopicsOut(periods=[], series=[], breakdown=Breakdown(dimension=dimension, items=[]))
