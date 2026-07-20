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
    """Create all tables, run automated migrations, and seed default admin user."""
    # Import models so they are registered on Base.metadata before create_all.
    from app.models import user, job, clip, caption  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Run migrations for existing databases (add new columns if missing)
    from sqlalchemy import inspect, text
    inspector = inspect(engine)

    try:
        with engine.connect() as conn:
            # 1. Check and add user_id to jobs
            columns_jobs = [col["name"] for col in inspector.get_columns("jobs")]
            if "user_id" not in columns_jobs:
                print("[Migration] Adding user_id to jobs table")
                conn.execute(text("ALTER TABLE jobs ADD COLUMN user_id VARCHAR"))
                conn.commit()

            # 2. Check and add user_id, background_color, safe_margins to caption_styles
            columns_styles = [col["name"] for col in inspector.get_columns("caption_styles")]
            if "user_id" not in columns_styles:
                print("[Migration] Adding user_id to caption_styles table")
                conn.execute(text("ALTER TABLE caption_styles ADD COLUMN user_id VARCHAR"))
                conn.commit()
            if "background_color" not in columns_styles:
                print("[Migration] Adding background_color to caption_styles table")
                conn.execute(text("ALTER TABLE caption_styles ADD COLUMN background_color VARCHAR DEFAULT '#000000'"))
                conn.commit()
            if "safe_margins" not in columns_styles:
                print("[Migration] Adding safe_margins to caption_styles table")
                conn.execute(text("ALTER TABLE caption_styles ADD COLUMN safe_margins INTEGER DEFAULT 60"))
                conn.commit()
    except Exception as e:
        print(f"[Migration] Auto-migration encountered an issue (non-critical if tables are fresh): {e}")

    # Seed default admin user if none exists
    db = SessionLocal()
    try:
        from app.models.user import User, UserSettings
        from app.core.security import hash_password

        user_count = db.query(User).count()
        if user_count == 0:
            print("[Seed] Seeding default admin user: admin@tubecut.com")
            admin_user = User(
                email="admin@tubecut.com",
                hashed_password=hash_password("admin"),
                is_admin=True,
            )
            db.add(admin_user)
            db.flush()

            # Create default settings
            settings = UserSettings(user_id=admin_user.id)
            db.add(settings)
            db.commit()
    except Exception as e:
        print(f"[Seed] Error seeding admin user: {e}")
        db.rollback()
    finally:
        db.close()


def get_db() -> Session:
    """FastAPI dependency that yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
