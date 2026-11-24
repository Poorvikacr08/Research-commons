
"""
F9 Analytics - Member 2
Admin dashboard analytics endpoints.
"""

from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from pydantic import BaseModel
from sqlmodel import Session

from app.auth import require_admin
from app.db import get_session
from app.models import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


# Response models
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
    counts: List[int]


class BreakdownItem(BaseModel):
    key: str
    label: str
    count: int


class Breakdown(BaseModel):
    dimension: Literal["department", "topic", "member"]
    items: List[BreakdownItem]


class TopicsOut(BaseModel):
    periods: List[str]
    series: List[Series]
    breakdown: Breakdown


# Shared activity query
ACTIVITY_SQL = """
    WITH activity AS (
        SELECT p.author_id AS user_id, pt.tag, p.created_at AS ts
        FROM posts p
        JOIN post_tags pt ON pt.post_id = p.id

        UNION ALL

        SELECT c.author_id AS user_id, pt.tag, c.created_at AS ts
        FROM comments c
        JOIN post_tags pt ON pt.post_id = c.post_id

        UNION ALL

        SELECT u.user_id, pt.tag, u.created_at AS ts
        FROM upvotes u
        JOIN post_tags pt ON pt.post_id = u.post_id
    )
    SELECT
        to_char(date_trunc('month', a.ts), 'YYYY-MM') AS period,
        a.tag,
        usr.department,
        usr.id::text AS user_id,
        usr.name,
        COUNT(*) AS n
    FROM activity a
    JOIN users usr ON usr.id = a.user_id
    WHERE
        a.ts >= date_trunc('month', now())
            - make_interval(months => :months - 1)
        AND usr.department IS NOT NULL
       
AND (CAST(:department AS TEXT) IS NULL OR usr.department = CAST(:department AS TEXT))
AND (CAST(:tag AS TEXT) IS NULL OR a.tag = CAST(:tag AS TEXT))

    GROUP BY 1, 2, 3, 4, 5
"""


# Overview endpoint
@router.get("/overview", response_model=OverviewOut)
def overview(
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    kpi_row = session.exec(text("""
        SELECT
            (SELECT COUNT(*) FROM users) AS members,
            (SELECT COUNT(*) FROM papers) AS papers,
            (SELECT COUNT(*) FROM posts) AS posts,
            (SELECT COUNT(*) FROM comments) AS comments,
            (SELECT COUNT(*) FROM saves
             WHERE saved_at >= now() - interval '30 days') AS saves_30d
    """)).one()

    top_rows = session.exec(text("""
        SELECT
            l.paper_id::text AS paper_id,
            p.title,
            l.save_count
        FROM library_save_counts l
        JOIN papers p ON p.id = l.paper_id
        ORDER BY l.save_count DESC, p.title
        LIMIT 8
    """)).all()

    cross_rows = session.exec(text("""
        SELECT
            actor.department AS from_department,
            author.department AS to_department,
            COUNT(*) AS count
        FROM (
            SELECT c.author_id AS actor_id, c.post_id
            FROM comments c

            UNION ALL

            SELECT u.user_id AS actor_id, u.post_id
            FROM upvotes u
        ) x
        JOIN posts p ON p.id = x.post_id
        JOIN users actor ON actor.id = x.actor_id
        JOIN users author ON author.id = p.author_id
        WHERE
            actor.department IS NOT NULL
            AND author.department IS NOT NULL
        GROUP BY actor.department, author.department
        ORDER BY count DESC
    """)).all()

    return OverviewOut(
        kpis=Kpis(
            members=int(kpi_row.members),
            papers=int(kpi_row.papers),
            posts=int(kpi_row.posts),
            comments=int(kpi_row.comments),
            saves_30d=int(kpi_row.saves_30d),
        ),
        top_saved=[
            TopSaved(
                paper_id=str(r.paper_id),
                title=r.title,
                save_count=int(r.save_count),
            )
            for r in top_rows
        ],
        cross_department=[
            CrossDept(
                from_department=r.from_department,
                to_department=r.to_department,
                count=int(r.count),
            )
            for r in cross_rows
        ],
    )


# Topics and drill-down endpoint
@router.get("/topics", response_model=TopicsOut)
def topics(
    months: int = 6,
    department: Optional[str] = None,
    tag: Optional[str] = None,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin),
):
    if months < 1 or months > 24:
        raise HTTPException(
            400,
            detail={
                "code": "invalid_months",
                "message": "Months must be between 1 and 24."
            }
        )

    if tag and not department:
        raise HTTPException(
            400,
            detail={
                "code": "department_required",
                "message": "A department is required when filtering by tag."
            }
        )

    # Generate all calendar months, including zero-activity months.
    period_rows = session.exec(text("""
        SELECT to_char(month_start, 'YYYY-MM') AS period
        FROM generate_series(
            date_trunc('month', now())
                - make_interval(months => :months - 1),
            date_trunc('month', now()),
            interval '1 month'
        ) AS months_series(month_start)
        ORDER BY month_start
    """), params={"months": months}).all()

    periods = [r.period for r in period_rows]
    period_index = {p: i for i, p in enumerate(periods)}

    activity_rows = session.exec(
        text(ACTIVITY_SQL),
        params={
            "months": months,
            "department": department,
            "tag": tag,
        }
    ).all()

    topic_counts = {}
    topic_totals = {}
    department_totals = {}
    member_totals = {}
    member_names = {}

    for r in activity_rows:
        topic = r.tag
        period = r.period
        count = int(r.n)

        if topic not in topic_counts:
            topic_counts[topic] = [0] * len(periods)
            topic_totals[topic] = 0

        if period in period_index:
            topic_counts[topic][period_index[period]] += count

        topic_totals[topic] += count

        if department is None:
            department_totals[r.department] = (
                department_totals.get(r.department, 0) + count
            )
        elif tag is None:
            department_totals[topic] = (
                department_totals.get(topic, 0) + count
            )
        else:
            member_totals[r.user_id] = (
                member_totals.get(r.user_id, 0) + count
            )
            member_names[r.user_id] = r.name

    if tag is not None:
        dimension = "member"
        breakdown_items = [
            BreakdownItem(
                key=user_id,
                label=member_names[user_id],
                count=count,
            )
            for user_id, count in sorted(
                member_totals.items(),
                key=lambda x: (-x[1], x[0])
            )[:10]
        ]

    elif department is not None:
        dimension = "topic"
        breakdown_items = [
            BreakdownItem(
                key=topic,
                label=topic,
                count=count,
            )
            for topic, count in sorted(
                department_totals.items(),
                key=lambda x: (-x[1], x[0])
            )[:10]
        ]

    else:
        dimension = "department"
        breakdown_items = [
            BreakdownItem(
                key=dept,
                label=dept,
                count=count,
            )
            for dept, count in sorted(
                department_totals.items(),
                key=lambda x: (-x[1], x[0])
            )
        ]

    top_topics = sorted(
        topic_totals.items(),
        key=lambda x: (-x[1], x[0])
    )[:4]

    series_items = [
        Series(
            key=topic,
            label=topic,
            counts=topic_counts[topic],
        )
        for topic, total in top_topics
    ]

    return TopicsOut(
        periods=periods,
        series=series_items,
        breakdown=Breakdown(
            dimension=dimension,
            items=breakdown_items,
        ),
    )
