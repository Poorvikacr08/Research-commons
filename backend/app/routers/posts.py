"""F2 posts and discussions: posts with tags and papers, comments + replies, upvotes, feed."""
import uuid
from datetime import datetime
from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import bindparam, func, or_, text
from sqlmodel import Session, select

from app.auth import get_current_user
from app.db import get_session
from app.events import clean_tag, log_event
from app.models import Comment, FollowTopic, FollowUser, Post, PostPaper, PostTag, Upvote, User, UserInterest

router = APIRouter(tags=["posts"])


# ---------- shapes ----------
class AuthorOut(BaseModel):
    id: str
    name: str
    department: Optional[str] = None


class PaperRef(BaseModel):
    id: str
    title: str


class PostSummary(BaseModel):
    id: str
    title: str
    snippet: str
    author: AuthorOut
    tags: List[str]
    created_at: datetime
    upvotes: int
    comment_count: int
    has_upvoted: bool
    reason: Optional[str] = None      # why it is in your feed


class CommentOut(BaseModel):
    id: str
    parent_id: Optional[str]
    author: AuthorOut
    body: str
    created_at: datetime


class PostDetail(PostSummary):
    body: str
    papers: List[PaperRef]
    comments: List[CommentOut]      # flat list; parent_id says which comment it replies to
    can_delete: bool


class PostIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)
    tags: List[str] = []
    paper_ids: List[uuid.UUID] = []


class CommentIn(BaseModel):
    body: str = Field(min_length=1)
    parent_id: Optional[uuid.UUID] = None


class FeedOut(BaseModel):
    strategy: str                    # "following" | "popular" | "all"
    items: List[PostSummary]


class UpvoteOut(BaseModel):
    upvotes: int
    has_upvoted: bool


# ---------- helpers ----------
def not_found(what: str = "Post"):
    return HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": f"{what} not found."})


def authors_by_id(session: Session, ids) -> Dict[uuid.UUID, AuthorOut]:
    users = session.exec(select(User).where(User.id.in_(list(set(ids))))).all() if ids else []
    return {u.id: AuthorOut(id=str(u.id), name=u.name, department=u.department) for u in users}


def summarize(session: Session, posts: List[Post], me: User, reasons: Optional[dict] = None) -> List[PostSummary]:
    """Turn Post rows into cards, loading tags/counts for all posts in a few queries."""
    if not posts:
        return []
    ids = [p.id for p in posts]
    tags: Dict[uuid.UUID, List[str]] = {}
    for pid, tag in session.exec(select(PostTag.post_id, PostTag.tag).where(PostTag.post_id.in_(ids)).order_by(PostTag.tag)):
        tags.setdefault(pid, []).append(tag)
    upvotes = dict(session.exec(select(Upvote.post_id, func.count()).where(Upvote.post_id.in_(ids)).group_by(Upvote.post_id)).all())
    comments = dict(session.exec(select(Comment.post_id, func.count()).where(Comment.post_id.in_(ids)).group_by(Comment.post_id)).all())
    mine = set(session.exec(select(Upvote.post_id).where(Upvote.user_id == me.id, Upvote.post_id.in_(ids))).all())
    authors = authors_by_id(session, [p.author_id for p in posts])
    reasons = reasons or {}
    return [
        PostSummary(
            id=str(p.id), title=p.title,
            snippet=p.body[:220] + ("…" if len(p.body) > 220 else ""),
            author=authors[p.author_id], tags=tags.get(p.id, []), created_at=p.created_at,
            upvotes=upvotes.get(p.id, 0), comment_count=comments.get(p.id, 0),
            has_upvoted=p.id in mine, reason=reasons.get(p.id),
        )
        for p in posts
    ]


def paper_refs(session: Session, paper_ids: List[uuid.UUID]) -> List[PaperRef]:
    """Titles from Member 2's papers table."""
    if not paper_ids:
        return []
    stmt = text("SELECT id, title FROM papers WHERE id IN :ids").bindparams(bindparam("ids", expanding=True))
    return [PaperRef(id=str(r.id), title=r.title) for r in session.exec(stmt, params={"ids": list(paper_ids)})]


