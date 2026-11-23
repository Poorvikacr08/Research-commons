"""
Python classes that map to tables created by db/init/01_schema.sql.
The SQL file creates the tables; these classes only read/write them
(we never call create_all).
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    email: str = Field(unique=True)
    password_hash: str
    role: str = "student"          # student / faculty / researcher / admin
    department: Optional[str] = None
    bio: Optional[str] = None
    links: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class UserInterest(SQLModel, table=True):
    __tablename__ = "user_interests"

    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    tag: str = Field(primary_key=True)


class FollowUser(SQLModel, table=True):
    __tablename__ = "follow_users"

    follower_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    followee_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)


class FollowTopic(SQLModel, table=True):
    __tablename__ = "follow_topics"

    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    tag: str = Field(primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)


class Post(SQLModel, table=True):
    __tablename__ = "posts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    author_id: uuid.UUID = Field(foreign_key="users.id")
    title: str
    body: str
    created_at: datetime = Field(default_factory=utcnow)


class PostTag(SQLModel, table=True):
    __tablename__ = "post_tags"

    post_id: uuid.UUID = Field(foreign_key="posts.id", primary_key=True)
    tag: str = Field(primary_key=True)


class PostPaper(SQLModel, table=True):
    __tablename__ = "post_papers"

    post_id: uuid.UUID = Field(foreign_key="posts.id", primary_key=True)
    paper_id: uuid.UUID = Field(primary_key=True)


class Comment(SQLModel, table=True):
    __tablename__ = "comments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    post_id: uuid.UUID = Field(foreign_key="posts.id")
    author_id: uuid.UUID = Field(foreign_key="users.id")
    parent_id: Optional[uuid.UUID] = Field(default=None, foreign_key="comments.id")  # None = top-level
    body: str
    created_at: datetime = Field(default_factory=utcnow)


class Upvote(SQLModel, table=True):
    __tablename__ = "upvotes"

    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    post_id: uuid.UUID = Field(foreign_key="posts.id", primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)


class Event(SQLModel, table=True):
    """Activity log read by Member 2 (analytics) and Member 3 (recs, trends)."""
    __tablename__ = "events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    event_type: str                      # view/search/save/follow/post/comment/upvote
    target_type: Optional[str] = None    # paper/post/user/topic
    target_id: Optional[uuid.UUID] = None
    target_tag: Optional[str] = None
    query_text: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
