"""
database.py - SQLAlchemy setup for the AI Image Detector backend
================================================================

WHY A DATABASE?
    Every successful /predict call should be persisted so the React
    frontend can show a "history" view of past scans. We use SQLite
    because the project is single-process / single-user for the viva
    demo - no need for a separate DB server.

LAYOUT:
    - `engine`: the actual DB connection (file: ./scans.db)
    - `SessionLocal`: a session factory. Each request gets its own
      session via the `get_db` dependency in main.py and closes it
      when the request finishes (this is important - leaked sessions
      keep DB file handles open).
    - `Base`: declarative base that all ORM models inherit from.
    - `Scan`: the single ORM table that stores one row per inference.
    - `init_db()`: creates the table on startup if it doesn't exist.

VIVA NOTE:
    SQLAlchemy's "declarative" style means we define columns as
    Python class attributes and SQLAlchemy generates the actual
    CREATE TABLE SQL for us. This keeps schema definition in code
    (version-controlled) instead of a separate .sql file.
"""

from __future__ import annotations

import os
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# ---------------------------------------------------------------
# Database URL
# ---------------------------------------------------------------
# SQLite file lives next to this script. Using a relative path keeps
# everything portable - the DB file goes wherever the backend folder
# goes.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "scans.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# ---------------------------------------------------------------
# SQLAlchemy core objects
# ---------------------------------------------------------------
# `check_same_thread=False` is the SQLite-specific flag we need because
# FastAPI can run request handlers on different threads than the one
# that created the engine. Safe because each request uses its own
# SessionLocal instance.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,  # set True to see raw SQL in console (useful for debugging)
)

# autocommit=False + autoflush=False is the recommended pattern for
# explicit transactions - we control when commits happen.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base - all ORM models inherit from this."""

    pass


# ---------------------------------------------------------------
# ORM model: one row per scan
# ---------------------------------------------------------------
class Scan(Base):
    """
    A single inference call against the model.

    Fields map directly to the JSON shape returned by /history:
        id, filename, label, confidence, timestamp, thumbnail_path.

    `label` stores either "REAL" or "AI-GENERATED" (the same string
    we send to the frontend, not the raw class index).
    """

    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    label = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    thumbnail_path = Column(String, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<Scan id={self.id} filename={self.filename!r} "
            f"label={self.label} confidence={self.confidence:.4f}>"
        )


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def init_db() -> None:
    """
    Create all tables that don't exist yet. Called once at app startup.
    Safe to call repeatedly - SQLAlchemy only issues CREATE TABLE for
    tables that are missing.
    """
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    FastAPI dependency that yields a DB session per request and
    guarantees it gets closed afterwards.

    Usage in main.py:
        @app.get(...)
        def handler(db: Session = Depends(get_db)):
            ...

    The `try/finally` ensures the session is closed even if the
    handler raises, preventing file-handle leaks on the SQLite file.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
