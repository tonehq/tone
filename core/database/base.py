from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
import logging

from core.config import settings

logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

keepalive_kwargs = {
    "keepalives": 1,
    "keepalives_idle": 30,
    "keepalives_interval": 5,
    "keepalives_count": 5,
}

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=50,
    max_overflow=70,
    pool_pre_ping=True,
    connect_args=keepalive_kwargs,
)

Base = declarative_base()
