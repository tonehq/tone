from sqlalchemy import event
from sqlalchemy.orm import Session
import time

from core.context import get_current_org_id
from core.database.base import Base

TENANT_MODELS = [
    'agents', 'api_keys', 'models', 'voices', 'transcribers',
    'channel_phone_numbers', 'agent_knowledge', 'members',
    'organization_invites', 'organization_access_requests'
]


def setup_tenant_events():
    @event.listens_for(Session, "do_orm_execute")
    def _add_tenant_filter(orm_execute_state):
        if orm_execute_state.is_select:
            org_id = get_current_org_id()
            if org_id is not None:
                mapper = orm_execute_state.bind_mapper
                if mapper and hasattr(mapper.class_, '__tablename__'):
                    if mapper.class_.__tablename__ in TENANT_MODELS:
                        if hasattr(mapper.class_, 'organization_id'):
                            orm_execute_state.statement = orm_execute_state.statement.filter(
                                mapper.class_.organization_id == org_id
                            )

    @event.listens_for(Base, "before_insert", propagate=True)
    def _set_org_id_on_insert(mapper, connection, target):
        if hasattr(target, 'organization_id') and target.organization_id is None:
            org_id = get_current_org_id()
            if org_id is not None:
                target.organization_id = org_id

    @event.listens_for(Base, "before_update", propagate=True)
    def _set_updated_at(mapper, connection, target):
        if hasattr(target, 'updated_at'):
            target.updated_at = int(time.time())
