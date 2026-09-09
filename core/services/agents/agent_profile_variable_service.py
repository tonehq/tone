"""``AgentProfileVariableService`` — CRUD + runtime map for per-agent profile
variables (the ``{{profile.<key>}}`` placeholders).

Transport-agnostic: takes a SQLAlchemy session + org context via
``BaseService``. Every query is org-scoped (via ``self.query()``) AND
agent-scoped, so a valid variable id from another agent still 404s.

Errors are TYPED (``ProfileVariableNotFoundError`` /
``ProfileVariableKeyConflictError`` / ``ProfileVariableInvalidError``); the
route layer maps them to HTTP status codes.
"""

from __future__ import annotations

import re
from typing import Optional
from uuid import UUID

from loguru import logger
from sqlalchemy.exc import IntegrityError

from core.models.agent_profile_variable import AgentProfileVariable
from core.services.agents.errors import (
    ProfileVariableInvalidError,
    ProfileVariableKeyConflictError,
    ProfileVariableNotFoundError,
)
from core.services.base import BaseService
from core.services.pipeline.prompt_variables import PROMPT_VARIABLE_KEYS


# Keys reserved so a profile variable cannot shadow a system variable or the
# ``profile`` namespace itself. Reserved names live here so any future system
# variable added to ``PROMPT_VARIABLE_KEYS`` is automatically protected.
RESERVED_PROFILE_KEYS = frozenset({"profile", *PROMPT_VARIABLE_KEYS})

# Same shape the frontend picker and TipTap mention regex accept: starts with
# a letter, then letters/digits/underscore, up to 64 chars.
_KEY_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{0,63}$")

# 10 KB — enough for a long disclosure paragraph, small enough to keep list
# responses cheap. Measured in UTF-8 bytes so multi-byte content is bounded
# consistently between backend + frontend.
MAX_VALUE_BYTES = 10_240
MAX_DESCRIPTION_LEN = 1000

# Placeholders are always referenced as ``{{profile.<key>}}`` — this prefix
# lives in ONE place so no call site re-derives it.
PROFILE_PREFIX = "profile."


def _validate_key(key: str) -> str:
    key = (key or "").strip()
    if not _KEY_RE.match(key):
        raise ProfileVariableInvalidError(
            "Key must start with a letter and use only letters, numbers, "
            "or underscores (max 64 characters)."
        )
    if key in RESERVED_PROFILE_KEYS:
        raise ProfileVariableInvalidError(
            f"'{key}' is a reserved name and cannot be used as a profile variable key."
        )
    return key


def _validate_value(value: Optional[str]) -> str:
    value = value or ""
    if len(value.encode("utf-8")) > MAX_VALUE_BYTES:
        raise ProfileVariableInvalidError(
            f"Value is too long (max {MAX_VALUE_BYTES} bytes)."
        )
    return value


def _validate_description(description: Optional[str]) -> Optional[str]:
    if description is None:
        return None
    description = description.strip()
    if not description:
        return None
    if len(description) > MAX_DESCRIPTION_LEN:
        raise ProfileVariableInvalidError(
            f"Description is too long (max {MAX_DESCRIPTION_LEN} characters)."
        )
    return description


class AgentProfileVariableService(BaseService):
    """CRUD for one agent's profile variables + the ONE runtime accessor."""

    # ── Reads ────────────────────────────────────────────────────────────

    def list_variables(self, agent_id: UUID) -> list[AgentProfileVariable]:
        """All variables for an agent, ordered by key. No pagination — the
        per-agent set is small (well under 100 in practice) and the frontend
        filters client-side."""
        return (
            self.query(AgentProfileVariable)
            .filter(AgentProfileVariable.agent_id == agent_id)
            .order_by(AgentProfileVariable.key.asc())
            .all()
        )

    def get_variables_map(self, agent_id: UUID) -> dict[str, str]:
        """Runtime accessor called by the pipeline resolver.

        Returns ``{"profile.<key>": <value>, ...}`` — already in the shape
        ``substitute_variables`` consumes, so the resolver never re-derives
        the ``profile.`` prefix or the merge shape.
        """
        rows = self.list_variables(agent_id)
        return {f"{PROFILE_PREFIX}{r.key}": (r.value or "") for r in rows}

    # ── Writes ───────────────────────────────────────────────────────────

    def create_variable(
        self,
        agent_id: UUID,
        *,
        key: str,
        value: Optional[str] = "",
        description: Optional[str] = None,
    ) -> AgentProfileVariable:
        clean_key = _validate_key(key)
        clean_value = _validate_value(value)
        clean_desc = _validate_description(description)

        if self._exists_for_key(agent_id, clean_key):
            raise ProfileVariableKeyConflictError(
                f"A profile variable named '{clean_key}' already exists for this agent."
            )

        row = AgentProfileVariable(
            organization_id=self.org_id,
            agent_id=agent_id,
            key=clean_key,
            value=clean_value,
            description=clean_desc,
        )
        self.db.add(row)
        try:
            self.db.commit()
        except IntegrityError as exc:
            # Race with a concurrent insert — the UNIQUE constraint saves us.
            self.db.rollback()
            raise ProfileVariableKeyConflictError(
                f"A profile variable named '{clean_key}' already exists for this agent."
            ) from exc
        self.db.refresh(row)
        return row

    def update_variable(
        self,
        agent_id: UUID,
        variable_id: UUID,
        *,
        key: Optional[str] = None,
        value: Optional[str] = None,
        description: Optional[str] = None,
    ) -> AgentProfileVariable:
        """PATCH-style: only fields passed as non-``None`` are touched.

        Note: ``description`` is nullable, so to *clear* it callers can pass
        an empty string (normalized to ``None`` in ``_validate_description``).
        ``key`` and ``value`` never accept ``None`` as a "clear" — clearing
        the key is nonsensical and value defaults to empty string on create.
        """
        row = self._get_or_raise(agent_id, variable_id)

        if key is not None:
            new_key = _validate_key(key)
            if new_key != row.key and self._exists_for_key(agent_id, new_key):
                raise ProfileVariableKeyConflictError(
                    f"A profile variable named '{new_key}' already exists for this agent."
                )
            row.key = new_key

        if value is not None:
            row.value = _validate_value(value)

        if description is not None:
            row.description = _validate_description(description)

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ProfileVariableKeyConflictError(
                f"A profile variable named '{row.key}' already exists for this agent."
            ) from exc
        self.db.refresh(row)
        return row

    def delete_variable(self, agent_id: UUID, variable_id: UUID) -> None:
        row = self._get_or_raise(agent_id, variable_id)
        self.db.delete(row)
        self.db.commit()

    # ── Response formatter (public per API code style) ───────────────────

    def variable_response(self, row: AgentProfileVariable) -> dict:
        return row.to_dict()

    # ── Internal helpers ─────────────────────────────────────────────────

    def _get_or_raise(
        self, agent_id: UUID, variable_id: UUID
    ) -> AgentProfileVariable:
        row = (
            self.query(AgentProfileVariable)
            .filter(
                AgentProfileVariable.agent_id == agent_id,
                AgentProfileVariable.id == variable_id,
            )
            .first()
        )
        if row is None:
            raise ProfileVariableNotFoundError("Profile variable not found.")
        return row

    def _exists_for_key(self, agent_id: UUID, key: str) -> bool:
        return (
            self.query(AgentProfileVariable)
            .filter(
                AgentProfileVariable.agent_id == agent_id,
                AgentProfileVariable.key == key,
            )
            .first()
            is not None
        )
