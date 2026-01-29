from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from core.database.base import engine

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_script() -> Session:
    """Get a database session for scripts (non-generator)."""
    return SessionLocal()
