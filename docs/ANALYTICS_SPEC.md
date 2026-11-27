# F9 Analytics API — admin analytics

The admin dashboard calls the overview, monthly engagement, and topic drill-down
routes implemented in `backend/app/routers/analytics.py`.

- Both routes are **admin-only**: keep `Depends(require_admin)`.
- Register once in `backend/app/main.py`:
  ```python
  from app.routers import analytics
  app.include_router(analytics.router, prefix="/api")
  ```
- Errors: `raise HTTPException(400, detail={"code": "...", "message": "..."})`.
- You may compute with PostgreSQL directly or with DuckDB/Parquet — only the JSON shape matters.

---

## 1. `GET /api/analytics/overview`

```json
{
  "kpis": { "members": 58, "papers": 512, "posts": 640, "comments": 1630, "saves_30d": 2214 },
  "top_saved": [ { "paper_id": "<uuid>", "title": "Attention Is All You Need", "save_count": 31 } ],
  "cross_department": [ { "from_department": "Computer Science", "to_department": "Electronics", "count": 28 } ]
}
```

| Field | Definition |
| --- | --- |
| `members` | `COUNT(*) FROM users` |
| `papers` | `COUNT(*) FROM papers` |
| `posts` | `COUNT(*) FROM posts` |
| `comments` | `COUNT(*) FROM comments` |
| `saves_30d` | `COUNT(*) FROM saves WHERE saved_at >= now() - interval '30 days'` |
| `top_saved` | Top 8 from the `library_save_counts` view joined to `papers`, ordered by `save_count DESC` |
| `cross_department` | Interactions where a member of department A comments on or upvotes a post written by a member of department B. One row per (A, B) pair with its count. Include A = B. Skip users with no department. |

Cross-department SQL sketch:

```sql
SELECT actor.department AS from_department, author.department AS to_department, COUNT(*) AS count
FROM (
    SELECT c.author_id AS actor_id, c.post_id FROM comments c
    UNION ALL
    SELECT u.user_id, u.post_id FROM upvotes u
) x
JOIN posts p        ON p.id = x.post_id
JOIN users actor    ON actor.id = x.actor_id
JOIN users author   ON author.id = p.author_id
WHERE actor.department IS NOT NULL AND author.department IS NOT NULL
GROUP BY 1, 2;
```

---

## 2. `GET /api/analytics/topics?months=6&department=&tag=`

Drill-down: **university → department → topic → member**.

| Query | Scope | `series` | `breakdown.dimension` | `breakdown.items` |
| --- | --- | --- | --- | --- |
| (none) | whole university | top 4 topics | `"department"` | activity per department, `key` = `label` = department name |
| `department=X` | department X only | top 4 topics in X | `"topic"` | top 10 topics in X, `key` = `label` = tag |
| `department=X&tag=Y` | topic Y in X | just topic Y | `"member"` | top 10 members, `key` = user UUID, `label` = name |

```json
{
  "periods": ["2026-06", "2026-07", "2026-08", "2026-09", "2026-10", "2026-11"],
  "series": [ { "key": "nlp", "label": "nlp", "counts": [40, 44, 51, 49, 58, 61] } ],
  "breakdown": { "dimension": "department",
                 "items": [ { "key": "Computer Science", "label": "Computer Science", "count": 310 } ] }
}
```

Rules:
- `periods`: the last `months` calendar months as `YYYY-MM`, oldest first, **including months with zero activity**.
- Every `series[].counts` has exactly `len(periods)` numbers (0 where nothing happened).
- `series`: at most 4 (the dashboard draws 4 lines). Ordered by total activity, highest first.
- `breakdown.items`: ordered by `count DESC`.
- Empty result → `[]`, not an error.

**"Activity" (use the same definition everywhere):** a post with tag *t* being written, a comment on a post with tag *t*, or an upvote on a post with tag *t*. The department is the department of the member who did it.

```sql
WITH activity AS (
    SELECT p.author_id AS user_id, pt.tag, p.created_at AS ts
    FROM posts p JOIN post_tags pt ON pt.post_id = p.id
    UNION ALL
    SELECT c.author_id, pt.tag, c.created_at
    FROM comments c JOIN post_tags pt ON pt.post_id = c.post_id
    UNION ALL
    SELECT u.user_id, pt.tag, u.created_at
    FROM upvotes u JOIN post_tags pt ON pt.post_id = u.post_id
)
SELECT to_char(date_trunc('month', a.ts), 'YYYY-MM') AS period, a.tag, usr.department, COUNT(*) AS n
FROM activity a JOIN users usr ON usr.id = a.user_id
WHERE a.ts >= date_trunc('month', now()) - make_interval(months => :months - 1)
  -- AND usr.department = :department   (when department is given)
  -- AND a.tag = :tag                   (when tag is given)
GROUP BY 1, 2, 3;
```

Tags are already stored lower-case and trimmed by the app, so match them exactly.

---

## 3. `GET /api/analytics/engagement?months=6`

Admin-only monthly totals for posts, comments, upvotes, and saves. The response
contains the same calendar-month labels (including months with zero activity)
and one integer count per period for each series. `months` must be 1–24.

## How to verify

1. Make yourself admin:
   `docker compose exec db psql -U rc_admin -d research_commons -c "UPDATE users SET role='admin' WHERE email='you@...'"`
2. http://localhost:8000/docs → **Authorize** → try both routes.
3. http://localhost:5173/admin → the dashboard fills in; click a department bar to drill down.
