"""Member 3: unified search, recommendations, trends, flags, and grounded Q&A.

The implementation is local and dependency-light. Search and passage ranking use
TF-IDF cosine similarity with a small, explicit research-term alias map; no paid
API or hosted model is required.
"""
from __future__ import annotations

import math
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlmodel import Session

from app.auth import get_current_user, require_admin
from app.db import get_session
from app.events import log_event
from app.intelligence_helpers import compose_evidence_answer, is_catalog_description, paper_member_ids, partition_paper_results, select_evidence_findings
from app.models import User
from app.mining.duplicates import find_near_duplicates

router = APIRouter(tags=["search and intelligence"])

# Transparent query expansion for common abbreviations and equivalent research terms.
# This gives the local TF-IDF search a useful meaning-based component while keeping
# every match explainable in the report and viva.
ALIASES = {
    "ai": ("artificial intelligence", "machine learning"),
    "artificial intelligence": ("ai", "machine learning"),
    "ml": ("machine learning",),
    "machine learning": ("ml", "artificial intelligence"),
    "llm": ("large language model", "generative ai"),
    "large language model": ("llm", "generative ai"),
    "gen ai": ("generative ai", "large language model"),
    "deep learning": ("neural network",),
    "neural network": ("deep learning",),
    "nlp": ("natural language processing",),
    "natural language processing": ("nlp",),
    "ir": ("information retrieval",),
    "information retrieval": ("ir",),
    "recommender": ("recommendation system",),
    "recommendation system": ("recommender",),
    "climate change": ("global warming",),
    "global warming": ("climate change",),
}
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "in", "is", "it", "of", "on", "or", "that", "the", "their", "this", "to",
    "using", "what", "with", "which", "who", "why",
}
TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)


