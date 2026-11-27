"""Batch-ingest OpenAlex works and curated RSS stories into PostgreSQL/MinIO.

Run once with `python -m app.ingest_external --openalex-limit 500`, or keep the
optional Compose ingestion profile running with `--interval-hours 24`.
OpenAlex response bodies and complete RSS documents are stored unchanged in
MinIO; normalized paper, author, and source rows are upserted idempotently.
"""
from __future__ import annotations

import argparse
import email.utils
import html
import io
import json
import os
import re
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import httpx
from minio import Minio
from sqlalchemy import text
from sqlmodel import Session

from app.db import engine


OPENALEX_URL = "https://api.openalex.org/works"
OPENALEX_QUERIES = (
    "artificial intelligence", "machine learning", "data science",
    "cybersecurity", "cloud computing", "software engineering",
    "computer networks", "natural language processing",
)
OPENALEX_SELECT = ",".join((
    "id", "doi", "title", "publication_year", "publication_date",
    "abstract_inverted_index", "authorships", "primary_location", "keywords",
    "referenced_works",
))
RSS_FEEDS = (
    ("MIT News Research", "https://news.mit.edu/rss/research"),
    ("MIT News AI", "https://news.mit.edu/rss/topic/artificial-intelligence2"),
)


def _minio_client() -> Tuple[Minio, str]:
    endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
    access = os.environ["MINIO_ACCESS_KEY"]
    secret = os.environ["MINIO_SECRET_KEY"]
    bucket = os.getenv("MINIO_BUCKET", "research-commons")
    client = Minio(endpoint, access_key=access, secret_key=secret,
                   secure=os.getenv("MINIO_SECURE", "false").lower() == "true")
    for attempt in range(30):
        try:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
            return client, bucket
        except Exception:
            if attempt == 29:
                raise
            time.sleep(2)
    raise RuntimeError("MinIO did not become available")


def _store_raw(client: Minio, bucket: str, key: str, body: bytes, content_type: str) -> None:
    client.put_object(bucket, key, io.BytesIO(body), len(body), content_type=content_type)


def _abstract_from_openalex(work: Dict[str, Any]) -> Optional[str]:
    inverted = work.get("abstract_inverted_index")
    if not inverted:
        return None
    words = sorted((int(position), word) for word, positions in inverted.items() for position in positions)
    return " ".join(word for _, word in words) or None


def _work_authors(work: Dict[str, Any]) -> List[Tuple[str, Optional[str]]]:
    authors = []
    for authorship in work.get("authorships") or []:
        author = authorship.get("author") or {}
        name = author.get("display_name")
        if not name:
            continue
        institutions = authorship.get("institutions") or []
        affiliation = "; ".join(i.get("display_name", "") for i in institutions if i.get("display_name")) or None
        authors.append((name, affiliation))
    return authors


def _work_metadata(work: Dict[str, Any]) -> Dict[str, Any]:
    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    doi = (work.get("doi") or "").replace("https://doi.org/", "") or None
    publication_date = work.get("publication_date")
    try:
        published_at = date.fromisoformat(publication_date) if publication_date else None
    except ValueError:
        published_at = None
    return {
        "title": work.get("title") or "Untitled research work",
        "abstract": _abstract_from_openalex(work),
        "doi": doi,
        "url": location.get("landing_page_url") or work.get("id"),
        "publication_year": work.get("publication_year"),
        "published_at": published_at,
        "venue": source.get("display_name"),
        "publisher": source.get("host_organization_name"),
        "source_record_id": work.get("id"),
        "keywords": [k.get("display_name") for k in work.get("keywords") or [] if k.get("display_name")],
    }


def _find_paper_id(session: Session, meta: Dict[str, Any]) -> Optional[uuid.UUID]:
    if meta.get("source_record_id"):
        found = session.exec(text("SELECT id FROM papers WHERE source_record_id = :source_id LIMIT 1"),
                             params={"source_id": meta["source_record_id"]}).first()
        if found:
            return found.id
    if meta.get("doi"):
        found = session.exec(text("SELECT id FROM papers WHERE lower(doi) = lower(:doi) LIMIT 1"),
                             params={"doi": meta["doi"]}).first()
        if found:
            return found.id
    if meta.get("url"):
        found = session.exec(text("SELECT id FROM papers WHERE url = :url LIMIT 1"),
                             params={"url": meta["url"]}).first()
        if found:
            return found.id
    return None


