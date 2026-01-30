from sqlalchemy import Column, BigInteger
from core.database.base import Base
import time


class TimestampModel(Base):
    __abstract__ = True

    id = Column(BigInteger, primary_key=True)
    created_at = Column(BigInteger, nullable=False, default=lambda: int(time.time()))
    updated_at = Column(BigInteger, nullable=False, default=lambda: int(time.time()))

