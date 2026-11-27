"""Add paper links to synthetic discussions without deleting or editing rows.

Run from the backend container after importing the paper catalog and generating
synthetic data: `python link_synthetic_discussions.py`. The operation is
idempotent and only links synthetic users' tagged posts to papers whose title,
abstract, or keywords contain the post tag.
"""
from __future__ import annotations

import os
import re

import psycopg


def main() -> None:
    database_url = os.environ["DATABASE_URL"].replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    with psycopg.connect(database_url) as conn:
        papers = conn.execute("""
            SELECT id, title, abstract, keywords
            FROM papers
            WHERE COALESCE(source_record_id, '') NOT LIKE 'synthetic-dedup-%'
            ORDER BY id
        """).fetchall()
        posts = conn.execute("""
            SELECT p.id, pt.tag
            FROM posts p
            JOIN users u ON u.id = p.author_id
            JOIN post_tags pt ON pt.post_id = p.id
            LEFT JOIN post_papers pp ON pp.post_id = p.id
            WHERE u.email LIKE 'synthetic_%@researchcommons.demo'
              AND pp.post_id IS NULL
            ORDER BY p.id, pt.tag
        """).fetchall()

        records = []
        normalized_papers = []
        for paper_id, title, abstract, keywords in papers:
            text = " ".join((title or "", abstract or "", " ".join(keywords or []))).lower()
            normalized_papers.append((paper_id, text))
        for post_id, tag in posts:
            normalized_tag = " ".join(re.findall(r"[a-z0-9]+", (tag or "").lower()))
            if not normalized_tag:
                continue
            matches = [paper_id for paper_id, searchable in normalized_papers
                       if normalized_tag in searchable]
            if matches:
                records.append((post_id, matches[0]))

        if records:
            conn.cursor().executemany("""
                INSERT INTO post_papers (post_id, paper_id)
                VALUES (%s, %s) ON CONFLICT DO NOTHING
            """, records)
        conn.commit()
    print(f"Added {len(records)} topic-matched synthetic post-paper links.")
    print("No existing posts, papers, or interactions were changed or deleted.")


if __name__ == "__main__":
    main()
