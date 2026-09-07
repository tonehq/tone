"""``AgentLlmEvalFolderService`` — single source of truth for CRUD on folder
nodes.

Folders are ``node_type='folder'`` rows in ``agent_llm_eval_scenarios`` (an
adjacency tree keyed by ``parent_id``); they previously lived in a separate
``agent_llm_eval_folders`` table. They survive after their last scenario is
deleted (Drive/Notion/Finder mental model) and rename is a single-row UPDATE.
Deleting a folder node cascades to its children (scenarios AND sub-folders)
via the ``ON DELETE CASCADE`` self-FK on ``agent_llm_eval_scenarios.parent_id``.

Every agent always has at least one folder (a seeded ``Default`` on
agent-create) so ``create_scenario`` always has a valid parent to write. The
service refuses to delete the last top-level folder so this invariant holds.

Errors are TYPED — the router maps them to HTTP codes, never the service.
"""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased

from core.models.agent import Agent
from core.models.agent_llm_eval_scenario import AgentLlmEvalScenario
from core.services.base import BaseService
from core.services.evals.errors import (
    AgentLlmEvalFolderNameConflictError,
    AgentLlmEvalFolderNotDeletableError,
    AgentLlmEvalFolderNotFoundError,
    EvalConfigurationError,
)


DEFAULT_FOLDER_NAME = "Default"

# Partial-index names for folder-name uniqueness (root vs child). Kept in one
# place so IntegrityError translation can't drift from the actual DB indexes.
_FOLDER_ROOT_CONSTRAINT = "uq_agent_llm_eval_scenarios_folder_root"
_FOLDER_CHILD_CONSTRAINT = "uq_agent_llm_eval_scenarios_folder_child"
_FOLDER_ROOT_WHERE = "node_type = 'folder' AND parent_id IS NULL"


