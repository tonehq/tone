from sqlalchemy.orm import Session, Query
from sqlalchemy.dialects.postgresql import insert as pg_insert
from typing import TYPE_CHECKING, Optional, Union, List, Dict, Any, Type, TypeVar
from uuid import UUID

from core.context import get_current_org_id, get_current_user_id

if TYPE_CHECKING:
    from core.services.audit_service import AuditService

T = TypeVar('T')


class BaseService:
    def __init__(self, db: Session, user_id: Optional[Union[str, UUID]] = None, org_id: Optional[Union[str, UUID]] = None):
        self.db = db
        self._user_id = user_id
        self._org_id = org_id

    @property
    def org_id(self) -> Optional[Union[str, UUID]]:
        return self._org_id or get_current_org_id()

    @property
    def user_id(self) -> Optional[Union[str, UUID]]:
        return self._user_id or get_current_user_id()

    @property
    def audit(self) -> "AuditService":
        """Shared audit-log writer bound to this service's session.

        Lazy so the import stays local and we don't pay the construction
        cost on services that never log. ``AuditService`` itself extends
        ``BaseService``; instantiating it here would otherwise recurse,
        so the writer's own ``audit`` property is never invoked.
        """
        writer = getattr(self, "_audit_writer", None)
        if writer is None:
            from core.services.audit_service import AuditService
            writer = AuditService(self.db, user_id=self._user_id, org_id=self._org_id)
            self._audit_writer = writer
        return writer

    def query(self, model: Type[T]) -> Query:
        q = self.db.query(model)
        if hasattr(model, 'organization_id') and self.org_id:
            q = q.filter(model.organization_id == self.org_id)
        return q

    def upsert(self, model, values: Dict[str, Any], conflict_fields: List[str],
               update_fields: List[str], extra_update: Optional[Dict[str, Any]] = None,
               auto_commit: bool = True):
        if hasattr(model, 'organization_id') and 'organization_id' not in values and self.org_id:
            values['organization_id'] = self.org_id
        stmt = pg_insert(model).values(**values)
        update_dict = {field: getattr(stmt.excluded, field) for field in update_fields}
        if extra_update:
            update_dict.update(extra_update)
        stmt = stmt.on_conflict_do_update(
            index_elements=conflict_fields,
            set_=update_dict
        )
        self.db.execute(stmt)
        if auto_commit:
            self.db.commit()
