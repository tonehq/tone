from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from core.config import settings


class BaseService:
    def __init__(self, db: Session, user_id: Optional[int] = None):
        self.db = db
        self._user_id = user_id

    @property
    def org_id(self) -> UUID:
        return UUID(settings.DEFAULT_ORG_ID)

    @property
    def user_id(self) -> Optional[int]:
        return self._user_id
