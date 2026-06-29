"""Read-side service for the audit log.

The writer lives in :mod:`core.services.audit_service`; this module only
queries. Kept separate so the writer stays tiny and dependency-free while
the reader can grow filters, joins, and serialisers without bloating the
hot write path.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
from uuid import UUID

from sqlalchemy import desc

from core.models.audit_log import AuditLog
from core.services.base import BaseService


class AuditLogService(BaseService):
    """Paginated read access to ``audit_logs``."""

    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 200

    def list(
        self,
        *,
        agent_id: UUID,
        actions: Optional[Iterable[str]] = None,
        actor_user_id: Optional[UUID] = None,
        start_date_time: Optional[datetime] = None,
        end_date_time: Optional[datetime] = None,
        page_no: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> Dict[str, Any]:
        """Return one page of audit rows scoped to ``agent_id``.

        Filters are AND-combined; ``actions`` accepts a list so the UI can
        bundle related events (e.g. show every attach/detach in one tab).
        Results are sorted ``created_at DESC`` so the newest event is
        first — the order the UI renders.
        """
        page_size = max(1, min(int(page_size), self.MAX_PAGE_SIZE))
        page_no = max(1, int(page_no))

        query = self.query(AuditLog).filter(AuditLog.agent_id == agent_id)

        actions_list = [a for a in (actions or []) if a]
        if actions_list:
            query = query.filter(AuditLog.action.in_(actions_list))
        if actor_user_id is not None:
            query = query.filter(AuditLog.actor_user_id == actor_user_id)
        if start_date_time is not None:
            query = query.filter(AuditLog.created_at >= start_date_time)
        if end_date_time is not None:
            query = query.filter(AuditLog.created_at <= end_date_time)

        total = query.count()
        rows: List[AuditLog] = (
            query.order_by(desc(AuditLog.created_at), desc(AuditLog.id))
            .offset((page_no - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "items": [self._serialize(row) for row in rows],
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
        }

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize(row: AuditLog) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "actor_user_id": str(row.actor_user_id) if row.actor_user_id else None,
            "action": row.action,
            "agent_id": str(row.agent_id) if row.agent_id else None,
            "agent_config_id": (
                str(row.agent_config_id) if row.agent_config_id else None
            ),
            "target_resource_type": row.target_resource_type,
            "target_resource_id": row.target_resource_id,
            "changes": row.changes,
            "request_id": row.request_id,
            "ip_address": str(row.ip_address) if row.ip_address else None,
            "user_agent": row.user_agent,
        }
