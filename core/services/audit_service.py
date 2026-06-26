"""Audit-log writer.

Single entry point for every "this changed" event the platform records.

**Isolation contract.** Each ``log()`` call opens its own SQLAlchemy session,
inserts one row, commits, and closes — completely independent of the
caller's session/transaction. This is deliberate:

* The caller's writes (agent name change, tool attachment, etc.) live on
  their session and are unaffected by anything the audit writer does.
* An audit failure (bad data, DB hiccup) cannot revert the caller's
  changes — it can't even be in the same transaction.
* The trade-off: if the caller later rolls back, the audit row stays.
  This is the standard pattern for production audit logs — "user
  attempted X" is the truth being recorded, and is itself useful
  forensic data.

Higher-level helpers (``log_attachment_diff`` and ``log_field_diff``) compute
set-diffs / field-diffs from before+after snapshots and emit one row per
change. They keep the diff logic in one place so every caller (agent edits,
versioning, bulk attach endpoints) behaves identically.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, Optional, Set
from uuid import UUID

from core.context import get_request_context
from core.database.session import SessionLocal
from core.models.audit_log import AuditLog
from core.services.base import BaseService


logger = logging.getLogger(__name__)


# Field names whose values must never be persisted into ``changes``. Kept here
# (not in the action enum) because this is a security boundary, not a naming
# decision — touching this list is a deliberate audit-policy change.
_REDACTED_FIELDS: frozenset = frozenset({
    "api_key", "apikey", "secret", "client_secret", "token",
    "access_token", "refresh_token", "password", "encrypted_value",
})
_REDACTED_PLACEHOLDER = "***"


def _redact(value: Any) -> Any:
    """Return ``value`` with any nested secret-shaped keys masked.

    Only descends into dicts and lists; everything else is returned as-is.
    The check is case-insensitive and also matches any key that ends in
    ``_token``, ``_secret`` or ``_key`` so newly-added fields fail safely.
    """
    if isinstance(value, dict):
        return {
            k: (
                _REDACTED_PLACEHOLDER
                if _is_secret_key(k)
                else _redact(v)
            )
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    if lowered in _REDACTED_FIELDS:
        return True
    return (
        lowered.endswith("_token")
        or lowered.endswith("_secret")
        or lowered.endswith("_key")
        or lowered.endswith("_password")
    )


class AuditService(BaseService):
    """Writer for ``audit_logs``.

    Instantiated like any other ``BaseService``. The ``log()`` method is the
    only public entry — ``log_attachment_diff`` and ``log_field_diff`` are
    helpers built on top.
    """

    # ------------------------------------------------------------------
    # Public writer
    # ------------------------------------------------------------------

    def log(
        self,
        action: str,
        *,
        agent_id: UUID,
        agent_config_id: Optional[UUID] = None,
        target_resource_type: Optional[str] = None,
        target_resource_id: Optional[str] = None,
        before: Any = None,
        after: Any = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Optional[AuditLog]:
        """Persist one audit row in an isolated session. Never raises.

        Opens a fresh ``SessionLocal()``, INSERTs the row, commits, and
        closes. Because the audit write uses its own session and
        connection, **nothing it does can affect the caller's session** —
        no shared dirty state, no shared transaction, no possibility of
        rolling back the caller's pending edits.

        Failures are logged at WARNING level and swallowed. The caller's
        unit of work continues normally even if the audit row could not
        be written for any reason.
        """
        # Attach/detach events carry their meaning entirely in the
        # ``target_resource_id``. Without help, ``changes`` ends up null and
        # the UI has nothing to render. Auto-derive a minimal before/after
        # payload from the action suffix so attach rows show ``after={id}``
        # and detach rows show ``before={id}`` — symmetrical with field
        # diffs from ``log_field_diff``. Callers can still pass an explicit
        # before/after to override.
        if before is None and after is None and target_resource_id is not None:
            resource_payload = {"id": str(target_resource_id)}
            if target_resource_type:
                resource_payload["type"] = target_resource_type
            if action.endswith(".attached"):
                after = resource_payload
            elif action.endswith(".detached"):
                before = resource_payload

        try:
            audit_db = SessionLocal()
            try:
                row = AuditLog(
                    organization_id=self.org_id,
                    actor_user_id=self._to_uuid(self.user_id),
                    action=action,
                    agent_id=agent_id,
                    agent_config_id=agent_config_id,
                    target_resource_type=target_resource_type,
                    target_resource_id=(
                        str(target_resource_id) if target_resource_id is not None else None
                    ),
                    changes=self._build_changes(before, after, extra),
                    **self._request_fields(),
                )
                audit_db.add(row)
                audit_db.commit()
                # Detach from the closing session so callers can still read
                # ``row.id`` / ``row.created_at`` without lazy-load surprises.
                audit_db.refresh(row)
                audit_db.expunge(row)
                return row
            finally:
                audit_db.close()
        except Exception:  # pragma: no cover — defensive
            logger.warning("audit-log write failed", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # High-level helpers
    # ------------------------------------------------------------------

    def log_attachment_diff(
        self,
        *,
        agent_id: UUID,
        agent_config_id: Optional[UUID],
        before_ids: Iterable[Any],
        after_ids: Iterable[Any],
        attached_action: str,
        detached_action: str,
        resource_type: str,
    ) -> None:
        """Emit one row per attached / detached id.

        ``before_ids`` / ``after_ids`` can be any iterable of comparable
        values (UUIDs or strings). Order and duplicates are ignored — only
        set membership matters.
        """
        before_set: Set[Any] = set(before_ids or [])
        after_set: Set[Any] = set(after_ids or [])

        for added in after_set - before_set:
            self.log(
                attached_action,
                agent_id=agent_id,
                agent_config_id=agent_config_id,
                target_resource_type=resource_type,
                target_resource_id=str(added),
            )
        for removed in before_set - after_set:
            self.log(
                detached_action,
                agent_id=agent_id,
                agent_config_id=agent_config_id,
                target_resource_type=resource_type,
                target_resource_id=str(removed),
            )

    def log_field_diff(
        self,
        action: str,
        *,
        agent_id: UUID,
        agent_config_id: Optional[UUID],
        before: Dict[str, Any],
        after: Dict[str, Any],
        fields: Iterable[str],
    ) -> Optional[AuditLog]:
        """Emit one row carrying the diff between ``before`` and ``after``.

        Only keys in ``fields`` are inspected; only keys whose value
        actually changed end up in ``changes``. Returns ``None`` (no row
        written) when nothing changed — callers don't have to pre-check.
        """
        diff_before: Dict[str, Any] = {}
        diff_after: Dict[str, Any] = {}
        for field in fields:
            if field not in after:
                continue
            old_val = before.get(field)
            new_val = after[field]
            if old_val == new_val:
                continue
            diff_before[field] = old_val
            diff_after[field] = new_val

        if not diff_after:
            return None

        return self.log(
            action,
            agent_id=agent_id,
            agent_config_id=agent_config_id,
            before=diff_before,
            after=diff_after,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _to_uuid(value: Any) -> Optional[UUID]:
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _request_fields() -> Dict[str, Any]:
        ctx = get_request_context()
        return {
            "request_id": ctx.request_id,
            "ip_address": ctx.ip_address,
            "user_agent": ctx.user_agent,
        }

    @staticmethod
    def _build_changes(
        before: Any, after: Any, extra: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        payload: Dict[str, Any] = {}
        if before is not None:
            payload["before"] = _redact(before)
        if after is not None:
            payload["after"] = _redact(after)
        if extra:
            payload["extra"] = _redact(extra)
        return payload or None
