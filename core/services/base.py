from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from typing import Optional, Union, List, Dict, Any
from uuid import UUID

from core.context import get_current_org_id, get_current_user_id


class BaseService:
    def __init__(self, db: Session, user_id: Optional[int] = None):
        self.db = db
        self._user_id = user_id

    @property
    def org_id(self) -> Optional[Union[str, UUID]]:
        return get_current_org_id()

    @property
    def user_id(self) -> Optional[int]:
        return self._user_id or get_current_user_id()

    def upsert(self, model, values: Dict[str, Any], conflict_fields: List[str],
               update_fields: List[str], extra_update: Optional[Dict[str, Any]] = None):
        stmt = pg_insert(model).values(**values)
        update_dict = {field: getattr(stmt.excluded, field) for field in update_fields}
        if extra_update:
            update_dict.update(extra_update)
        stmt = stmt.on_conflict_do_update(
            index_elements=conflict_fields,
            set_=update_dict
        )
        self.db.execute(stmt)
        self.db.commit()
