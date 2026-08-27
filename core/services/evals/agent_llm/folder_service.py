"""``AgentLlmEvalFolderService`` — single source of truth for CRUD on
``agent_llm_eval_folders``.

Folders are first-class rows so they survive after their last scenario is
deleted (Drive/Notion/Finder mental model) and rename is a single-row
UPDATE. Deleting a folder cascades to every scenario inside it via the
``ON DELETE CASCADE`` FK on ``agent_llm_eval_scenarios.folder_id``.

Every agent always has at least one folder (a seeded ``Default`` on
agent-create) so ``create_scenario`` always has a valid ``folder_id`` to
write. The service refuses to delete the last folder so this invariant
holds at runtime too.

Errors are TYPED — the router maps them to HTTP codes, never the service.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from core.models.agent import Agent
from core.models.agent_llm_eval_folder import AgentLlmEvalFolder
from core.models.agent_llm_eval_scenario import AgentLlmEvalScenario
from core.services.base import BaseService
from core.services.evals.errors import (
    AgentLlmEvalFolderNameConflictError,
    AgentLlmEvalFolderNotDeletableError,
    AgentLlmEvalFolderNotFoundError,
    EvalConfigurationError,
)


DEFAULT_FOLDER_NAME = "Default"

# Constraint name from the model — kept in one place so IntegrityError
# translation can't drift from the actual DB constraint if the model is
# renamed.
_FOLDER_NAME_CONSTRAINT = "uq_agent_llm_eval_folders_agent_name"


@dataclass
class FolderRow:
    """Lightweight DTO — folder metadata + scenario count. Kept as a
    dataclass so the router can format the response without touching ORM
    lazy-load semantics."""

    id: UUID
    agent_id: UUID
    name: str
    description: Optional[str]
    count: int
    created_at: Optional[str]
    updated_at: Optional[str]

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "name": self.name,
            "description": self.description,
            "count": int(self.count),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class AgentLlmEvalFolderService(BaseService):
    """Manages ``agent_llm_eval_folders`` rows.

    Instantiated per request/task with the caller's org context via
    ``BaseService``. Every read uses ``self.query(AgentLlmEvalFolder)`` so
    cross-tenant folder access is impossible.
    """

    # ── Read ────────────────────────────────────────────────────────────

    def list_folders(self, agent_id: UUID) -> list[FolderRow]:
        """Every folder for one agent plus its scenario count.

        Single JOIN + GROUP BY so N folders cost 1 query. Ordered by
        (created_at ASC, name ASC) so the seeded ``Default`` folder lands
        first for newly-created agents.
        """
        rows = (
            self.query(AgentLlmEvalFolder)
            .with_entities(
                AgentLlmEvalFolder.id,
                AgentLlmEvalFolder.agent_id,
                AgentLlmEvalFolder.name,
                AgentLlmEvalFolder.description,
                AgentLlmEvalFolder.created_at,
                AgentLlmEvalFolder.updated_at,
                func.count(AgentLlmEvalScenario.id).label("count"),
            )
            .outerjoin(
                AgentLlmEvalScenario,
                AgentLlmEvalScenario.folder_id == AgentLlmEvalFolder.id,
            )
            .filter(AgentLlmEvalFolder.agent_id == agent_id)
            .group_by(
                AgentLlmEvalFolder.id,
                AgentLlmEvalFolder.agent_id,
                AgentLlmEvalFolder.name,
                AgentLlmEvalFolder.description,
                AgentLlmEvalFolder.created_at,
                AgentLlmEvalFolder.updated_at,
            )
            .order_by(
                AgentLlmEvalFolder.created_at.asc(),
                AgentLlmEvalFolder.name.asc(),
            )
            .all()
        )
        return [
            FolderRow(
                id=r.id,
                agent_id=r.agent_id,
                name=r.name,
                description=r.description,
                count=int(r.count or 0),
                created_at=r.created_at.isoformat() if r.created_at else None,
                updated_at=r.updated_at.isoformat() if r.updated_at else None,
            )
            for r in rows
        ]

    def get_folder(self, agent_id: UUID, folder_id: UUID) -> AgentLlmEvalFolder:
        """Fetch one folder, org- + agent-scoped. Raises
        ``AgentLlmEvalFolderNotFoundError`` when the id is missing OR belongs
        to another agent in the same org."""
        return self._require_folder(agent_id, folder_id)

    def count_folders(self, agent_id: UUID) -> int:
        """Number of folders for one agent — used by ``delete_folder`` to
        enforce the "at least one folder" invariant."""
        return int(
            self.query(AgentLlmEvalFolder)
            .filter(AgentLlmEvalFolder.agent_id == agent_id)
            .count()
        )

    # ── Write ───────────────────────────────────────────────────────────

    def get_or_create_folder(
        self,
        agent_id: UUID,
        name: str,
        *,
        description: Optional[str] = None,
        commit: bool = True,
    ) -> AgentLlmEvalFolder:
        """Idempotent by ``(agent_id, name)``. Used by the agent-create
        hook, the seed script, and the CSV importer.

        Trims the name; empty / whitespace-only raises
        ``EvalConfigurationError``. Does not touch ``description`` on an
        existing folder — used only when a fresh row is inserted.

        ``commit=False`` is for nested use — an outer service that is
        itself building a transaction (e.g. agent-create seeding its
        Default folder, or bulk-create resolving CSV folder names) passes
        ``False`` so this helper only flushes, and the outer commit/
        rollback stays atomic. Public routes leave the default so the
        write is committed inline.

        Race-safe: uses Postgres ``INSERT ... ON CONFLICT DO NOTHING``
        so a concurrent insert of the same ``(agent_id, name)`` doesn't
        taint the transaction with an IntegrityError. The final SELECT
        returns whichever row won the race.
        """
        cleaned_name = _clean_folder_name(name)
        if not cleaned_name:
            raise EvalConfigurationError("folder name must be non-empty")

        self._assert_agent_in_org(agent_id)

        existing = (
            self.query(AgentLlmEvalFolder)
            .filter(AgentLlmEvalFolder.agent_id == agent_id)
            .filter(AgentLlmEvalFolder.name == cleaned_name)
            .first()
        )
        if existing is not None:
            return existing

        import uuid as _uuid

        from sqlalchemy.dialects.postgresql import insert as pg_insert

        new_id = _uuid.uuid4()
        stmt = (
            pg_insert(AgentLlmEvalFolder)
            .values(
                id=new_id,
                organization_id=self.org_id,
                agent_id=agent_id,
                name=cleaned_name,
                description=_clean_optional_text(description),
            )
            .on_conflict_do_nothing(
                index_elements=["agent_id", "name"],
            )
        )
        self.db.execute(stmt)
        if commit:
            self.db.commit()
        else:
            self.db.flush()

        # Reload the row (either the one we just inserted, or the winner
        # of a concurrent race — always visible after our own commit /
        # after the winning txn's commit, whichever came first).
        row = (
            self.query(AgentLlmEvalFolder)
            .filter(AgentLlmEvalFolder.agent_id == agent_id)
            .filter(AgentLlmEvalFolder.name == cleaned_name)
            .first()
        )
        if row is None:
            # Should be impossible — ON CONFLICT DO NOTHING succeeded and
            # a row with (agent_id, name) must exist. Surface as a
            # conflict so the caller can retry rather than crash.
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
        description: Optional[str] = None,
        commit: bool = True,
    ) -> AgentLlmEvalFolder:
        """Explicit user-driven create. Raises
        ``AgentLlmEvalFolderNameConflictError`` on unique-constraint hit —
        callers that want idempotence should use ``get_or_create_folder``.

        ``commit`` — see :meth:`get_or_create_folder`.
        """
        cleaned_name = _clean_folder_name(name)
        if not cleaned_name:
            raise EvalConfigurationError("folder name must be non-empty")

        self._assert_agent_in_org(agent_id)

        clash = (
            self.query(AgentLlmEvalFolder)
            .filter(AgentLlmEvalFolder.agent_id == agent_id)
            .filter(AgentLlmEvalFolder.name == cleaned_name)
            .first()
        )
        if clash is not None:
            raise AgentLlmEvalFolderNameConflictError(
                f"folder {cleaned_name!r} already exists for agent {agent_id}"
            )

        row = AgentLlmEvalFolder(
            organization_id=self.org_id,
            agent_id=agent_id,
            name=cleaned_name,
            description=_clean_optional_text(description),
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
    ) -> AgentLlmEvalFolder:
        """Single-row UPDATE. Snapshot rows on ``agent_llm_eval_results``
        keep the OLD name so history renders as it did at scoring time.
        """
        cleaned = _clean_folder_name(new_name)
        if not cleaned:
            raise EvalConfigurationError("new_name must be non-empty")

        row = self._require_folder(agent_id, folder_id)
        if row.name == cleaned:
            return row

        clash = (
            self.query(AgentLlmEvalFolder)
            .filter(AgentLlmEvalFolder.agent_id == agent_id)
            .filter(AgentLlmEvalFolder.name == cleaned)
            .filter(AgentLlmEvalFolder.id != folder_id)
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
        """Delete the folder row — the DB CASCADE deletes every scenario
        inside it. Past run results (``agent_llm_eval_results``) keep their
        snapshotted folder-name text column, so history remains readable.

        Refuses to delete the LAST remaining folder for an agent — every
        agent must always have at least one folder so ``create_scenario``
        has a valid ``folder_id`` to write.

        Concurrency: two simultaneous delete requests on an agent with
        exactly 2 folders would each see count=2 and both delete without
        a lock — dropping the agent to zero folders. We take a row-level
        ``SELECT ... FOR UPDATE`` on every folder for this agent, which
        serialises concurrent deletes on the same agent.
        """
        from core.models.agent_llm_eval_result import AgentLlmEvalResult

        row = self._require_folder(agent_id, folder_id)

        # Row-lock every folder row for this agent — concurrent deletes
        # now queue behind us instead of check-then-act racing.
        locked = (
            self.query(AgentLlmEvalFolder)
            .filter(AgentLlmEvalFolder.agent_id == agent_id)
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
            .filter(AgentLlmEvalScenario.folder_id == folder_id)
            .count()
        )
        # Count past-run rows tagged with this folder's NAME (snapshot) so
        # the FE toast can quote how many historical rows keep the label.
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

    def _require_folder(
        self, agent_id: UUID, folder_id: UUID
    ) -> AgentLlmEvalFolder:
        row = (
            self.query(AgentLlmEvalFolder)
            .filter(AgentLlmEvalFolder.id == folder_id)
            .filter(AgentLlmEvalFolder.agent_id == agent_id)
            .first()
        )
        if row is None:
            raise AgentLlmEvalFolderNotFoundError(
                f"Folder {folder_id} not found for agent {agent_id}"
            )
        return row

    def _assert_agent_in_org(self, agent_id: UUID) -> None:
        """Cross-tenant leak guard for non-router callers (workers, CLIs,
        seed scripts) whose ``TenantContext`` might not match the target
        agent. Router paths already run ``_ensure_agent_in_org`` so this
        is redundant there — but calling it in the service closes the
        hole for every entry point uniformly.

        Uses ``self.db`` (not ``self.query``) to bypass org scoping so
        we can compare the AGENT's org to OUR context and raise on
        mismatch instead of silently returning None."""
        agent_org = (
            self.db.query(Agent.organization_id)
            .filter(Agent.id == agent_id)
            .scalar()
        )
        if agent_org is None:
            raise EvalConfigurationError(
                f"Agent {agent_id} not found — cannot write folder"
            )
        if self.org_id is not None and str(agent_org) != str(self.org_id):
            raise EvalConfigurationError(
                f"Agent {agent_id} does not belong to organization {self.org_id}"
            )


# ── Helpers ──────────────────────────────────────────────────────────


def _clean_folder_name(value: object) -> str:
    if value is None or not isinstance(value, str):
        return ""
    trimmed = value.strip()
    return trimmed[:120]


def _clean_optional_text(value: object) -> Optional[str]:
    if value is None or not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _is_folder_name_conflict(exc: IntegrityError) -> bool:
    """True when the given ``IntegrityError`` was raised by the UNIQUE
    constraint on ``(agent_id, name)``. Any other integrity violation is a
    different bug that should NOT be hidden behind a "folder exists" message.

    Priority: (1) exact constraint name from psycopg diag; (2) unique-
    violation pgcode 23505 AND constraint name substring — the pgcode gate
    prevents an FK / NOT-NULL violation whose message coincidentally
    mentions the constraint name from being misclassified as a name
    conflict (would surface as 409 to the user and mask a real 5xx).
    """
    orig = getattr(exc, "orig", None)
    diag = getattr(orig, "diag", None)
    constraint_name = getattr(diag, "constraint_name", None)
    if constraint_name is not None:
        return constraint_name == _FOLDER_NAME_CONSTRAINT
    pgcode = getattr(orig, "pgcode", None)
    if pgcode != "23505":  # unique_violation
        return False
    return _FOLDER_NAME_CONSTRAINT in str(exc)


__all__ = [
    "AgentLlmEvalFolderService",
    "FolderRow",
    "DEFAULT_FOLDER_NAME",
]
