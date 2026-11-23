"""
Activity logging. Call log_event(...) whenever a user views, searches,
saves, follows, posts, comments or upvotes. Member 2 and Member 3 read
the events table for analytics, recommendations and trends.
"""
import uuid
from typing import Optional

from sqlmodel import Session

from app.models import Event


def clean_tag(tag: str) -> str:
    """One spelling for every tag: 'Machine Learning ' -> 'machine learning'."""
    return " ".join(tag.strip().lower().split())


def log_event(
    session: Session,
    user_id: Optional[uuid.UUID],
    event_type: str,
    target_type: Optional[str] = None,
    target_id: Optional[uuid.UUID] = None,
    target_tag: Optional[str] = None,
    query_text: Optional[str] = None,
) -> None:
    """Adds an event row. The caller's session.commit() saves it."""
    session.add(Event(
        user_id=user_id, event_type=event_type, target_type=target_type,
        target_id=target_id, target_tag=target_tag, query_text=query_text,
    ))