def _tokens(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [t for t in TOKEN_RE.findall(value.lower()) if t not in STOP_WORDS and len(t) > 1]


def _expanded_query(query: str) -> List[str]:
    base = query.strip().lower()
    expanded = list(_tokens(base))
    for phrase, equivalents in ALIASES.items():
        if phrase in base:
            for equivalent in equivalents:
                expanded.extend(_tokens(equivalent))
    return expanded


def _tfidf_scores(query: str, documents: Sequence[str], expand: bool = True) -> List[float]:
    """Cosine similarity using in-process TF-IDF; returns scores from 0 to 1."""
    q_counts = Counter(_expanded_query(query) if expand else _tokens(query))
    if not q_counts or not documents:
        return [0.0] * len(documents)
    vectors = [Counter(_tokens(doc)) for doc in documents]
    df = Counter()
    for vector in vectors:
        df.update(vector.keys())
    n_docs = len(vectors)
    idf = {term: math.log((n_docs + 1) / (df.get(term, 0) + 1)) + 1.0 for term in q_counts}
    q_vec = {term: count * idf[term] for term, count in q_counts.items()}
    q_norm = math.sqrt(sum(value * value for value in q_vec.values())) or 1.0
    scores = []
    for vector in vectors:
        weighted = {term: count * idf[term] for term, count in vector.items() if term in idf}
        dot = sum(q_vec[term] * weighted.get(term, 0.0) for term in q_vec)
        d_norm = math.sqrt(sum(value * value for value in weighted.values())) or 1.0
        scores.append(max(0.0, min(1.0, dot / (q_norm * d_norm))))
    return scores


def _table_exists(session: Session, name: str) -> bool:
    return session.exec(text("SELECT to_regclass(:name)"), params={"name": f"public.{name}"}).one()[0] is not None


def _paper_rows(session: Session, deduplicate: bool = True) -> List[Dict[str, Any]]:
    """Read either the starter paper table or the normalized Member 2 schema."""
    paper_columns = {r[0] for r in session.exec(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'papers'
    """)).all()}
    if not paper_columns:
        raise RuntimeError("The papers table has not been created yet.")
    has_authors_table = _table_exists(session, "paper_authors")
    has_sources_table = _table_exists(session, "paper_sources")
    year_expr = "p.publication_year" if "publication_year" in paper_columns else ("p.year" if "year" in paper_columns else "NULL::integer")
    if "authors" in paper_columns:
        authors_expr = "p.authors"
    elif has_authors_table:
        authors_expr = "(SELECT string_agg(pa.author_name, ', ' ORDER BY pa.author_position) FROM paper_authors pa WHERE pa.paper_id = p.id)"
    else:
        authors_expr = "NULL::text"
    source_expr = "p.source" if "source" in paper_columns else (
        "(SELECT string_agg(DISTINCT ps.source_name, ', ' ORDER BY ps.source_name) FROM paper_sources ps WHERE ps.paper_id = p.id)"
        if has_sources_table else "NULL::text"
    )
    url_expr = "p.url" if "url" in paper_columns else (
        "(SELECT ps.source_url FROM paper_sources ps WHERE ps.paper_id = p.id AND ps.source_url IS NOT NULL ORDER BY ps.fetched_at DESC LIMIT 1)"
        if has_sources_table else "NULL::text"
    )
    keywords_expr = "p.keywords" if "keywords" in paper_columns else "NULL::text"
    rows = session.exec(text(f"""
        SELECT p.id, p.title, p.abstract, {authors_expr} AS authors,
               {year_expr} AS year, p.doi, p.arxiv_id, {url_expr} AS url,
               {source_expr} AS source, {keywords_expr} AS keywords
        FROM papers p
    """)).all()
    sources: Dict[str, List[str]] = {}
    if has_sources_table:
        for r in session.exec(text("SELECT paper_id, source_name FROM paper_sources ORDER BY source_name")).all():
            values = sources.setdefault(str(r.paper_id), [])
            if r.source_name and r.source_name not in values:
                values.append(r.source_name)
    papers = []
    for r in rows:
        source_list = sources.get(str(r.id), [])
        if not source_list and r.source:
            source_list = [part.strip() for part in str(r.source).split(",") if part.strip()]
        papers.append(dict(
            id=str(r.id), title=r.title or "Untitled", abstract=r.abstract,
            authors=r.authors, year=r.year, doi=r.doi, arxiv_id=r.arxiv_id,
            url=r.url, source=r.source, sources=source_list, keywords=r.keywords,
        ))
    return _deduplicate_papers(papers) if deduplicate else papers


def _normalize_identifier(value: Optional[str], kind: str) -> str:
    value = (value or "").strip().lower()
    if kind == "doi":
        value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value)
        value = re.sub(r"^doi:\s*", "", value)
    else:
        value = re.sub(r"^https?://arxiv\.org/(abs|pdf)/", "", value)
        value = re.sub(r"^arxiv:\s*", "", value)
        value = re.sub(r"\.pdf$", "", value)
        value = re.sub(r"v\d+$", "", value)
    return value.rstrip(" .")


def _deduplicate_papers(papers: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Collapse DOI/arXiv matches and very close titles into one searchable record."""
    if len(papers) < 2:
        return list(papers)
    parent = list(range(len(papers)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    seen: Dict[Tuple[str, str], int] = {}
    for index, paper in enumerate(papers):
        for key, value in (("doi", _normalize_identifier(paper.get("doi"), "doi")),
                           ("arxiv", _normalize_identifier(paper.get("arxiv_id"), "arxiv"))):
            if value:
                previous = seen.setdefault((key, value), index)
                union(index, previous)

    title_pairs = find_near_duplicates(papers, threshold=0.92)
    index_by_id = {str(paper.get("id")): index for index, paper in enumerate(papers)}
    for pair in title_pairs:
        left = index_by_id.get(str(pair["paper_id_1"]))
        right = index_by_id.get(str(pair["paper_id_2"]))
        if left is not None and right is not None:
            union(left, right)

    groups: Dict[int, List[Dict[str, Any]]] = {}
    for index, paper in enumerate(papers):
        groups.setdefault(find(index), []).append(paper)

    merged = []
    for group in groups.values():
        # Keep the most complete record, with a stable UUID tie-breaker.
        canonical = max(group, key=lambda p: (sum(bool(p.get(k)) for k in
                            ("abstract", "doi", "arxiv_id", "url", "authors", "year")),
                            str(p.get("id", ""))))
        item = dict(canonical)
        item["_member_ids"] = [str(p["id"]) for p in group]
        source_names = []
        for paper in group:
            for source in paper.get("sources") or ([paper.get("source")] if paper.get("source") else []):
                source = str(source).strip()
                if source and source.lower() not in {s.lower() for s in source_names}:
                    source_names.append(source)
        item["sources"] = source_names
        for key in ("abstract", "doi", "arxiv_id", "url", "authors", "year", "keywords"):
            if not item.get(key):
                item[key] = next((p.get(key) for p in group if p.get(key)), None)
        merged.append(item)
    return merged


def _paper_member_ids(paper: Dict[str, Any]) -> List[str]:
    return paper_member_ids(paper)


def _paper_save_count(paper: Dict[str, Any], counts: Dict[str, int]) -> int:
    return sum(counts.get(paper_id, 0) for paper_id in _paper_member_ids(paper))


def _paper_url(p: Dict[str, Any]) -> Optional[str]:
    return p.get("url") or (f"https://doi.org/{p['doi']}" if p.get("doi") else None)


def _paper_item(p: Dict[str, Any], score: float, item_type: str = "paper", save_count: int = 0) -> Dict[str, Any]:
    sources = p.get("sources") or ([p["source"]] if p.get("source") else [])
    snippet = p.get("abstract") or p.get("authors") or ""
    if len(snippet) > 280:
        snippet = snippet[:277].rsplit(" ", 1)[0] + "..."
    return {
        "id": str(p["id"]), "type": item_type, "title": p.get("title") or "Untitled",
        "snippet": snippet, "sources": sources, "score": round(float(score), 4),
        "url": _paper_url(p), "save_count": int(save_count),
    }


def _limit(value: int, maximum: int = 50) -> int:
    return max(1, min(int(value), maximum))


def _rank(query: str, docs: Sequence[Dict[str, Any]], text_for) -> List[Tuple[Dict[str, Any], float]]:
    values = [text_for(d) or "" for d in docs]
    scores = _tfidf_scores(query, values)
    ranked = sorted(zip(docs, scores), key=lambda pair: pair[1], reverse=True)
    return [(doc, score) for doc, score in ranked if score > 0]


def _query_match(query: str, value: Optional[str]) -> bool:
    q_terms = set(_expanded_query(query))
    return bool(q_terms.intersection(_tokens(value)))


def _member_rows(session: Session) -> List[Dict[str, Any]]:
    members = session.exec(text("""
        SELECT id, name, role, department, bio, created_at
        FROM users
    """)).all()
    interests: Dict[str, List[str]] = {}
    for row in session.exec(text("SELECT user_id, tag FROM user_interests ORDER BY tag")).all():
        interests.setdefault(str(row.user_id), []).append(row.tag)
    return [{
        "id": str(m.id), "name": m.name, "role": m.role, "department": m.department,
        "bio": m.bio, "created_at": m.created_at, "interests": interests.get(str(m.id), []),
    } for m in members]


def _member_item(m: Dict[str, Any], score: float, shared: Optional[List[str]] = None) -> Dict[str, Any]:
    snippet = m.get("bio") or ", ".join(m.get("interests", []))
    return {
        "id": m["id"], "type": "person", "title": m["name"], "snippet": snippet,
        "sources": [], "score": round(max(0.0, min(1.0, score)), 4), "url": None,
        "department": m.get("department"), "shared_interests": shared or [],
    }


def _post_rows(session: Session) -> List[Dict[str, Any]]:
    rows = session.exec(text("""
        SELECT p.id, p.title, p.body, p.author_id, p.created_at,
               u.name AS author_name, u.department AS author_department
        FROM posts p JOIN users u ON u.id = p.author_id
    """)).all()
    tags: Dict[str, List[str]] = {}
    for row in session.exec(text("SELECT post_id, tag FROM post_tags ORDER BY tag")).all():
        tags.setdefault(str(row.post_id), []).append(row.tag)
    return [{
        "id": str(r.id), "title": r.title, "body": r.body, "author_id": str(r.author_id),
        "created_at": r.created_at, "author_name": r.author_name,
        "author_department": r.author_department, "tags": tags.get(str(r.id), []),
    } for r in rows]


def _post_item(p: Dict[str, Any], score: float) -> Dict[str, Any]:
    body = p.get("body") or ""
    return {
        "id": p["id"], "type": "post", "title": p["title"],
        "snippet": body[:277] + ("..." if len(body) > 280 else ""),
        "sources": [], "score": round(score, 4), "url": None,
        "author": {"id": p["author_id"], "name": p["author_name"], "department": p["author_department"]},
        "created_at": p["created_at"].isoformat() if p.get("created_at") else None,
    }


def _safe_panel(session: Session, errors: Dict[str, str], key: str, function):
    try:
        return function()
    except Exception as exc:  # keep one panel failure from blanking the other panels
        session.rollback()
        errors[key] = "This result panel is temporarily unavailable."
        return []


@router.get("/search")
def unified_search(
    q: str = Query(min_length=1, max_length=250),
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Search external papers, saved library items, members, and posts in one response."""
    query = q.strip()
    if not query:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": "empty_query", "message": "Enter a search topic."})
    errors: Dict[str, str] = {}
    papers = _safe_panel(session, errors, "external", lambda: _paper_rows(session))
    ranked_papers = _rank(query, papers, lambda p: f"{p['title']} {p.get('title', '')} {p.get('abstract') or ''} {p.get('authors') or ''} {' '.join(p.get('keywords') or []) if isinstance(p.get('keywords'), (list, tuple)) else (p.get('keywords') or '')}")

    def library_save_counts():
        saved = session.exec(text("""
            SELECT paper_id, save_count FROM library_save_counts
        """)).all()
        return {str(r.paper_id): int(r.save_count) for r in saved}

    counts = _safe_panel(session, errors, "library", library_save_counts)
    external_matches, library_matches = partition_paper_results(ranked_papers, counts, limit)
    external = [_paper_item(p, score) for p, score in external_matches]
    library = [
        _paper_item(p, score, "library", _paper_save_count(p, counts))
        for p, score in library_matches
    ]

    def people_panel():
        members = [m for m in _member_rows(session) if str(m["id"]) != str(me.id)]
        ranked = _rank(query, members, lambda m: f"{m['name']} {m.get('department') or ''} {m.get('bio') or ''} {' '.join(m['interests'])}")
        results = []
        for m, score in ranked[:limit]:
            shared = [tag for tag in m["interests"] if _query_match(query, tag)]
            results.append(_member_item(m, score, shared))
        return results
    people = _safe_panel(session, errors, "people", people_panel)

    def posts_panel():
        posts = _post_rows(session)
        ranked = _rank(query, posts, lambda p: f"{p['title']} {p['title']} {p['body']} {' '.join(p['tags'])}")
        return [_post_item(p, score) for p, score in ranked[:limit]]
    posts = _safe_panel(session, errors, "posts", posts_panel)

    log_event(session, me.id, "search", query_text=query)
    session.commit()
    return {"query": query, "external": external, "library": library, "people": people, "posts": posts, "errors": errors}


@router.get("/recommend/papers")
def recommend_papers(
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Blend co-save recommendations with profile/content similarity; cold-start uses popular papers."""
    papers = _paper_rows(session)
    if not papers:
        return {"strategy": "popular", "items": []}
    saved_ids = [str(r[0]) for r in session.exec(text("SELECT paper_id FROM saves WHERE user_id = :uid"), params={"uid": me.id}).all()]
    interest_rows = session.exec(text("SELECT tag FROM user_interests WHERE user_id = :uid"), params={"uid": me.id}).all()
    interests = [r[0] for r in interest_rows]
    saved_set = set(saved_ids)
    count_rows = session.exec(text("SELECT paper_id, count(*) AS n FROM saves GROUP BY paper_id")).all()
    counts = {str(r.paper_id): int(r.n) for r in count_rows}
    candidates = [p for p in papers if not saved_set.intersection(_paper_member_ids(p))]

    if not saved_ids and not interests:
        department_counts: Dict[str, int] = {}
        if me.department:
            dept_rows = session.exec(text("""
                SELECT s.paper_id, count(DISTINCT s.user_id) AS n
                FROM saves s JOIN users u ON u.id = s.user_id
                WHERE u.department = :department AND u.id <> :uid
                GROUP BY s.paper_id
            """), params={"department": me.department, "uid": me.id}).all()
            department_counts = {str(r.paper_id): int(r.n) for r in dept_rows}
        popularity = department_counts or counts
        max_popularity = max(popularity.values(), default=1)
        ranked = sorted(candidates, key=lambda p: (sum(popularity.get(pid, 0) for pid in _paper_member_ids(p)), _paper_save_count(p, counts), p.get("year") or 0), reverse=True)
        return {"strategy": "popular", "items": [_paper_item(p, sum(popularity.get(pid, 0) for pid in _paper_member_ids(p)) / max_popularity, "paper", _paper_save_count(p, counts)) for p in ranked[:limit]]}

    query_parts = list(interests)
    if saved_ids:
        seed_text = " ".join(f"{p['title']} {p.get('abstract') or ''}" for p in papers if str(p["id"]) in saved_set)
        query_parts.append(seed_text)
    profile_query = " ".join(query_parts)
    content = dict((str(p["id"]), score) for p, score in _rank(profile_query, candidates, lambda p: f"{p['title']} {p['title']} {p.get('abstract') or ''} {p.get('authors') or ''} {' '.join(p.get('keywords') or []) if isinstance(p.get('keywords'), (list, tuple)) else (p.get('keywords') or '')}"))

    collaborative: Dict[str, int] = {}
    if saved_ids:
        rows = session.exec(text("""
            SELECT s2.paper_id, count(DISTINCT s2.user_id) AS support
            FROM saves s1 JOIN saves s2 ON s1.user_id = s2.user_id
            WHERE s1.user_id = :uid AND s2.user_id <> :uid
              AND s2.paper_id NOT IN (SELECT paper_id FROM saves WHERE user_id = :uid)
            GROUP BY s2.paper_id
        """), params={"uid": me.id}).all()
        collaborative = {str(r.paper_id): int(r.support) for r in rows}
    max_collab = max(collaborative.values(), default=1)
    ranked_items = []
    for p in candidates:
        pid = str(p["id"])
        collab_score = collaborative.get(pid, 0) / max_collab
        content_score = content.get(pid, 0.0)
        score = (0.65 * collab_score + 0.35 * content_score) if saved_ids else content_score
        if score > 0:
            ranked_items.append((p, score))
    ranked_items.sort(key=lambda pair: pair[1], reverse=True)
    if not ranked_items:
        ranked_items = sorted(candidates, key=lambda p: _paper_save_count(p, counts), reverse=True)[:limit]
        return {"strategy": "popular", "items": [_paper_item(p, 0.0, "paper", _paper_save_count(p, counts)) for p in ranked_items]}
    return {"strategy": "personalized", "items": [_paper_item(p, score, "paper", _paper_save_count(p, counts)) for p, score in ranked_items[:limit]]}


@router.get("/recommend/people")
def recommend_people(
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Recommend people by shared interests, department, and recent platform activity."""
    members = [m for m in _member_rows(session) if str(m["id"]) != str(me.id)]
    already = {str(r[0]) for r in session.exec(text("SELECT followee_id FROM follow_users WHERE follower_id = :uid"), params={"uid": me.id}).all()}
    members = [m for m in members if m["id"] not in already]
    my_tags = {r[0] for r in session.exec(text("SELECT tag FROM user_interests WHERE user_id = :uid"), params={"uid": me.id}).all()}
    activity_rows = session.exec(text("""
        SELECT author_id AS user_id, count(*) AS n FROM posts
        WHERE created_at >= now() - interval '30 days' GROUP BY author_id
    """)).all()
    activity = {str(r.user_id): int(r.n) for r in activity_rows}
    max_activity = max(activity.values(), default=1)
    personalized = bool(my_tags)
    ranked = []
    for m in members:
        shared = sorted(my_tags.intersection(m["interests"]))
        same_dept = bool(me.department and m.get("department") == me.department)
        if personalized:
            score = 0.65 * (len(shared) / max(1, len(my_tags))) + 0.25 * same_dept + 0.10 * (activity.get(m["id"], 0) / max_activity)
        else:
            # Cold start: show active members in the same department first, then other active members.
            score = 0.70 * same_dept + 0.30 * (activity.get(m["id"], 0) / max_activity)
        ranked.append((m, score, shared))
    ranked.sort(key=lambda x: (x[1], x[0]["name"].lower()), reverse=True)
    return {
        "strategy": "personalized" if personalized else "popular",
        "items": [_member_item(m, score, shared) for m, score, shared in ranked[:_limit(limit)]],
    }


@router.get("/papers/{paper_id}/also-saved")
def also_saved(
    paper_id: uuid.UUID,
    limit: int = Query(default=5, ge=1, le=20),
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Collaborative-filtering list: other papers saved by members who saved this paper."""
    current = session.exec(text("SELECT id FROM papers WHERE id = :pid"), params={"pid": paper_id}).first()
    if current is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "Paper not found."})
    rows = session.exec(text("""
        SELECT s2.paper_id, count(DISTINCT s2.user_id) AS support
        FROM saves s1 JOIN saves s2 ON s1.user_id = s2.user_id
        WHERE s1.paper_id = :pid AND s2.paper_id <> :pid
        GROUP BY s2.paper_id ORDER BY support DESC LIMIT :limit
    """), params={"pid": paper_id, "limit": _limit(limit, 20)}).all()
    docs_by_id: Dict[str, Dict[str, Any]] = {}
    for paper in _paper_rows(session):
        for member_id in _paper_member_ids(paper):
            docs_by_id[member_id] = paper
    support_by_paper: Dict[str, int] = {}
    counts_by_id: Dict[str, int] = {}
    for row in rows:
        paper = docs_by_id.get(str(row.paper_id))
        if paper:
            paper_id = str(paper["id"])
            support_by_paper[paper_id] = support_by_paper.get(paper_id, 0) + int(row.support)
            counts_by_id[str(row.paper_id)] = int(row.support)
    max_support = max(support_by_paper.values(), default=1)
    items = []
    for paper_id, support in sorted(support_by_paper.items(), key=lambda item: item[1], reverse=True):
        paper = docs_by_id[paper_id]
        items.append(_paper_item(paper, support / max_support, "paper", _paper_save_count(paper, counts_by_id)))
    return {"items": items}


@router.get("/trends")
def trends(
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=20, ge=1, le=50),
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Compare topic activity in the latest window with the preceding equal window."""
    rows = session.exec(text("""
        WITH hits AS (
            SELECT lower(trim(target_tag)) AS tag,
                   count(*) FILTER (WHERE created_at >= now() - (:days * interval '1 day')) AS current_count,
                   count(*) FILTER (WHERE created_at < now() - (:days * interval '1 day')) AS previous_count
            FROM events
            WHERE target_type = 'topic' AND target_tag IS NOT NULL AND trim(target_tag) <> ''
              AND created_at >= now() - ((:days * 2) * interval '1 day')
            GROUP BY lower(trim(target_tag))
            UNION ALL
            SELECT lower(trim(pt.tag)) AS tag,
                   count(*) FILTER (WHERE p.created_at >= now() - (:days * interval '1 day')) AS current_count,
                   count(*) FILTER (WHERE p.created_at < now() - (:days * interval '1 day')) AS previous_count
            FROM post_tags pt JOIN posts p ON p.id = pt.post_id
            WHERE p.created_at >= now() - ((:days * 2) * interval '1 day')
            GROUP BY lower(trim(pt.tag))
        )
        SELECT tag, sum(current_count) AS current_count, sum(previous_count) AS previous_count
        FROM hits GROUP BY tag HAVING sum(current_count) > 0 ORDER BY current_count DESC LIMIT :limit
    """), params={"days": days, "limit": _limit(limit, 50)}).all()
    items = []
    for r in rows:
        current, previous = int(r.current_count or 0), int(r.previous_count or 0)
        change = round(((current - previous) / previous) * 100.0, 1) if previous else (100.0 if current else 0.0)
        spike = current >= 3 and (previous == 0 or (current >= previous * 1.5 and current - previous >= 2))
        items.append({"tag": r.tag, "count": current, "change_pct": change, "is_spike": spike})
    return {"items": items}


@router.get("/admin/flags")
def admin_flags(
    limit: int = Query(default=50, ge=1, le=100),
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin),
):
    """Flag high-rate posting, link spam, mass upvotes/follows, and repeated titles."""
    rows = session.exec(text("""
        WITH activity AS (
            SELECT user_id, count(*) AS total_events,
                   count(*) FILTER (WHERE event_type IN ('post', 'comment')) AS content_events,
                   max(created_at) AS last_event
            FROM events
            WHERE created_at >= now() - interval '7 days' AND user_id IS NOT NULL
            GROUP BY user_id
        ), repeated AS (
            SELECT author_id AS user_id, max(n) AS repeat_count, max(last_post) AS last_post
            FROM (
                SELECT author_id, lower(regexp_replace(trim(title), '\\s+', ' ', 'g')) AS normalized_title,
                       count(*) AS n, max(created_at) AS last_post
                FROM posts WHERE created_at >= now() - interval '30 days'
                GROUP BY author_id, lower(regexp_replace(trim(title), '\\s+', ' ', 'g'))
            ) t WHERE n >= 3 GROUP BY author_id
        ), link_bursts AS (
            SELECT p.author_id AS user_id, max(burst.n) AS link_burst_count,
                   max(p.created_at) AS last_post
            FROM posts p
            CROSS JOIN LATERAL (
                SELECT count(*) AS n
                FROM posts p2
                WHERE p2.author_id = p.author_id
                  AND lower(substring(p2.body FROM '(https?://[^[:space:]]+)')) =
                      lower(substring(p.body FROM '(https?://[^[:space:]]+)'))
                  AND substring(p.body FROM '(https?://[^[:space:]]+)') IS NOT NULL
                  AND p2.created_at BETWEEN p.created_at AND p.created_at + interval '1 hour'
            ) burst
            WHERE p.created_at >= now() - interval '7 days'
            GROUP BY p.author_id
        ), upvote_bursts AS (
            SELECT u1.user_id, max(burst.n) AS upvote_burst_count
            FROM upvotes u1
            CROSS JOIN LATERAL (
                SELECT count(*) AS n FROM upvotes u2
                WHERE u2.user_id = u1.user_id
                  AND u2.created_at BETWEEN u1.created_at AND u1.created_at + interval '1 hour'
            ) burst
            WHERE u1.created_at >= now() - interval '7 days'
            GROUP BY u1.user_id
        ), follow_activity AS (
            SELECT follower_id AS user_id, created_at FROM follow_users
            UNION ALL SELECT user_id, created_at FROM follow_topics
        ), follow_bursts AS (
            SELECT f1.user_id, max(burst.n) AS follow_burst_count
            FROM follow_activity f1
            CROSS JOIN LATERAL (
                SELECT count(*) AS n FROM follow_activity f2
                WHERE f2.user_id = f1.user_id
                  AND f2.created_at BETWEEN f1.created_at AND f1.created_at + interval '10 minutes'
            ) burst
            WHERE f1.created_at >= now() - interval '7 days'
            GROUP BY f1.user_id
        )
        SELECT u.id AS user_id, u.name, coalesce(a.total_events, 0) AS total_events,
               coalesce(a.content_events, 0) AS content_events,
               coalesce(r.repeat_count, 0) AS repeat_count,
               coalesce(l.link_burst_count, 0) AS link_burst_count,
               coalesce(v.upvote_burst_count, 0) AS upvote_burst_count,
               coalesce(f.follow_burst_count, 0) AS follow_burst_count,
               greatest(a.last_event, r.last_post, l.last_post) AS flagged_at
        FROM users u LEFT JOIN activity a ON a.user_id = u.id
        LEFT JOIN repeated r ON r.user_id = u.id
        LEFT JOIN link_bursts l ON l.user_id = u.id
        LEFT JOIN upvote_bursts v ON v.user_id = u.id
        LEFT JOIN follow_bursts f ON f.user_id = u.id
        WHERE coalesce(a.total_events, 0) >= 40
           OR coalesce(a.content_events, 0) >= 12
           OR coalesce(r.repeat_count, 0) >= 3
           OR coalesce(l.link_burst_count, 0) >= 10
           OR coalesce(v.upvote_burst_count, 0) >= 20
           OR coalesce(f.follow_burst_count, 0) >= 20
        ORDER BY coalesce(l.link_burst_count, 0) DESC,
                 coalesce(v.upvote_burst_count, 0) DESC,
                 coalesce(f.follow_burst_count, 0) DESC,
                 coalesce(r.repeat_count, 0) DESC,
                 coalesce(a.total_events, 0) DESC
        LIMIT :limit
    """), params={"limit": _limit(limit, 100)}).all()
    items = []
    for r in rows:
        reasons = []
        if r.repeat_count >= 3:
            reasons.append(f"Repeated the same post title {int(r.repeat_count)} times in 30 days")
        if r.content_events >= 12:
            reasons.append(f"High posting/comment activity ({int(r.content_events)} events in 7 days)")
        if r.total_events >= 40:
            reasons.append(f"Unusually high activity ({int(r.total_events)} events in 7 days)")
        if r.link_burst_count >= 10:
            reasons.append(f"Repeated the same link in {int(r.link_burst_count)} posts within an hour")
        if r.upvote_burst_count >= 20:
            reasons.append(f"Unusually many upvotes ({int(r.upvote_burst_count)} within an hour)")
        if r.follow_burst_count >= 20:
            reasons.append(f"Unusually many follows ({int(r.follow_burst_count)} within 10 minutes)")
        score = min(1.0, max(float(r.repeat_count) / 5.0, float(r.content_events) / 24.0,
                             float(r.total_events) / 80.0, float(r.link_burst_count) / 30.0,
                             float(r.upvote_burst_count) / 50.0, float(r.follow_burst_count) / 50.0))
        flagged_at = r.flagged_at.isoformat() if r.flagged_at else datetime.now(timezone.utc).isoformat()
        items.append({"user_id": str(r.user_id), "name": r.name, "reason": "; ".join(reasons), "score": round(score, 3), "flagged_at": flagged_at})
    return {"items": items}


@router.get("/admin/duplicates")
def admin_duplicate_candidates(
    threshold: float = Query(default=0.78, ge=0.0, le=1.0),
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin),
):
    """Show MinHash/LSH candidates after exact Jaccard verification."""
    pairs = find_near_duplicates(_paper_rows(session, deduplicate=False), threshold=threshold)
    return {"threshold": threshold, "algorithm": "MinHash + LSH + exact Jaccard", "items": pairs[:_limit(limit, 500)]}

def _sentences(text_value: str) -> List[str]:
    # Some harvested abstracts omit spaces after sentence punctuation. Split on
    # those boundaries too so Ask does not return an entire abstract as one quote.
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+|(?<=[.!?])(?=[A-Z])", text_value or "")
        if len(sentence.strip()) > 20
    ]


@router.post("/ask")
def ask_research_assistant(
    data: Dict[str, str],
    limit: int = Query(default=5, ge=1, le=10),
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Extract answer passages from stored abstracts and return verifiable citations."""
    question = (data.get("question") or "").strip()
    if not question:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": "empty_question", "message": "Enter a research question."})
    papers = [
        paper for paper in _paper_rows(session)
        if paper.get("abstract") and not is_catalog_description(paper)
    ]
    ranked = _rank(question, papers, lambda p: f"{p['title']} {p.get('abstract') or ''}")[:_limit(limit, 10)]
    findings = []
    for paper, paper_score in ranked:
        sentences = _sentences(paper.get("abstract") or "")
        if not sentences:
            continue
        sentence_scores = _tfidf_scores(question, sentences)
        best_index = max(range(len(sentences)), key=lambda i: sentence_scores[i])
        passage_score = max(sentence_scores[best_index], paper_score * 0.75)
        if passage_score <= 0:
            continue
        findings.append({
            "paper": paper,
            "text": sentences[best_index],
            "score": passage_score,
        })
    selected = select_evidence_findings(findings)
    citations, passages = [], []
    for number, finding in enumerate(selected, start=1):
        finding["n"] = number
        paper = finding["paper"]
        pid = str(paper["id"])
        citations.append({"n": number, "paper_id": pid, "title": paper["title"], "url": _paper_url(paper)})
        passages.append({"n": number, "paper_id": pid, "text": finding["text"], "score": round(finding["score"], 4)})
    answer = compose_evidence_answer(selected)
    return {"answer": answer, "citations": citations, "passages": passages}






