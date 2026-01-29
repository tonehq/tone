from contextvars import ContextVar
from typing import Optional, Union
from dataclasses import dataclass
from uuid import UUID


@dataclass
class TenantContext:
    org_id: Optional[Union[str, UUID]] = None
    user_id: Optional[int] = None
    role: Optional[str] = None


_tenant_context: ContextVar[TenantContext] = ContextVar('tenant_context', default=TenantContext())


def get_tenant_context() -> TenantContext:
    return _tenant_context.get()


def set_tenant_context(org_id: Union[str, UUID] = None, user_id: int = None, role: str = None) -> None:
    _tenant_context.set(TenantContext(org_id=org_id, user_id=user_id, role=role))


def get_current_org_id() -> Optional[Union[str, UUID]]:
    return _tenant_context.get().org_id


def get_current_user_id() -> Optional[int]:
    return _tenant_context.get().user_id


def clear_tenant_context() -> None:
    _tenant_context.set(TenantContext())