@dataclass
class FolderRow:
    """Lightweight DTO — folder metadata + scenario count. Kept as a
    dataclass so the router can format the response without touching ORM
    lazy-load semantics."""

    id: UUID
    agent_id: UUID
    name: str
    description: Optional[str]
    parent_id: Optional[UUID]
    count: int
    created_at: Optional[str]
    updated_at: Optional[str]

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "name": self.name,
            "description": self.description,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "count": int(self.count),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class AgentLlmEvalFolderService(BaseService):
    """Manages ``node_type='folder'`` rows in ``agent_llm_eval_scenarios``.

    Instantiated per request/task with the caller's org context via
    ``BaseService``. Every read uses ``self.query(AgentLlmEvalScenario)`` so
    cross-tenant folder access is impossible.
    """

    # ── Read ────────────────────────────────────────────────────────────

    def list_folders(self, agent_id: UUID) -> list[FolderRow]:
        """Every folder node for one agent plus its direct scenario count.

        Single JOIN + GROUP BY so N folders cost 1 query. Ordered by
        (created_at ASC, name ASC) so the seeded ``Default`` folder lands
        first for newly-created agents. ``parent_id`` is surfaced so the FE
        can nest the tree client-side.
        """
        child = aliased(AgentLlmEvalScenario)
        rows = (
            self.query(AgentLlmEvalScenario)
            .with_entities(
                AgentLlmEvalScenario.id,
                AgentLlmEvalScenario.agent_id,
                AgentLlmEvalScenario.name,
                AgentLlmEvalScenario.parent_id,
                AgentLlmEvalScenario.created_at,
                AgentLlmEvalScenario.updated_at,
                func.count(child.id).label("count"),
            )
            .outerjoin(
                child,
                (child.parent_id == AgentLlmEvalScenario.id)
                & (child.node_type == "scenario"),
            )
            .filter(AgentLlmEvalScenario.agent_id == agent_id)
            .filter(AgentLlmEvalScenario.node_type == "folder")
            .group_by(
                AgentLlmEvalScenario.id,
                AgentLlmEvalScenario.agent_id,
                AgentLlmEvalScenario.name,
                AgentLlmEvalScenario.parent_id,
                AgentLlmEvalScenario.created_at,
                AgentLlmEvalScenario.updated_at,
            )
            .order_by(
                AgentLlmEvalScenario.created_at.asc(),
                AgentLlmEvalScenario.name.asc(),
            )
            .all()
        )
        return [
            FolderRow(
                id=r.id,
                agent_id=r.agent_id,
                name=r.name,
                description=None,
                parent_id=r.parent_id,
                count=int(r.count or 0),
                created_at=r.created_at.isoformat() if r.created_at else None,
                updated_at=r.updated_at.isoformat() if r.updated_at else None,
            )
            for r in rows
        ]

    def get_folder(self, agent_id: UUID, folder_id: UUID) -> AgentLlmEvalScenario:
        """Fetch one folder node, org- + agent-scoped. Raises
        ``AgentLlmEvalFolderNotFoundError`` when the id is missing OR belongs
        to another agent in the same org."""
        return self._require_folder(agent_id, folder_id)

    def count_folders(self, agent_id: UUID) -> int:
        """Number of folder nodes for one agent — used by ``delete_folder``
        to enforce the "at least one folder" invariant."""
        return int(
            self.query(AgentLlmEvalScenario)
            .filter(AgentLlmEvalScenario.agent_id == agent_id)
            .filter(AgentLlmEvalScenario.node_type == "folder")
            .count()
        )

    def scenario_count(self, agent_id: UUID, folder_id: UUID) -> int:
        """Number of scenarios directly in one folder (org-scoped via
        ``BaseService``). Lets the rename route echo the ``count`` field the
        FE type expects without a raw ``db.query`` in the router."""
        return int(
            self.query(AgentLlmEvalScenario)
            .filter(AgentLlmEvalScenario.agent_id == agent_id)
            .filter(AgentLlmEvalScenario.node_type == "scenario")
            .filter(AgentLlmEvalScenario.parent_id == folder_id)
            .count()
        )

    # ── Write ───────────────────────────────────────────────────────────

    def get_or_create_folder(
        self,
        agent_id: UUID,
        name: str,
        *,
        description: Optional[str] = None,  # accepted for API compat; not persisted
        commit: bool = True,
    ) -> AgentLlmEvalScenario:
        """Idempotent by top-level ``(agent_id, name)``. Used by the
        agent-create hook, the seed script, and the CSV importer.

        Trims the name; empty / whitespace-only raises
        ``EvalConfigurationError``.

        ``commit=False`` is for nested use — an outer service building its own
        transaction (agent-create seeding its Default folder, or bulk-create
        resolving CSV folder names) passes ``False`` so this helper only
        flushes and the outer commit/rollback stays atomic.

        Race-safe: Postgres ``INSERT ... ON CONFLICT DO NOTHING`` on the
        partial root-folder index, so a concurrent insert of the same
        ``(agent_id, name)`` doesn't taint the transaction. The final SELECT
        returns whichever row won the race.
        """
        cleaned_name = _clean_folder_name(name)
        if not cleaned_name:
            raise EvalConfigurationError("folder name must be non-empty")

        self._assert_agent_in_org(agent_id)

        existing = self._find_root_folder(agent_id, cleaned_name)
        if existing is not None:
            return existing

        stmt = (
            pg_insert(AgentLlmEvalScenario)
            .values(
                id=_uuid.uuid4(),
                organization_id=self.org_id,
                agent_id=agent_id,
                node_type="folder",
                name=cleaned_name,
                parent_id=None,
                approval_status="approved",
                scenario_ord=0,
            )
            .on_conflict_do_nothing(
                index_elements=["agent_id", "name"],
                index_where=text(_FOLDER_ROOT_WHERE),
            )
        )
        self.db.execute(stmt)
        if commit:
            self.db.commit()
        else:
            self.db.flush()

        row = self._find_root_folder(agent_id, cleaned_name)
        if row is None:
            raise AgentLlmEvalFolderNameConflictError(
                f"folder {cleaned_name!r} could not be resolved for agent {agent_id}"
            )
        logger.info(
            "[agent-llm-eval] resolved folder agent={} name={} id={}",
            agent_id, cleaned_name, row.id,
        )
        return row

    def create_folder(
        self,
        agent_id: UUID,
        name: str,
        *,
        description: Optional[str] = None,  # accepted for API compat; not persisted
        commit: bool = True,
    ) -> AgentLlmEvalScenario:
        """Explicit user-driven create of a top-level folder node. Raises
        ``AgentLlmEvalFolderNameConflictError`` on unique-index hit — callers
        that want idempotence should use ``get_or_create_folder``.
        """
        cleaned_name = _clean_folder_name(name)
        if not cleaned_name:
            raise EvalConfigurationError("folder name must be non-empty")

        self._assert_agent_in_org(agent_id)

        if self._find_root_folder(agent_id, cleaned_name) is not None:
            raise AgentLlmEvalFolderNameConflictError(
                f"folder {cleaned_name!r} already exists for agent {agent_id}"
            )

        row = AgentLlmEvalScenario(
            organization_id=self.org_id,
            agent_id=agent_id,
            node_type="folder",
            name=cleaned_name,
            parent_id=None,
            approval_status="approved",
            scenario_ord=0,
        )
        self.db.add(row)
        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            if _is_folder_name_conflict(exc):
                raise AgentLlmEvalFolderNameConflictError(
                    f"folder {cleaned_name!r} already exists for agent {agent_id}"
                ) from exc
            raise
        if commit:
            self.db.commit()
            self.db.refresh(row)
        logger.info(
            "[agent-llm-eval] created folder agent={} name={} id={}",
            agent_id, cleaned_name, row.id,
        )
        return row

    def rename_folder(
        self,
        agent_id: UUID,
        folder_id: UUID,
        new_name: str,
    ) -> AgentLlmEvalScenario:
        """Single-row UPDATE. Snapshot rows on ``agent_llm_eval_results`` keep
        the OLD name so history renders as it did at scoring time."""
        cleaned = _clean_folder_name(new_name)
        if not cleaned:
            raise EvalConfigurationError("new_name must be non-empty")

        row = self._require_folder(agent_id, folder_id)
        if row.name == cleaned:
            return row

        clash = (
            self.query(AgentLlmEvalScenario)
            .filter(AgentLlmEvalScenario.agent_id == agent_id)
            .filter(AgentLlmEvalScenario.node_type == "folder")
            .filter(AgentLlmEvalScenario.name == cleaned)
            .filter(AgentLlmEvalScenario.parent_id.is_(row.parent_id))
            .filter(AgentLlmEvalScenario.id != folder_id)
            .first()
        )
        if clash is not None:
            raise AgentLlmEvalFolderNameConflictError(
                f"folder {cleaned!r} already exists for agent {agent_id}"
            )

        old_name = row.name
        row.name = cleaned
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            if _is_folder_name_conflict(exc):
                raise AgentLlmEvalFolderNameConflictError(
                    f"folder {cleaned!r} already exists for agent {agent_id}"
                ) from exc
            raise
        self.db.refresh(row)
        logger.info(
            "[agent-llm-eval] renamed folder agent={} id={} old={} new={}",
            agent_id, folder_id, old_name, cleaned,
        )
        return row

    def delete_folder(self, agent_id: UUID, folder_id: UUID) -> dict:
        """Delete the folder node — the DB CASCADE (self-FK ``parent_id``)
        deletes every child scenario AND sub-folder. Past run results
        (``agent_llm_eval_results``) keep their snapshotted folder-name text
        column, so history remains readable.

        Refuses to delete the LAST remaining folder for an agent. Concurrency:
        a row-level ``SELECT ... FOR UPDATE`` on every folder node for this
        agent serialises concurrent deletes so we can't drop to zero folders.
        """
        from core.models.agent_llm_eval_result import AgentLlmEvalResult

        row = self._require_folder(agent_id, folder_id)

        locked = (
            self.query(AgentLlmEvalScenario)
            .filter(AgentLlmEvalScenario.agent_id == agent_id)
            .filter(AgentLlmEvalScenario.node_type == "folder")
            .with_for_update()
            .all()
        )
        if len(locked) <= 1:
            self.db.rollback()
            raise AgentLlmEvalFolderNotDeletableError(
                "Cannot delete the last folder for this agent — "
                "every agent must have at least one folder."
            )

        scenarios_deleted = (
            self.query(AgentLlmEvalScenario)
            .filter(AgentLlmEvalScenario.agent_id == agent_id)
            .filter(AgentLlmEvalScenario.node_type == "scenario")
            .filter(AgentLlmEvalScenario.parent_id == folder_id)
            .count()
        )
        results_preserved = (
            self.query(AgentLlmEvalResult)
            .filter(AgentLlmEvalResult.agent_id == agent_id)
            .filter(AgentLlmEvalResult.folder == row.name)
            .count()
        )

        self.db.delete(row)
        self.db.commit()
        logger.info(
            "[agent-llm-eval] deleted folder agent={} id={} name={} "
            "scenarios_deleted={} results_preserved={}",
            agent_id, folder_id, row.name, scenarios_deleted, results_preserved,
        )
        return {
            "folder_id": str(folder_id),
            "scenarios_deleted": int(scenarios_deleted),
            "results_preserved": int(results_preserved),
        }

    # ── Internals ───────────────────────────────────────────────────────

    def _find_root_folder(
        self, agent_id: UUID, name: str
    ) -> Optional[AgentLlmEvalScenario]:
        return (
            self.query(AgentLlmEvalScenario)
            .filter(AgentLlmEvalScenario.agent_id == agent_id)
            .filter(AgentLlmEvalScenario.node_type == "folder")
            .filter(AgentLlmEvalScenario.parent_id.is_(None))
            .filter(AgentLlmEvalScenario.name == name)
            .first()
        )

    def _require_folder(
        self, agent_id: UUID, folder_id: UUID
    ) -> AgentLlmEvalScenario:
        row = (
            self.query(AgentLlmEvalScenario)
            .filter(AgentLlmEvalScenario.id == folder_id)
            .filter(AgentLlmEvalScenario.agent_id == agent_id)
            .filter(AgentLlmEvalScenario.node_type == "folder")
            .first()
        )
        if row is None:
            raise AgentLlmEvalFolderNotFoundError(
                f"Folder {folder_id} not found for agent {agent_id}"
            )
        return row

    def _assert_agent_in_org(self, agent_id: UUID) -> None:
        """Cross-tenant leak guard for non-router callers (workers, CLIs, seed
        scripts) whose ``TenantContext`` might not match the target agent."""
        assert_agent_in_org(
            self.db,
            agent_id=agent_id,
            org_id=self.org_id,
            error_cls=EvalConfigurationError,
        )


