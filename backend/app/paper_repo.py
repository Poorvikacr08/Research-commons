"""
ALL reads/writes of Member 2's papers table go through this file.

The rest of the app only uses the functions below and the PaperOut shape.
If Member 2's papers / paper_authors columns change, change ONLY the SQL in this file.

Matches Member 2's schema in db/init/02_papers.sql:
  papers(id, title, abstract, doi, arxiv_id, url, publication_year, source, ...)
  paper_authors(paper_id, author_name, normalized_name, author_position, ...)
"""
import re
import uuid
from typing import List, Optional

import httpx
from pydantic import BaseModel
from sqlalchemy import bindparam, text
from sqlmodel import Session


class PaperOut(BaseModel):
    id: str
    title: str
    abstract: Optional[str] = None
    authors: Optional[str] = None      # "A. Author, B. Author"
    year: Optional[int] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None


# authors are stored one per row in paper_authors; join them into "A, B, C" in author order
PAPER_SELECT = """
    SELECT p.id, p.title, p.abstract,
           (SELECT string_agg(a.author_name, ', ' ORDER BY a.author_position NULLS LAST, a.author_name)
              FROM paper_authors a WHERE a.paper_id = p.id) AS authors,
           p.publication_year AS year, p.doi, p.arxiv_id, p.url, p.source
    FROM papers p
"""


def _row_to_paper(r) -> PaperOut:
    return PaperOut(
        id=str(r.id), title=r.title, abstract=r.abstract, authors=r.authors, year=r.year,
        doi=r.doi, arxiv_id=r.arxiv_id, url=r.url, source=r.source,
    )


def get_papers(session: Session, ids: List[uuid.UUID]) -> List[PaperOut]:
    """Papers by id, in the same order as ids (missing ones are skipped)."""
    if not ids:
        return []
    stmt = text(PAPER_SELECT + " WHERE p.id IN :ids").bindparams(bindparam("ids", expanding=True))
    found = {r.id: _row_to_paper(r) for r in session.exec(stmt, params={"ids": list(ids)})}
    return [found[i] for i in ids if i in found]


def get_paper(session: Session, paper_id: uuid.UUID) -> Optional[PaperOut]:
    papers = get_papers(session, [paper_id])
    return papers[0] if papers else None


def search_papers(session: Session, q: str, limit: int = 20) -> List[PaperOut]:
    """Simple title search, used by the 'attach a paper' picker (Member 3 owns real search)."""
    stmt = text(PAPER_SELECT + " WHERE p.title ILIKE :q ORDER BY p.publication_year DESC NULLS LAST LIMIT :limit")
    return [_row_to_paper(r) for r in session.exec(stmt, params={"q": f"%{q}%", "limit": limit})]


# ---------- save by URL / DOI / arXiv ID ----------
DOI_RE = re.compile(r"(10\.\d{4,9}/[^\s?#]+)", re.I)
ARXIV_RE = re.compile(r"(?:arxiv\.org/(?:abs|pdf)/|arxiv:)?(\d{4}\.\d{4,5})(v\d+)?", re.I)


def parse_identifier(value: str) -> dict:
    """'https://doi.org/10.1/abc' -> {'doi': '10.1/abc'}; 'arXiv:1706.03762' -> {'arxiv_id': '1706.03762'}"""
    value = value.strip()
    arxiv = ARXIV_RE.search(value)
    if arxiv and ("arxiv" in value.lower() or re.fullmatch(r"\d{4}\.\d{4,5}(v\d+)?", value)):
        return {"arxiv_id": arxiv.group(1)}
    doi = DOI_RE.search(value)
    if doi:
        return {"doi": doi.group(1).rstrip(".").lower()}
    if value.startswith("http"):
        return {"url": value}
    return {}


def find_by_identifier(session: Session, ident: dict) -> Optional[PaperOut]:
    if "doi" in ident:
        where, val = "lower(p.doi) = :v OR lower(p.doi) LIKE '%' || :v", ident["doi"]
    elif "arxiv_id" in ident:
        where, val = "p.arxiv_id = :v OR p.url ILIKE '%' || :v || '%'", ident["arxiv_id"]
    elif "url" in ident:
        where, val = "p.url = :v", ident["url"]
    else:
        return None
    row = session.exec(text(PAPER_SELECT + f" WHERE {where} LIMIT 1"), params={"v": val}).first()
    return _row_to_paper(row) if row else None


def fetch_from_openalex(ident: dict) -> Optional[dict]:
    """Look up a paper that is not in our database yet (free OpenAlex API)."""
    if "doi" in ident:
        key = f"doi:{ident['doi']}"
    elif "arxiv_id" in ident:
        key = f"doi:10.48550/arxiv.{ident['arxiv_id']}"   # arXiv papers have DOIs of this form
    else:
        return None
    try:
        r = httpx.get(f"https://api.openalex.org/works/{key}", timeout=10, params={"mailto": "research-commons@example.org"})
        if r.status_code != 200:
            return None
        w = r.json()
    except httpx.HTTPError:
        return None

    abstract = None
    inv = w.get("abstract_inverted_index")
    if inv:  # OpenAlex stores abstracts as {word: [positions]}
        words = sorted((pos, word) for word, positions in inv.items() for pos in positions)
        abstract = " ".join(word for _, word in words)
    authors = ", ".join(a["author"]["display_name"] for a in w.get("authorships", [])[:8] if a.get("author"))
    doi = (w.get("doi") or "").replace("https://doi.org/", "") or None
    return {
        "title": w.get("title") or w.get("display_name") or "Untitled",
        "abstract": abstract, "authors": authors or None, "year": w.get("publication_year"),
        "doi": doi, "arxiv_id": ident.get("arxiv_id"),
        "url": (w.get("primary_location") or {}).get("landing_page_url") or w.get("id"),
        "source": "openalex",
    }


def insert_paper(session: Session, meta: dict) -> PaperOut:
    """Add a paper saved by a member (row in papers + one row per author in paper_authors)."""
    row = session.exec(text("""
        INSERT INTO papers (title, abstract, publication_year, doi, arxiv_id, url, source)
        VALUES (:title, :abstract, :year, :doi, :arxiv_id, :url, :source)
        RETURNING id
    """), params={k: meta.get(k) for k in ("title", "abstract", "year", "doi", "arxiv_id", "url", "source")}).one()
    names = [n.strip() for n in (meta.get("authors") or "").split(",") if n.strip()]
    for position, name in enumerate(names, start=1):
        session.exec(text("""
            INSERT INTO paper_authors (paper_id, author_name, normalized_name, author_position)
            VALUES (:paper_id, :name, :normalized, :position)
        """), params={"paper_id": row.id, "name": name, "normalized": name.lower(), "position": position})
    return get_paper(session, row.id)
