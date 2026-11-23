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
