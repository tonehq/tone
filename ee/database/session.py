from core.database.session import SessionLocal, get_db

EESessionLocal = SessionLocal


def get_ee_db():
    return get_db()