def _upsert_work(session: Session, work: Dict[str, Any], source_name: str = "OpenAlex") -> bool:
    meta = _work_metadata(work)
    paper_id = _find_paper_id(session, meta)
    if paper_id is None:
        paper_id = session.exec(text("""
            INSERT INTO papers
                (title, abstract, keywords, doi, url, publication_year, published_at,
                 venue, publisher, source, source_record_id)
            VALUES
                (:title, :abstract, :keywords, :doi, :url, :publication_year, :published_at,
                 :venue, :publisher, :source, :source_record_id)
            RETURNING id
        """), params={**meta, "source": source_name}).one().id
    else:
        # Backfill identifiers and metadata only when missing; never overwrite a
        # curated title or abstract during an incremental refresh.
        session.exec(text("""
            UPDATE papers SET
                source_record_id = COALESCE(source_record_id, :source_record_id),
                doi = COALESCE(doi, :doi),
                keywords = COALESCE(keywords, :keywords),
                updated_at = now()
            WHERE id = :paper_id
        """), params={**meta, "paper_id": paper_id})

    authors = _work_authors(work)
    existing_authors = session.exec(text("SELECT COUNT(*) FROM paper_authors WHERE paper_id = :id"),
                                    params={"id": paper_id}).one()[0]
    if not existing_authors:
        for position, (name, affiliation) in enumerate(authors, 1):
            normalized = " ".join(re.findall(r"[a-z0-9]+", name.lower()))
            session.exec(text("""
                INSERT INTO paper_authors (paper_id, author_name, normalized_name, affiliation, author_position)
                VALUES (:paper_id, :name, :normalized, :affiliation, :position)
            """), params={"paper_id": paper_id, "name": name, "normalized": normalized,
                          "affiliation": affiliation, "position": position})

    raw_json = json.dumps(work, ensure_ascii=False)
    source_row = session.exec(text("""
        SELECT id FROM paper_sources
        WHERE paper_id = :paper_id AND source_name = :source AND source_record_id = :source_id
        LIMIT 1
    """), params={"paper_id": paper_id, "source": source_name,
                   "source_id": meta["source_record_id"]}).first()
    if source_row:
        session.exec(text("""
            UPDATE paper_sources SET raw_metadata = CAST(:raw AS JSONB), fetched_at = now()
            WHERE id = :id
        """), params={"raw": raw_json, "id": source_row.id})
    else:
        session.exec(text("""
            INSERT INTO paper_sources
                (paper_id, source_name, source_record_id, source_url, raw_metadata, fetched_at)
            VALUES (:paper_id, :source, :source_id, :source_url, CAST(:raw AS JSONB), now())
        """), params={"paper_id": paper_id, "source": source_name,
                      "source_id": meta["source_record_id"], "source_url": meta["url"], "raw": raw_json})
    return True