# ---------- posts ----------
@router.post("/posts", response_model=PostDetail, status_code=status.HTTP_201_CREATED)
def create_post(data: PostIn, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    paper_ids = list(dict.fromkeys(data.paper_ids))
    if paper_ids and len(paper_refs(session, paper_ids)) != len(paper_ids):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "unknown_paper", "message": "One of the attached papers does not exist."})

    post = Post(author_id=me.id, title=data.title.strip(), body=data.body.strip())
    session.add(post)
    session.flush()  # gives post.id before we add tags
    for tag in sorted({clean_tag(t) for t in data.tags if t.strip()}):
        session.add(PostTag(post_id=post.id, tag=tag))
    for pid in paper_ids:
        session.add(PostPaper(post_id=post.id, paper_id=pid))
    log_event(session, me.id, "post", "post", target_id=post.id)
    session.commit()
    return post_detail(session, post, me)


@router.get("/posts", response_model=List[PostSummary])
def list_posts(
    tag: Optional[str] = None,
    author_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Posts filtered by ?tag= or ?author_id=, newest first."""
    stmt = select(Post)
    if tag:
        stmt = stmt.where(Post.id.in_(select(PostTag.post_id).where(PostTag.tag == clean_tag(tag))))
    if author_id:
        stmt = stmt.where(Post.author_id == author_id)
    posts = session.exec(stmt.order_by(Post.created_at.desc()).limit(min(limit, 200))).all()
    return summarize(session, posts, me)


@router.get("/posts/{post_id}", response_model=PostDetail)
def get_post(post_id: uuid.UUID, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    post = session.get(Post, post_id)
    if post is None:
        raise not_found()
    if post.author_id != me.id:
        log_event(session, me.id, "view", "post", target_id=post.id)
        session.commit()
    return post_detail(session, post, me)


def post_detail(session: Session, post: Post, me: User) -> PostDetail:
    summary = summarize(session, [post], me)[0]
    comments = session.exec(select(Comment).where(Comment.post_id == post.id).order_by(Comment.created_at)).all()
    authors = authors_by_id(session, [c.author_id for c in comments])
    paper_ids = session.exec(select(PostPaper.paper_id).where(PostPaper.post_id == post.id)).all()
    return PostDetail(
        **summary.model_dump(),
        body=post.body,
        papers=paper_refs(session, list(paper_ids)),
        comments=[
            CommentOut(id=str(c.id), parent_id=str(c.parent_id) if c.parent_id else None,
                       author=authors[c.author_id], body=c.body, created_at=c.created_at)
            for c in comments
        ],
        can_delete=post.author_id == me.id or me.role == "admin",
    )


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: uuid.UUID, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    post = session.get(Post, post_id)
    if post is None:
        raise not_found()
    if post.author_id != me.id and me.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail={"code": "forbidden", "message": "You can only delete your own posts."})
    session.delete(post)   # tags, papers, comments and upvotes go too (ON DELETE CASCADE)
    session.commit()


# ---------- comments ----------
@router.post("/posts/{post_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(post_id: uuid.UUID, data: CommentIn, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    if session.get(Post, post_id) is None:
        raise not_found()
    if data.parent_id:
        parent = session.get(Comment, data.parent_id)
        if parent is None or parent.post_id != post_id:
            raise not_found("Comment to reply to")
    comment = Comment(post_id=post_id, author_id=me.id, parent_id=data.parent_id, body=data.body.strip())
    session.add(comment)
    log_event(session, me.id, "comment", "post", target_id=post_id)
    session.commit()
    session.refresh(comment)
    return CommentOut(id=str(comment.id), parent_id=str(comment.parent_id) if comment.parent_id else None,
                      author=AuthorOut(id=str(me.id), name=me.name, department=me.department),
                      body=comment.body, created_at=comment.created_at)


# ---------- upvotes ----------
def upvote_state(session: Session, post_id: uuid.UUID, me: User) -> UpvoteOut:
    count = session.exec(select(func.count()).select_from(Upvote).where(Upvote.post_id == post_id)).one()
    return UpvoteOut(upvotes=count, has_upvoted=session.get(Upvote, (me.id, post_id)) is not None)


@router.post("/posts/{post_id}/upvote", response_model=UpvoteOut)
def upvote(post_id: uuid.UUID, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    if session.get(Post, post_id) is None:
        raise not_found()
    if session.get(Upvote, (me.id, post_id)) is None:
        session.add(Upvote(user_id=me.id, post_id=post_id))
        log_event(session, me.id, "upvote", "post", target_id=post_id)
        session.commit()
    return upvote_state(session, post_id, me)


@router.delete("/posts/{post_id}/upvote", response_model=UpvoteOut)
def remove_upvote(post_id: uuid.UUID, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    row = session.get(Upvote, (me.id, post_id))
    if row:
        session.delete(row)
        session.commit()
    return upvote_state(session, post_id, me)


# ---------- feed ----------
@router.get("/feed", response_model=FeedOut)
def feed(
    tab: Literal["following", "all"] = "following",
    limit: int = 30,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """
    following: posts from people you follow, topics you follow, or matching your interests.
    New users with nothing to follow get popular recent posts (strategy = "popular").
    all: every post, newest first.
    """
    limit = min(limit, 100)
    if tab == "all":
        posts = session.exec(select(Post).order_by(Post.created_at.desc()).limit(limit)).all()
        return FeedOut(strategy="all", items=summarize(session, posts, me))

    people = set(session.exec(select(FollowUser.followee_id).where(FollowUser.follower_id == me.id)).all())
    topics = set(session.exec(select(FollowTopic.tag).where(FollowTopic.user_id == me.id)).all())
    interests = set(session.exec(select(UserInterest.tag).where(UserInterest.user_id == me.id)).all())

    conditions = []
    if people:
        conditions.append(Post.author_id.in_(people))
    if topics | interests:
        conditions.append(Post.id.in_(select(PostTag.post_id).where(PostTag.tag.in_(topics | interests))))

    posts = []
    if conditions:
        posts = session.exec(
            select(Post).where(Post.author_id != me.id, or_(*conditions)).order_by(Post.created_at.desc()).limit(limit)
        ).all()

    if posts:
        # say why each post is here
        post_tags: Dict[uuid.UUID, set] = {}
        for pid, tag in session.exec(select(PostTag.post_id, PostTag.tag).where(PostTag.post_id.in_([p.id for p in posts]))):
            post_tags.setdefault(pid, set()).add(tag)
        authors = authors_by_id(session, [p.author_id for p in posts])
        reasons = {}
        for p in posts:
            t = post_tags.get(p.id, set())
            if p.author_id in people:
                reasons[p.id] = f"You follow {authors[p.author_id].name}"
            elif t & topics:
                reasons[p.id] = f"Topic you follow: {sorted(t & topics)[0]}"
            else:
                reasons[p.id] = f"Matches your interest: {sorted(t & interests)[0]}"
        return FeedOut(strategy="following", items=summarize(session, posts, me, reasons))

    # cold start: most upvoted + commented recent posts
    score = (
        select(Post.id, (func.count(func.distinct(Upvote.user_id)) + func.count(func.distinct(Comment.id))).label("score"))
        .join(Upvote, Upvote.post_id == Post.id, isouter=True)
        .join(Comment, Comment.post_id == Post.id, isouter=True)
        .where(Post.author_id != me.id)
        .group_by(Post.id)
        .subquery()
    )
    posts = session.exec(
        select(Post).join(score, score.c.id == Post.id).order_by(score.c.score.desc(), Post.created_at.desc()).limit(limit)
    ).all()
    return FeedOut(strategy="popular", items=summarize(session, posts, me, {p.id: "Popular on Research Commons" for p in posts}))
