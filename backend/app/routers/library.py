"""F3 library: save papers, personal collections with private notes, the shared Chanakya library."""
import uuid
from datetime import datetime
from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, text
from sqlmodel import Session, select

from app import paper_repo
from app.auth import get_current_user
from app.db import get_session
from app.events import log_event
from app.models import Collection, CollectionItem, Save, User
from app.paper_repo import PaperOut

router = APIRouter(tags=["library"])


# ---------- shapes ----------
class LibraryPaper(PaperOut):
    save_count: int = 0           # how many members saved it
    is_saved: bool = False        # did I save it
    saved_at: Optional[datetime] = None


class CollectionRef(BaseModel):
    id: str
    name: str


class PaperDetail(LibraryPaper):
    my_collections: List[CollectionRef]     # my collections that contain this paper
    my_notes: Dict[str, Optional[str]]      # collection id -> my private note


class SaveIn(BaseModel):
    paper_id: Optional[uuid.UUID] = None
    identifier: Optional[str] = None        # URL, DOI or arXiv ID


class CollectionIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class CollectionOut(BaseModel):
    id: str
    name: str
    item_count: int
    created_at: datetime


class CollectionItemOut(LibraryPaper):
    note: Optional[str] = None
    added_at: datetime


class CollectionDetail(CollectionOut):
    items: List[CollectionItemOut]


class ItemIn(BaseModel):
    paper_id: uuid.UUID
    note: Optional[str] = None


class NoteIn(BaseModel):
    note: Optional[str] = None


class ChanakyaLibraryOut(BaseModel):
    total_papers: int
    items: List[LibraryPaper]


# ---------- helpers ----------
def not_found(what: str):
    return HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": f"{what} not found."})


def save_counts(session: Session, paper_ids) -> Dict[uuid.UUID, int]:
    if not paper_ids:
        return {}
    return dict(session.exec(
        select(Save.paper_id, func.count()).where(Save.paper_id.in_(list(paper_ids))).group_by(Save.paper_id)
    ).all())


def my_saves(session: Session, me: User, paper_ids=None) -> Dict[uuid.UUID, datetime]:
    stmt = select(Save.paper_id, Save.saved_at).where(Save.user_id == me.id)
    if paper_ids is not None:
        stmt = stmt.where(Save.paper_id.in_(list(paper_ids)))
    return dict(session.exec(stmt).all())


def enrich(session: Session, papers: List[PaperOut], me: User) -> List[LibraryPaper]:
    ids = [uuid.UUID(p.id) for p in papers]
    counts, mine = save_counts(session, ids), my_saves(session, me, ids)
    return [
        LibraryPaper(**p.model_dump(), save_count=counts.get(uuid.UUID(p.id), 0),
                     is_saved=uuid.UUID(p.id) in mine, saved_at=mine.get(uuid.UUID(p.id)))
        for p in papers
    ]


def save_paper_for(session: Session, me: User, paper_id: uuid.UUID) -> None:
    """Save once per member (the database also enforces this with UNIQUE)."""
    exists = session.exec(select(Save).where(Save.user_id == me.id, Save.paper_id == paper_id)).first()
    if not exists:
        session.add(Save(user_id=me.id, paper_id=paper_id))
        log_event(session, me.id, "save", "paper", target_id=paper_id)


def my_collection_or_404(session: Session, me: User, collection_id: uuid.UUID) -> Collection:
    c = session.get(Collection, collection_id)
    if c is None or c.user_id != me.id:     # other people's collections are private
        raise not_found("Collection")
    return c


# ---------- papers ----------
@router.get("/papers", response_model=List[LibraryPaper])
def find_papers(q: str = "", limit: int = 20, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    """Title search used by the 'attach a paper' picker."""
    return enrich(session, paper_repo.search_papers(session, q.strip(), min(limit, 50)), me)


@router.get("/papers/{paper_id}", response_model=PaperDetail)
def paper_detail(paper_id: uuid.UUID, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    paper = paper_repo.get_paper(session, paper_id)
    if paper is None:
        raise not_found("Paper")
    log_event(session, me.id, "view", "paper", target_id=paper_id)
    session.commit()
    rows = session.exec(
        select(Collection, CollectionItem.note)
        .join(CollectionItem, CollectionItem.collection_id == Collection.id)
        .where(Collection.user_id == me.id, CollectionItem.paper_id == paper_id)
    ).all()
    return PaperDetail(
        **enrich(session, [paper], me)[0].model_dump(),
        my_collections=[CollectionRef(id=str(c.id), name=c.name) for c, _ in rows],
        my_notes={str(c.id): note for c, note in rows},
    )


# ---------- saving ----------
@router.post("/library/save", response_model=LibraryPaper)
def save(data: SaveIn, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    """Save by paper_id (from search results) or by identifier (URL / DOI / arXiv ID)."""
    if data.paper_id:
        paper = paper_repo.get_paper(session, data.paper_id)
        if paper is None:
            raise not_found("Paper")
    elif data.identifier and data.identifier.strip():
        ident = paper_repo.parse_identifier(data.identifier)
        if not ident:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={
                "code": "bad_identifier", "message": "Enter a paper URL, a DOI (10.xxxx/…) or an arXiv ID (e.g. 1706.03762)."})
        paper = paper_repo.find_by_identifier(session, ident)
        if paper is None:
            meta = paper_repo.fetch_from_openalex(ident)
            if meta is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail={
                    "code": "paper_not_found", "message": "Couldn't find that paper. Try its DOI or arXiv ID."})
            paper = paper_repo.insert_paper(session, meta)
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "missing", "message": "Give a paper_id or an identifier."})

    save_paper_for(session, me, uuid.UUID(paper.id))
    session.commit()
    return enrich(session, [paper], me)[0]


