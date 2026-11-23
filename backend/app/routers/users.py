"""F1 profiles: view and edit profiles, interests, follow members and topics."""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.auth import get_current_user
from app.db import get_session
from app.events import clean_tag, log_event
from app.models import FollowTopic, FollowUser, User, UserInterest

router = APIRouter(tags=["users"])


# ---------- response / request shapes ----------
class MemberOut(BaseModel):
    id: str
    name: str
    role: str
    department: Optional[str] = None
    interests: List[str] = []
    is_following: bool = False


class ProfileOut(MemberOut):
    email: str
    bio: Optional[str] = None
    links: Optional[str] = None
    followers_count: int = 0
    following_count: int = 0
    is_me: bool = False


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1)
    department: Optional[str] = None
    bio: Optional[str] = None
    links: Optional[str] = None
    interests: List[str] = []


class TopicsOut(BaseModel):
    topics: List[str]


# ---------- helpers ----------
def interests_of(session: Session, user_id: uuid.UUID) -> List[str]:
    return list(session.exec(
        select(UserInterest.tag).where(UserInterest.user_id == user_id).order_by(UserInterest.tag)
    ).all())


def following_ids(session: Session, user_id: uuid.UUID) -> set:
    return set(session.exec(select(FollowUser.followee_id).where(FollowUser.follower_id == user_id)).all())


def get_user_or_404(session: Session, user_id: uuid.UUID) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "Member not found."})
    return user


def build_profile(session: Session, user: User, me: User) -> ProfileOut:
    followers = session.exec(select(func.count()).select_from(FollowUser).where(FollowUser.followee_id == user.id)).one()
    following = session.exec(select(func.count()).select_from(FollowUser).where(FollowUser.follower_id == user.id)).one()
    return ProfileOut(
        id=str(user.id), name=user.name, role=user.role, department=user.department,
        email=user.email, bio=user.bio, links=user.links,
        interests=interests_of(session, user.id),
        followers_count=followers, following_count=following,
        is_following=user.id in following_ids(session, me.id),
        is_me=user.id == me.id,
    )


# ---------- members ----------
@router.get("/users", response_model=List[MemberOut])
def list_members(
    q: Optional[str] = None,
    department: Optional[str] = None,
    limit: int = 50,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Members directory. ?q= searches name, department and interests."""
    stmt = select(User).where(User.id != me.id)
    if department:
        stmt = stmt.where(User.department == department)
    if q:
        like = f"%{q.strip()}%"
        with_interest = select(UserInterest.user_id).where(UserInterest.tag.ilike(like))
        stmt = stmt.where(or_(User.name.ilike(like), User.department.ilike(like), User.id.in_(with_interest)))
    users = session.exec(stmt.order_by(User.name).limit(min(limit, 200))).all()
    mine = following_ids(session, me.id)
    return [
        MemberOut(id=str(u.id), name=u.name, role=u.role, department=u.department,
                  interests=interests_of(session, u.id), is_following=u.id in mine)
        for u in users
    ]


@router.get("/users/{user_id}", response_model=ProfileOut)
def get_profile(user_id: uuid.UUID, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    user = get_user_or_404(session, user_id)
    if user.id != me.id:
        log_event(session, me.id, "view", "user", target_id=user.id)
        session.commit()
    return build_profile(session, user, me)


@router.put("/users/me", response_model=ProfileOut)
def update_my_profile(data: ProfileUpdate, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    me.name = data.name.strip()
    me.department = (data.department or "").strip() or None
    me.bio = (data.bio or "").strip() or None
    me.links = (data.links or "").strip() or None
    session.add(me)

    # replace interests with the new list (cleaned, no duplicates)
    for old in session.exec(select(UserInterest).where(UserInterest.user_id == me.id)).all():
        session.delete(old)
    for tag in sorted({clean_tag(t) for t in data.interests if t.strip()}):
        session.add(UserInterest(user_id=me.id, tag=tag))

    session.commit()
    session.refresh(me)
    return build_profile(session, me, me)


@router.post("/users/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
def follow_member(user_id: uuid.UUID, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    get_user_or_404(session, user_id)
    if user_id == me.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "self_follow", "message": "You can't follow yourself."})
    if session.get(FollowUser, (me.id, user_id)) is None:
        session.add(FollowUser(follower_id=me.id, followee_id=user_id))
        log_event(session, me.id, "follow", "user", target_id=user_id)
        session.commit()


@router.delete("/users/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
def unfollow_member(user_id: uuid.UUID, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    row = session.get(FollowUser, (me.id, user_id))
    if row:
        session.delete(row)
        session.commit()


# ---------- topics ----------
@router.get("/topics/following", response_model=TopicsOut)
def my_topics(session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    tags = session.exec(select(FollowTopic.tag).where(FollowTopic.user_id == me.id).order_by(FollowTopic.tag)).all()
    return TopicsOut(topics=list(tags))


@router.post("/topics/{tag}/follow", response_model=TopicsOut)
def follow_topic(tag: str, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    tag = clean_tag(tag)
    if not tag:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "empty_tag", "message": "Topic can't be empty."})
    if session.get(FollowTopic, (me.id, tag)) is None:
        session.add(FollowTopic(user_id=me.id, tag=tag))
        log_event(session, me.id, "follow", "topic", target_tag=tag)
        session.commit()
    return my_topics(session, me)


@router.delete("/topics/{tag}/follow", response_model=TopicsOut)
def unfollow_topic(tag: str, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    row = session.get(FollowTopic, (me.id, clean_tag(tag)))
    if row:
        session.delete(row)
        session.commit()
    return my_topics(session, me)