def _ingest_openalex(client: httpx.Client, storage: Minio, bucket: str,
                     run_id: str, limit: int) -> int:
    if limit <= 0:
        return 0
    target_each = max(1, (limit + len(OPENALEX_QUERIES) - 1) // len(OPENALEX_QUERIES))
    works_by_id: Dict[str, Dict[str, Any]] = {}
    for query in OPENALEX_QUERIES:
        cursor = "*"
        query_count = 0
        batch = 0
        while query_count < target_each and len(works_by_id) < limit:
            page_size = min(100, target_each - query_count)
            response = client.get(OPENALEX_URL, params={
                "search": query, "filter": "type:article", "sort": "publication_date:desc",
                "per-page": page_size, "cursor": cursor, "select": OPENALEX_SELECT,
                "mailto": os.getenv("OPENALEX_MAILTO", "research-commons@example.org"),
            })
            response.raise_for_status()
            batch += 1
            _store_raw(storage, bucket, f"raw/openalex/{run_id}/{query.replace(' ', '-')}-{batch:03d}.json",
                       response.content, response.headers.get("content-type", "application/json"))
            payload = response.json()
            results = payload.get("results") or []
            if not results:
                break
            for work in results:
                work_id = work.get("id")
                if work_id:
                    works_by_id.setdefault(work_id, work)
            query_count += len(results)
            cursor = (payload.get("meta") or {}).get("next_cursor")
            if not cursor:
                break
    selected = list(works_by_id.values())[:limit]
    inserted = 0
    with Session(engine) as session:
        for work in selected:
            _upsert_work(session, work)
            inserted += 1
        session.commit()
    return inserted


class _TextOnly(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []

    def handle_data(self, data: str) -> None:
        cleaned = " ".join(data.split())
        if cleaned:
            self.parts.append(cleaned)


def _strip_html(value: str) -> str:
    parser = _TextOnly()
    parser.feed(html.unescape(value))
    return " ".join(parser.parts)


def _entry_data(entry: ET.Element) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for child in list(entry):
        name = child.tag.rsplit("}", 1)[-1].lower()
        if name == "link":
            values.setdefault("link", child.attrib.get("href") or (child.text or "").strip())
        elif name in {"title", "description", "summary", "published", "updated", "pubdate", "content"}:
            values.setdefault(name, "".join(child.itertext()).strip())
    values["link"] = values.get("link", "")
    return values


def _published_date(value: str) -> Optional[date]:
    if not value:
        return None
    try:
        return email.utils.parsedate_to_datetime(value).date()
    except (TypeError, ValueError, OverflowError):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None


def _ingest_rss(client: httpx.Client, storage: Minio, bucket: str,
                run_id: str, per_feed: int) -> int:
    total = 0
    for feed_name, feed_url in RSS_FEEDS:
        response = client.get(feed_url)
        response.raise_for_status()
        safe_name = re.sub(r"[^a-z0-9]+", "-", feed_name.lower()).strip("-")
        _store_raw(storage, bucket, f"raw/rss/{run_id}/{safe_name}.xml",
                   response.content, response.headers.get("content-type", "application/xml"))
        root = ET.fromstring(response.content)
        entries = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1].lower() in {"item", "entry"}]
        with Session(engine) as session:
            for entry in entries[:per_feed]:
                item = _entry_data(entry)
                title = _strip_html(item.get("title", ""))
                url = item.get("link", "").strip()
                summary = _strip_html(item.get("summary") or item.get("description") or item.get("content") or "")
                if not title or not url:
                    continue
                published = _published_date(item.get("published") or item.get("updated") or item.get("pubdate", ""))
                existing = session.exec(text("""
                    SELECT id FROM papers WHERE url = :url OR source_record_id = :url LIMIT 1
                """), params={"url": url}).first()
                if existing:
                    continue
                paper_id = session.exec(text("""
                    INSERT INTO papers (title, abstract, url, publication_year, published_at, source, source_record_id)
                    VALUES (:title, :abstract, :url, :year, :published, :source, :source_id)
                    RETURNING id
                """), params={"title": title, "abstract": summary[:8000] or None, "url": url,
                              "year": published.year if published else None, "published": published,
                              "source": feed_name, "source_id": url}).one().id
                metadata = json.dumps({"feed": feed_url, "title": title, "url": url, **item}, ensure_ascii=False)
                session.exec(text("""
                    INSERT INTO paper_sources
                        (paper_id, source_name, source_record_id, source_url, raw_metadata, fetched_at)
                    VALUES (:paper_id, :source, :source_id, :url, CAST(:raw AS JSONB), now())
                """), params={"paper_id": paper_id, "source": feed_name, "source_id": url,
                              "url": url, "raw": metadata})
                total += 1
            session.commit()
    return total


def ingest_once(openalex_limit: int, rss_limit: int) -> None:
    storage, bucket = _minio_client()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with httpx.Client(timeout=45, follow_redirects=True,
                      headers={"User-Agent": "ChanakyaScholarSphere/1.0 (academic course project)"}) as client:
        openalex_count = _ingest_openalex(client, storage, bucket, run_id, openalex_limit)
        rss_count = _ingest_rss(client, storage, bucket, run_id, rss_limit)
    print(f"Batch complete: {openalex_count} OpenAlex works processed; {rss_count} new RSS stories inserted.")
    print(f"Unmodified source payloads stored in MinIO bucket '{bucket}' under raw/openalex/ and raw/rss/.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openalex-limit", type=int, default=100,
                        help="maximum distinct OpenAlex works per batch (0 disables it)")
    parser.add_argument("--rss-limit", type=int, default=20,
                        help="maximum new stories per feed in each batch (0 disables RSS)")
    parser.add_argument("--interval-hours", type=float, default=0,
                        help="repeat this batch on a fixed interval; 0 runs exactly once")
    args = parser.parse_args()
    if args.openalex_limit < 0 or args.rss_limit < 0 or args.interval_hours < 0:
        parser.error("limits and interval must be non-negative")
    while True:
        try:
            ingest_once(args.openalex_limit, args.rss_limit)
        except Exception as exc:
            print(f"Ingestion batch failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            if not args.interval_hours:
                raise SystemExit(1) from exc
        if not args.interval_hours:
            break
        time.sleep(args.interval_hours * 3600)


if __name__ == "__main__":
    main()
