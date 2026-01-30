from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from ee.database.base import ee_engine

EESessionLocal = sessionmaker(bind=ee_engine, autocommit=False, autoflush=False)


def get_ee_db():
    db = EESessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_ee_db_context():
    db = EESessionLocal()
    try:
        yield db
    finally:
        db.close()
