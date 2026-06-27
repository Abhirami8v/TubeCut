"""
Database engine and session management.

Uses SQLAlchemy with SQLite by default (configurable via DATABASE_URL in
the environment) so the same code path works in development and can be
pointed at Postgres in production without changes elsewhere in the app.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


def init_db() -> None:
    """Create all tables. Safe to call repeatedly (no-op if they exist)."""
    # Import models so they are registered on Base.metadata before create_all.
    from app.models import job, clip, caption  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """FastAPI dependency that yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