# ── Helpers ──────────────────────────────────────────────────────────


def assert_agent_in_org(db, *, agent_id: UUID, org_id, error_cls) -> None:
    """Cross-tenant leak guard shared by the agent-LLM eval services (folder /
    scenario / version). Compares the AGENT's org to the caller's context and
    raises ``error_cls`` on a missing agent or org mismatch. Uses the raw
    session (not org-scoped ``query``) so it can detect the mismatch instead
    of silently returning ``None``."""
    agent_org = (
        db.query(Agent.organization_id).filter(Agent.id == agent_id).scalar()
    )
    if agent_org is None:
        raise error_cls(f"Agent {agent_id} not found — cannot resolve organization")
    if org_id is not None and str(agent_org) != str(org_id):
        raise error_cls(
            f"Agent {agent_id} does not belong to organization {org_id}"
        )


def _clean_folder_name(value: object) -> str:
    if value is None or not isinstance(value, str):
        return ""
    trimmed = value.strip()
    return trimmed[:120]


def _is_folder_name_conflict(exc: IntegrityError) -> bool:
    """True when the ``IntegrityError`` was raised by a folder-name partial
    unique index (root or child). Any other integrity violation is a
    different bug that should NOT be hidden behind a "folder exists" message.

    Priority: (1) exact index name from psycopg diag; (2) unique-violation
    pgcode 23505 AND an index-name substring."""
    orig = getattr(exc, "orig", None)
    diag = getattr(orig, "diag", None)
    constraint_name = getattr(diag, "constraint_name", None)
    folder_constraints = {_FOLDER_ROOT_CONSTRAINT, _FOLDER_CHILD_CONSTRAINT}
    if constraint_name is not None:
        return constraint_name in folder_constraints
    pgcode = getattr(orig, "pgcode", None)
    if pgcode != "23505":  # unique_violation
        return False
    return any(name in str(exc) for name in folder_constraints)


__all__ = [
    "AgentLlmEvalFolderService",
    "FolderRow",
    "DEFAULT_FOLDER_NAME",
]
