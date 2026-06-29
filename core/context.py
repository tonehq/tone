from contextvars import ContextVar
from typing import Optional, Union
from dataclasses import dataclass
from uuid import UUID


@dataclass
class TenantContext:
    org_id: Optional[Union[str, UUID]] = None
    user_id: Optional[Union[str, UUID]] = None
    role: Optional[str] = None


@dataclass
class RequestContext:
    """Per-request metadata captured by RequestContextMiddleware.

    Read by the audit-log writer (and anything else that needs request
    correlation) without threading the FastAPI ``Request`` object through
    every service layer.
    """
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


_tenant_context: ContextVar[TenantContext] = ContextVar('tenant_context', default=TenantContext())
_request_context: ContextVar[RequestContext] = ContextVar('request_context', default=RequestContext())


def get_tenant_context() -> TenantContext:
    return _tenant_context.get()


def set_tenant_context(org_id: Union[str, UUID] = None, user_id: Union[str, UUID] = None, role: str = None) -> None:
    _tenant_context.set(TenantContext(org_id=org_id, user_id=user_id, role=role))


def get_current_org_id() -> Optional[Union[str, UUID]]:
    return _tenant_context.get().org_id


def get_current_user_id() -> Optional[Union[str, UUID]]:
    return _tenant_context.get().user_id


def clear_tenant_context() -> None:
    _tenant_context.set(TenantContext())


def get_request_context() -> RequestContext:
    return _request_context.get()


def set_request_context(
    request_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    _request_context.set(
        RequestContext(request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    )


def clear_request_context() -> None:
    _request_context.set(RequestContext())
