"""Database connection shared by all routers."""
import os

from sqlmodel import Session, create_engine

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def get_session():
    """FastAPI dependency: one DB session per request."""
    with Session(engine) as session:
        yield session