@router.delete("/library/save/{paper_id}", response_model=LibraryPaper)
def unsave(paper_id: uuid.UUID, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    """Remove from my library (and from my collections)."""
    paper = paper_repo.get_paper(session, paper_id)
    if paper is None:
        raise not_found("Paper")
    for s in session.exec(select(Save).where(Save.user_id == me.id, Save.paper_id == paper_id)).all():
        session.delete(s)
    my_cols = select(Collection.id).where(Collection.user_id == me.id)
    for item in session.exec(select(CollectionItem).where(CollectionItem.paper_id == paper_id, CollectionItem.collection_id.in_(my_cols))).all():
        session.delete(item)
    session.commit()
    return enrich(session, [paper], me)[0]


@router.get("/library/mine", response_model=List[LibraryPaper])
def my_library(session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    saved = session.exec(select(Save.paper_id).where(Save.user_id == me.id).order_by(Save.saved_at.desc())).all()
    return enrich(session, paper_repo.get_papers(session, list(saved)), me)


@router.get("/library/chanakya", response_model=ChanakyaLibraryOut)
def chanakya_library(
    sort: Literal["most_saved", "recent"] = "most_saved",
    q: str = "",
    limit: int = 50,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Every paper any member has saved, with how many members saved it."""
    order = "save_count DESC, last_saved_at DESC" if sort == "most_saved" else "last_saved_at DESC"
    rows = session.exec(text(f"""
        SELECT c.paper_id, c.save_count FROM library_save_counts c
        JOIN papers p ON p.id = c.paper_id
        WHERE p.title ILIKE :q
        ORDER BY {order} LIMIT :limit
    """), params={"q": f"%{q.strip()}%", "limit": min(limit, 200)}).all()
    total = session.exec(text("SELECT COUNT(*) FROM library_save_counts")).one()[0]
    return ChanakyaLibraryOut(total_papers=total, items=enrich(session, paper_repo.get_papers(session, [r.paper_id for r in rows]), me))


# ---------- collections ----------
def collection_out(session: Session, c: Collection) -> CollectionOut:
    n = session.exec(select(func.count()).select_from(CollectionItem).where(CollectionItem.collection_id == c.id)).one()
    return CollectionOut(id=str(c.id), name=c.name, item_count=n, created_at=c.created_at)


@router.get("/collections", response_model=List[CollectionOut])
def list_collections(session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    cols = session.exec(select(Collection).where(Collection.user_id == me.id).order_by(Collection.name)).all()
    return [collection_out(session, c) for c in cols]


@router.post("/collections", response_model=CollectionOut, status_code=status.HTTP_201_CREATED)
def create_collection(data: CollectionIn, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    name = data.name.strip()
    if session.exec(select(Collection).where(Collection.user_id == me.id, Collection.name == name)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, detail={"code": "duplicate", "message": "You already have a collection with this name."})
    c = Collection(user_id=me.id, name=name)
    session.add(c)
    session.commit()
    session.refresh(c)
    return collection_out(session, c)


@router.get("/collections/{collection_id}", response_model=CollectionDetail)
def get_collection(collection_id: uuid.UUID, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    c = my_collection_or_404(session, me, collection_id)
    items = session.exec(select(CollectionItem).where(CollectionItem.collection_id == c.id).order_by(CollectionItem.added_at.desc())).all()
    papers = {p.id: p for p in enrich(session, paper_repo.get_papers(session, [i.paper_id for i in items]), me)}
    return CollectionDetail(
        **collection_out(session, c).model_dump(),
        items=[CollectionItemOut(**papers[str(i.paper_id)].model_dump(), note=i.note, added_at=i.added_at)
               for i in items if str(i.paper_id) in papers],
    )


@router.delete("/collections/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(collection_id: uuid.UUID, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    """Deletes the folder only; the papers stay saved in your library."""
    session.delete(my_collection_or_404(session, me, collection_id))
    session.commit()


@router.post("/collections/{collection_id}/items", response_model=CollectionItemOut, status_code=status.HTTP_201_CREATED)
def add_to_collection(collection_id: uuid.UUID, data: ItemIn, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    c = my_collection_or_404(session, me, collection_id)
    paper = paper_repo.get_paper(session, data.paper_id)
    if paper is None:
        raise not_found("Paper")
    item = session.get(CollectionItem, (c.id, data.paper_id))
    if item is None:
        item = CollectionItem(collection_id=c.id, paper_id=data.paper_id, note=(data.note or "").strip() or None)
        session.add(item)
    elif data.note is not None:
        item.note = data.note.strip() or None
    save_paper_for(session, me, data.paper_id)   # adding to a collection also saves it
    session.commit()
    session.refresh(item)
    return CollectionItemOut(**enrich(session, [paper], me)[0].model_dump(), note=item.note, added_at=item.added_at)


@router.put("/collections/{collection_id}/items/{paper_id}", response_model=CollectionItemOut)
def update_note(collection_id: uuid.UUID, paper_id: uuid.UUID, data: NoteIn, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    c = my_collection_or_404(session, me, collection_id)
    item = session.get(CollectionItem, (c.id, paper_id))
    if item is None:
        raise not_found("Paper in this collection")
    item.note = (data.note or "").strip() or None
    session.commit()
    session.refresh(item)
    return CollectionItemOut(**enrich(session, [paper_repo.get_paper(session, paper_id)], me)[0].model_dump(), note=item.note, added_at=item.added_at)


@router.delete("/collections/{collection_id}/items/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_collection(collection_id: uuid.UUID, paper_id: uuid.UUID, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    c = my_collection_or_404(session, me, collection_id)
    item = session.get(CollectionItem, (c.id, paper_id))
    if item:
        session.delete(item)
        session.commit()
