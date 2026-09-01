"""``AgentLlmScenarioService`` — CRUD + CSV import + generation dispatch for
per-agent Level-2 (agent-LLM) eval scenarios.

Transport-agnostic: takes plain args (a SQLAlchemy session + org context via
``BaseService``), returns ORM rows or lightweight dataclasses. The API routes
in ``core/api/v1/agent_llm_evals.py`` are thin adapters over this class; the
CLI seed script (``dev/seed_agent_llm_scenarios.py``) is another adapter.

Every scenario row is:
- **org-scoped** — every query goes through ``self.query()`` so cross-tenant
  reads/writes are impossible (mirror ``BaseService.query``);
- **agent-scoped** — the ``(agent_id, scenario_key)`` UNIQUE + explicit
  ``agent_id`` filter on every read means a valid scenario UUID from another
  agent still 404s.

Errors are TYPED (``AgentLlmScenarioNotFoundError`` /
``AgentLlmScenarioKeyConflictError`` / ``EvalConfigurationError``) — the
route layer maps them to HTTP codes, never the service.

Folder membership is via ``folder_id`` FK to ``agent_llm_eval_folders``.
Every scenario always belongs to a real folder — callers that omit
``folder_id`` fall back to the agent's ``Default`` folder (seeded on
agent-create). Folder writes (create/rename/delete) live on
``AgentLlmEvalFolderService``.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence
from uuid import UUID

from core.services.evals.csv_decode import decode_csv_bytes
from sqlalchemy import String, bindparam
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from core.models.agent_llm_eval_scenario import AgentLlmEvalScenario
from core.services.base import BaseService
from core.services.common.list_query import apply_search_sort_pagination
from core.services.evals.agent_llm.folder_service import (
    DEFAULT_FOLDER_NAME,
    AgentLlmEvalFolderService,
)
from core.services.evals.errors import (
    AgentLlmEvalFolderNotFoundError,
    AgentLlmScenarioKeyConflictError,
    AgentLlmScenarioNotFoundError,
    EvalConfigurationError,
)


# Scenario input shape (used for both create + update; every field is
# optional on update patches). Kept as a dataclass so the same DTO can be
# passed from the route layer, the CSV importer, and the generator without
# any of them needing to know about SQLAlchemy.
@dataclass
class ScenarioInput:
    scenario_key: str
    prompt: str
    expected_answer: Optional[str] = None
    persona_criteria: Optional[str] = None
    instruction_criteria: Optional[str] = None
    tags: Optional[List[str]] = None
    metrics_override: Optional[List[str]] = None
    threshold_override: Optional[float] = None
    scenario_ord: Optional[int] = None
    generation_metadata: Optional[dict] = None
    # First-class folder FK. When ``None``, the service resolves the
    # agent's ``Default`` folder. Callers with an explicit user-picked
    # folder pass ``folder_id`` directly.
    folder_id: Optional[UUID] = None
    # CSV / importer path: the raw folder NAME from the source file.
    # When set (and ``folder_id`` is None), the service resolves-or-creates
    # the folder by name in the same transaction.
    folder_name: Optional[str] = None
    # v2 forward-compat — accepted here so the same payload can be POSTed
    # by a future tool-scoring UI without touching this DTO. Both stay
    # ``None`` for every v1 scenario.
    expected_tools: Optional[Any] = None
    tool_config: Optional[Any] = None


@dataclass
class ScenarioPatch:
    """Per-field update patch. ``None`` means "don't touch"; explicit
    ``__unset__`` sentinel would be needed to clear a nullable — v1 chooses
    the simpler contract: pass an empty string / empty list to clear."""

    prompt: Optional[str] = None
    expected_answer: Optional[str] = None
    persona_criteria: Optional[str] = None
    instruction_criteria: Optional[str] = None
    tags: Optional[List[str]] = None
    metrics_override: Optional[List[str]] = None
    threshold_override: Optional[float] = None
    scenario_ord: Optional[int] = None
    # Renaming a scenario_key is allowed — the UNIQUE constraint on
    # ``(agent_id, scenario_key)`` catches collisions, converted to
    # ``AgentLlmScenarioKeyConflictError`` at the service layer.
    scenario_key: Optional[str] = None
    # Move to a different folder. Every scenario must belong to a real
    # folder — ``None`` here means "don't change"; there is no way to
    # detach a scenario from all folders.
    folder_id: Optional[UUID] = None


_CSV_REQUIRED_COLUMNS = ("scenario_key", "prompt")
_CSV_HEADER_ALIASES = {
    "key": "scenario_key",
    "name": "scenario_key",
    "id": "scenario_key",
    "question": "prompt",
    "user_prompt": "prompt",
    "expected": "expected_answer",
    "persona": "persona_criteria",
    "instruction": "instruction_criteria",
    "instructions": "instruction_criteria",
    "metrics": "metrics_override",
    "threshold": "threshold_override",
    "order": "scenario_ord",
    "ord": "scenario_ord",
}
_CSV_ALLOWED_COLUMNS = {
    "scenario_key",
    "prompt",
    "expected_answer",
    "persona_criteria",
    "instruction_criteria",
    "tags",
    "metrics_override",
    "threshold_override",
    "scenario_ord",
    "folder",
}

# Whitelisted ``source`` values accepted by ``list_scenarios``. Kept in
# sync with the router's Pydantic pattern in ``agent_llm_evals.py`` so
# a service-level typo (e.g. ``'CSV'`` vs ``'csv'``) raises loudly
# instead of silently returning every source.
_SCENARIO_SOURCE_WHITELIST: frozenset[str] = frozenset(
    {"manual", "csv", "generated", "fixture"}
)


class AgentLlmScenarioService(BaseService):
    """Manages ``agent_llm_eval_scenarios`` rows.

    Instantiated per request/task with the caller's org context via
    ``BaseService``. Every read uses ``self.query(AgentLlmEvalScenario)`` so
    cross-tenant scenario access is impossible (no route/task should ever
    query the model directly).
    """

    # ── Read ────────────────────────────────────────────────────────────

    def list_scenarios(
        self,
        agent_id: UUID,
        *,
        search: Optional[str] = None,
        tags: Optional[Sequence[str]] = None,
        folder_id: Optional[UUID] = None,
        source: Optional[str] = None,
        sort_by: Optional[str] = "created_at",
        sort_order: str = "desc",
        page_no: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AgentLlmEvalScenario], int]:
        """Paginated list of scenarios for one agent, with optional search /
        tag filter / folder filter / source filter / whitelisted sort.
        Reuses ``apply_search_sort_pagination`` so search / sort /
        pagination semantics match every other ``POST /…/list`` endpoint.

        ``folder_id`` is an exact-match filter; ``None`` skips the filter
        entirely.
        """
        q = (
            self.query(AgentLlmEvalScenario)
            .options(joinedload(AgentLlmEvalScenario.folder_ref))
            .filter(AgentLlmEvalScenario.agent_id == agent_id)
        )

        # Tag filter — JSONB ``?|`` (has-any-of-these-keys) so a scenario
        # with tags = ['booking','happy'] matches when tags param is
        # ['booking'] OR ['pricing','booking']. Skipped when empty.
        clean_tags = [t.strip() for t in (tags or []) if isinstance(t, str) and t.strip()]
        if clean_tags:
            q = q.filter(AgentLlmEvalScenario.tags.op("?|")(_jsonb_text_array(clean_tags)))

        if folder_id is not None:
            q = q.filter(AgentLlmEvalScenario.folder_id == folder_id)

        # Source filter — reject unknown values loudly instead of silently
        # skipping the filter. Router-level Pydantic pattern already
        # guards HTTP callers; this catches programmatic mistakes
        # (case-sensitive: ``'CSV'`` would previously return every row).
        if source is not None:
            if source not in _SCENARIO_SOURCE_WHITELIST:
                raise EvalConfigurationError(
                    f"Unknown source filter {source!r}; expected one of "
                    f"{sorted(_SCENARIO_SOURCE_WHITELIST)}."
                )
            q = q.filter(AgentLlmEvalScenario.source == source)

        sort_map = {
            "created_at": AgentLlmEvalScenario.created_at,
            "updated_at": AgentLlmEvalScenario.updated_at,
            "scenario_key": AgentLlmEvalScenario.scenario_key,
            "scenario_ord": AgentLlmEvalScenario.scenario_ord,
        }

        rows, total = apply_search_sort_pagination(
            q,
            search=search,
            search_fields=[
                AgentLlmEvalScenario.scenario_key,
                AgentLlmEvalScenario.prompt,
            ],
            sort_by=sort_by,
            sort_order=sort_order,
            sort_map=sort_map,
            page_no=page_no,
            page_size=page_size,
        )
        return rows, total

    def get_scenario(self, agent_id: UUID, scenario_id: UUID) -> AgentLlmEvalScenario:
        """Fetch one scenario, org- + agent-scoped. Raises
        ``AgentLlmScenarioNotFoundError`` when the id is missing OR belongs
        to another agent in the same org (agent-mismatch is a 404, not a 403 —
        the caller shouldn't be able to distinguish "wrong agent" from
        "no such row" without another API call)."""
        return self._require_scenario(agent_id, scenario_id)

    def load_all_for_run(
        self,
        agent_id: UUID,
        *,
        scenario_ids: Optional[Sequence[UUID]] = None,
        tags: Optional[Sequence[str]] = None,
        folder_id: Optional[UUID] = None,
        folder_ids: Optional[Sequence[UUID]] = None,
    ) -> list[AgentLlmEvalScenario]:
        """Every scenario the run should score, ordered by ``scenario_ord``.

        Filters when ``scenario_ids`` / ``tags`` / ``folder_id`` /
        ``folder_ids`` is provided; otherwise returns every scenario for
        the agent.

        ``folder_ids`` (plural, multi-select) takes precedence over
        ``folder_id`` (singular) when both are provided.
        """
        q = (
            self.query(AgentLlmEvalScenario)
            .options(joinedload(AgentLlmEvalScenario.folder_ref))
            .filter(AgentLlmEvalScenario.agent_id == agent_id)
        )
        if scenario_ids:
            q = q.filter(AgentLlmEvalScenario.id.in_(list(scenario_ids)))
        clean_tags = [t.strip() for t in (tags or []) if isinstance(t, str) and t.strip()]
        if clean_tags:
            q = q.filter(AgentLlmEvalScenario.tags.op("?|")(_jsonb_text_array(clean_tags)))
        if folder_ids is not None:
            # ``folder_ids`` explicitly supplied — filter by it (even if
            # empty means "no folders selected → no rows"). Do NOT silently
            # broaden to every scenario when the list is empty or all-None:
            # a caller who asked for a folder filter would rather see zero
            # results than a run scoring every scenario in the agent.
            cleaned_ids = [f for f in folder_ids if f is not None]
            if not cleaned_ids:
                return []
            q = q.filter(AgentLlmEvalScenario.folder_id.in_(cleaned_ids))
        elif folder_id is not None:
            q = q.filter(AgentLlmEvalScenario.folder_id == folder_id)
        rows = (
            q.order_by(
                AgentLlmEvalScenario.scenario_ord.asc(),
                AgentLlmEvalScenario.created_at.asc(),
            )
            .all()
        )
        return rows

    # ── Write ───────────────────────────────────────────────────────────

    def create_scenario(
        self,
        agent_id: UUID,
        payload: ScenarioInput,
        *,
        source: str = "manual",
    ) -> AgentLlmEvalScenario:
        """Create one scenario. Raises ``AgentLlmScenarioKeyConflictError``
        if ``payload.scenario_key`` already exists for this agent."""
        rows = self.create_scenarios_bulk(agent_id, [payload], source=source)
        return rows[0]

    def create_scenarios_bulk(
        self,
        agent_id: UUID,
        payloads: Sequence[ScenarioInput],
        *,
        source: str = "manual",
    ) -> list[AgentLlmEvalScenario]:
        """Insert many scenarios in one transaction. Duplicate ``scenario_key``s
        either WITHIN the payload OR against existing rows raise
        ``AgentLlmScenarioKeyConflictError`` before any INSERT — no partial
        writes.

        Every scenario must land in a real folder — payloads that omit
        ``folder_id`` fall back to the agent's ``Default`` folder;
        payloads that carry a raw ``folder_name`` (CSV path) resolve-or-
        create the folder by name.
        """
        payloads = list(payloads)
        if not payloads:
            return []

        # Fail-fast on within-batch collisions BEFORE hitting the DB — the
        # DB constraint would otherwise catch it, but only after N-1 valid
        # rows had been rendered, and the error message wouldn't name the
        # duplicate key.
        seen: set[str] = set()
        duplicates: set[str] = set()
        for p in payloads:
            key = (p.scenario_key or "").strip()
            if not key:
                raise EvalConfigurationError(
                    "scenario_key is required on every scenario"
                )
            if not (p.prompt or "").strip():
                raise EvalConfigurationError(
                    f"prompt is required on scenario {key!r}"
                )
            if key in seen:
                duplicates.add(key)
            seen.add(key)
        if duplicates:
            raise AgentLlmScenarioKeyConflictError(
                f"Duplicate scenario_key(s) in payload: {sorted(duplicates)}"
            )

        existing_keys = set(
            k
            for (k,) in self.query(AgentLlmEvalScenario)
            .with_entities(AgentLlmEvalScenario.scenario_key)
            .filter(AgentLlmEvalScenario.agent_id == agent_id)
            .filter(AgentLlmEvalScenario.scenario_key.in_(sorted(seen)))
            .all()
        )
        if existing_keys:
            raise AgentLlmScenarioKeyConflictError(
                f"scenario_key(s) already exist for this agent: {sorted(existing_keys)}"
            )

        # Resolve folder_id for every payload BEFORE the INSERT loop so the
        # DB write is a single transaction. Reuse the folder service so
        # "resolve-or-create" logic isn't duplicated here.
        # ``commit=False`` on the folder writes — the outer commit at the
        # bottom of this method finalizes folders + scenarios atomically.
        folder_svc = AgentLlmEvalFolderService(
            self.db, user_id=self.user_id, org_id=self.org_id
        )
        default_folder_id: Optional[UUID] = None
        name_to_id: dict[str, UUID] = {}
        resolved_folder_ids: list[UUID] = []
        for p in payloads:
            if p.folder_id is not None:
                # Validate the folder belongs to this (agent, org).
                folder_svc.get_folder(agent_id, p.folder_id)
                resolved_folder_ids.append(p.folder_id)
                continue
            raw_name = (p.folder_name or "").strip()
            if raw_name:
                cached = name_to_id.get(raw_name)
                if cached is None:
                    folder = folder_svc.get_or_create_folder(
                        agent_id, raw_name, commit=False
                    )
                    cached = folder.id
                    name_to_id[raw_name] = cached
                resolved_folder_ids.append(cached)
                continue
            if default_folder_id is None:
                default_folder_id = folder_svc.get_or_create_folder(
                    agent_id, DEFAULT_FOLDER_NAME, commit=False
                ).id
            resolved_folder_ids.append(default_folder_id)

        # Figure out the next ``scenario_ord`` once so bulk imports land
        # after existing rows in display order (rather than at 0 or NULL).
        next_ord = self._next_scenario_ord(agent_id)

        created: list[AgentLlmEvalScenario] = []
        for offset, (payload, folder_id) in enumerate(
            zip(payloads, resolved_folder_ids)
        ):
            row = AgentLlmEvalScenario(
                organization_id=self.org_id,
                agent_id=agent_id,
                scenario_key=payload.scenario_key.strip(),
                scenario_ord=(
                    payload.scenario_ord
                    if payload.scenario_ord is not None
                    else next_ord + offset
                ),
                prompt=payload.prompt.strip(),
                expected_answer=_clean_optional_text(payload.expected_answer),
                persona_criteria=_clean_optional_text(payload.persona_criteria),
                instruction_criteria=_clean_optional_text(payload.instruction_criteria),
                tags=_clean_string_list(payload.tags),
                folder_id=folder_id,
                metrics_override=_clean_string_list(payload.metrics_override),
                threshold_override=payload.threshold_override,
                source=source,
                generation_metadata=payload.generation_metadata,
                expected_tools=payload.expected_tools,
                tool_config=payload.tool_config,
            )
            self.db.add(row)
            created.append(row)

        try:
            self.db.commit()
        except IntegrityError as exc:
            # Only wrap when the DB actually hit our UNIQUE constraint —
            # otherwise a FK / CHECK / NOT-NULL violation would show up as a
            # misleading "scenario_key exists" message and mask the real bug.
            self.db.rollback()
            if not _is_scenario_key_conflict(exc):
                raise
            offending = set(
                k
                for (k,) in self.db.query(AgentLlmEvalScenario.scenario_key)
                .filter(AgentLlmEvalScenario.agent_id == agent_id)
                .filter(AgentLlmEvalScenario.scenario_key.in_(sorted(seen)))
                .all()
            )
            if offending:
                raise AgentLlmScenarioKeyConflictError(
                    f"scenario_key(s) already exist for this agent: {sorted(offending)}"
                ) from exc
            raise AgentLlmScenarioKeyConflictError(
                "scenario_key collision on insert (concurrent write)"
            ) from exc

        for row in created:
            # ``folder_ref`` will load lazily on first access in ``to_dict``.
            self.db.refresh(row)
        return created

    def update_scenario(
        self,
        agent_id: UUID,
        scenario_id: UUID,
        patch: ScenarioPatch,
    ) -> AgentLlmEvalScenario:
        """Apply ``patch`` to one scenario. Only fields with non-``None``
        values on the patch are touched — the router should NOT pre-fill
        omitted fields with the current row (that would silently overwrite
        concurrent edits)."""
        row = self._require_scenario(agent_id, scenario_id)

        # Handle scenario_key rename with the same conflict-check semantics
        # as create — otherwise the UNIQUE constraint fires and the user
        # sees an opaque IntegrityError.
        if patch.scenario_key is not None:
            new_key = patch.scenario_key.strip()
            if not new_key:
                raise EvalConfigurationError("scenario_key must be non-empty")
            if new_key != row.scenario_key:
                clash = (
                    self.query(AgentLlmEvalScenario)
                    .filter(AgentLlmEvalScenario.agent_id == agent_id)
                    .filter(AgentLlmEvalScenario.scenario_key == new_key)
                    .filter(AgentLlmEvalScenario.id != scenario_id)
                    .first()
                )
                if clash is not None:
                    raise AgentLlmScenarioKeyConflictError(
                        f"scenario_key {new_key!r} already exists for this agent"
                    )
                row.scenario_key = new_key

        if patch.prompt is not None:
            cleaned = patch.prompt.strip()
            if not cleaned:
                raise EvalConfigurationError("prompt must be non-empty")
            row.prompt = cleaned

        if patch.expected_answer is not None:
            row.expected_answer = _clean_optional_text(patch.expected_answer)
        if patch.persona_criteria is not None:
            row.persona_criteria = _clean_optional_text(patch.persona_criteria)
        if patch.instruction_criteria is not None:
            row.instruction_criteria = _clean_optional_text(patch.instruction_criteria)
        if patch.tags is not None:
            row.tags = _clean_string_list(patch.tags)
        if patch.folder_id is not None:
            # Validate the folder belongs to this (agent, org).
            folder_svc = AgentLlmEvalFolderService(
                self.db, user_id=self.user_id, org_id=self.org_id
            )
            folder_svc.get_folder(agent_id, patch.folder_id)
            row.folder_id = patch.folder_id
        if patch.metrics_override is not None:
            row.metrics_override = _clean_string_list(patch.metrics_override)
        if patch.threshold_override is not None:
            # Sentinel to allow clearing: caller passes -1 (invalid ratio).
            # Otherwise the value is validated in (0.0, 1.0].
            if patch.threshold_override < 0:
                row.threshold_override = None
            elif not (0.0 < float(patch.threshold_override) <= 1.0):
                raise EvalConfigurationError(
                    "threshold_override must be in (0.0, 1.0] (or -1 to clear)"
                )
            else:
                row.threshold_override = float(patch.threshold_override)
        if patch.scenario_ord is not None:
            row.scenario_ord = int(patch.scenario_ord)

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            if not _is_scenario_key_conflict(exc):
                raise  # not our UNIQUE constraint — bubble up the real cause
            attempted_key = (patch.scenario_key or row.scenario_key or "").strip()
            raise AgentLlmScenarioKeyConflictError(
                f"scenario_key {attempted_key!r} already exists for this agent"
                if attempted_key
                else "scenario_key collision on update (concurrent write)"
            ) from exc

        self.db.refresh(row)
        return row

    def delete_scenario(self, agent_id: UUID, scenario_id: UUID) -> None:
        """Hard-delete one scenario. Historical ``agent_llm_eval_results``
        rows keep their own snapshotted prompt/expected_answer, so past
        runs remain fully explainable after the source scenario is gone.
        """
        row = self._require_scenario(agent_id, scenario_id)
        self.db.delete(row)
        self.db.commit()

    def delete_scenarios_bulk(
        self,
        agent_id: UUID,
        scenario_ids: Sequence[UUID],
    ) -> int:
        """Hard-delete every scenario in ``scenario_ids`` that belongs to
        ``agent_id`` (and, transitively via ``BaseService.query``, to this
        service's org). Returns the number of rows removed.

        Ids that don't belong to this (agent, org) — a stale UI cache or
        a forged request — are silently ignored: the ``.filter()`` chain
        already scopes the query so the delete only sees the caller's
        rows. Same history-preservation semantics as :meth:`delete_scenario`
        — past run results keep their snapshotted prompt/expected_answer.

        Empty ``scenario_ids`` is a no-op returning ``0`` (avoids issuing
        a ``WHERE id IN ()`` query that some drivers reject).
        """
        ids = [i for i in scenario_ids if i is not None]
        if not ids:
            return 0
        deleted = (
            self.query(AgentLlmEvalScenario)
            .filter(AgentLlmEvalScenario.agent_id == agent_id)
            .filter(AgentLlmEvalScenario.id.in_(ids))
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return int(deleted)

    # ── CSV import ──────────────────────────────────────────────────────

    def import_from_csv(
        self,
        agent_id: UUID,
        csv_bytes: bytes,
    ) -> list[AgentLlmEvalScenario]:
        """Parse a CSV upload → create scenarios with ``source='csv'``.

        Delegates parse errors to ``EvalConfigurationError`` so the route
        maps them to HTTP 400 with the exact reason. Row validation
        (empty ``prompt``, duplicate keys, …) reuses the same checks as
        the manual create path — one implementation of the rules.
        Folder names referenced by rows are resolve-or-created by
        ``create_scenarios_bulk`` so a CSV column ``folder=Support`` lands
        the row in a (new or existing) Support folder.
        """
        parsed = _parse_scenarios_csv(csv_bytes)
        payloads = [_csv_row_to_input(r) for r in parsed]
        return self.create_scenarios_bulk(agent_id, payloads, source="csv")

    # ── Generation dispatch ─────────────────────────────────────────────

    def generate_scenarios(
        self,
        agent_id: UUID,
        *,
        strategy: str = "noop",
        count: int = 10,
        dry_run: bool = True,
        options: Optional[dict] = None,
        folder_id: Optional[UUID] = None,
    ) -> "GeneratedBatch":
        """Ask the given generator strategy for ``count`` scenarios.

        When ``dry_run`` is True (the FE preview step), returns the raw
        ``GeneratedScenario`` list without persisting. When False, persists
        via ``create_scenarios_bulk(source='generated')`` — the SAME entry
        point as manual create, so future automated cron jobs use exactly
        the same code path.

        ``folder_id`` (when non-None) is stamped on every persisted
        scenario so a "Generate into this folder" flow lands N rows
        organized from the start. When omitted, the create path resolves
        the agent's ``Default`` folder.
        """
        # Local import — the scenario_generation package is lightweight but
        # importing it lazily keeps the CLI (which never generates) fast.
        from core.services.evals.agent_llm.scenario_generation import (
            get_scenario_generator,
        )

        generator = get_scenario_generator(strategy)
        generated = list(
            generator.generate(
                self.db,
                agent_id,
                count=count,
                options=options or {},
            )
        )

        if dry_run or not generated:
            return GeneratedBatch(
                strategy=strategy,
                generated=generated,
                persisted=[],
                note=(
                    "Generator returned no scenarios (dry_run or empty result)"
                    if not generated
                    else None
                ),
            )

        payloads = [_generated_to_input(g, folder_id=folder_id) for g in generated]
        persisted = self.create_scenarios_bulk(
            agent_id, payloads, source="generated"
        )
        return GeneratedBatch(
            strategy=strategy,
            generated=generated,
            persisted=persisted,
        )

    # ── Internals ───────────────────────────────────────────────────────

    def _require_scenario(
        self, agent_id: UUID, scenario_id: UUID
    ) -> AgentLlmEvalScenario:
        row = (
            self.query(AgentLlmEvalScenario)
            .filter(AgentLlmEvalScenario.id == scenario_id)
            .filter(AgentLlmEvalScenario.agent_id == agent_id)
            .first()
        )
        if row is None:
            raise AgentLlmScenarioNotFoundError(
                f"Scenario {scenario_id} not found for agent {agent_id}"
            )
        return row

    def _next_scenario_ord(self, agent_id: UUID) -> int:
        from sqlalchemy import func

        row = (
            self.query(AgentLlmEvalScenario)
            .with_entities(func.coalesce(func.max(AgentLlmEvalScenario.scenario_ord), -1) + 1)
            .filter(AgentLlmEvalScenario.agent_id == agent_id)
            .scalar()
        )
        return int(row or 0)

# ── Helpers exposed to callers (eval runner uses the row → LLMScenario one) ──


def scenario_row_to_llm_scenario(row: AgentLlmEvalScenario) -> Any:
    """Convert a persisted scenario row to the in-memory ``LLMScenario``
    dataclass ``AgentLlmEvalService.run_eval`` expects.

    Lives in this file (not in the run service) so the two representations
    stay 1:1 — a new field on ``AgentLlmEvalScenario`` is one edit here
    and one on the dataclass, never scattered across every call site.

    ``metrics_override`` on the row maps to ``metrics`` on the scenario
    (the dataclass field is named after the CLI usage, not the DB column).

    The ``folder`` field on the dataclass carries the folder NAME
    (the runner snapshots it into ``agent_llm_eval_results.folder``).
    Callers should have loaded the ``folder_ref`` relationship (e.g. via
    ``joinedload`` in ``list_scenarios`` / ``load_all_for_run``); if the
    relationship isn't loaded we fall back to None rather than firing a
    lazy query on a possibly-closed session.
    """
    # Local import keeps the CLI fixture module out of any process that
    # never runs an eval (routes that only list scenarios).
    from evals.fixtures.agent_llm_scenarios import LLMScenario

    folder_name: Optional[str] = None
    try:
        folder_row = row.folder_ref
        if folder_row is not None:
            folder_name = folder_row.name
    except Exception:  # noqa: BLE001 — detached / expired instance
        folder_name = None

    return LLMScenario(
        name=row.scenario_key,
        prompt=row.prompt,
        expected_answer=row.expected_answer,
        metrics=list(row.metrics_override) if row.metrics_override else None,
        threshold=(
            float(row.threshold_override) if row.threshold_override is not None else None
        ),
        persona_criteria=row.persona_criteria,
        instruction_criteria=row.instruction_criteria,
        tags=list(row.tags) if row.tags else [],
        folder=folder_name,
        # Tool-aware fields — forward the persisted JSONB verbatim; the
        # deterministic ``tool_selection`` metric consumes it (see
        # ``core.services.evals.agent_llm.tool_selection_metric``). ``None``
        # for text-only scenarios so v1 scoring is byte-identical.
        expected_tools=list(row.expected_tools) if row.expected_tools else None,
    )


@dataclass
class GeneratedBatch:
    """Return value of ``generate_scenarios`` — describes what a strategy
    proposed AND what (if anything) was persisted."""

    strategy: str
    generated: list  # list[GeneratedScenario] — kept loose to avoid a hard import
    persisted: list[AgentLlmEvalScenario] = field(default_factory=list)
    note: Optional[str] = None


# ── Private helpers ─────────────────────────────────────────────────────


_SCENARIO_KEY_CONSTRAINT = "uq_agent_llm_eval_scenarios_agent_key"


def _is_scenario_key_conflict(exc: IntegrityError) -> bool:
    """True when the given ``IntegrityError`` was raised by the UNIQUE
    constraint on ``(agent_id, scenario_key)``. Any other integrity
    violation (FK, CHECK, NOT NULL) is a different bug that should NOT be
    hidden behind a "scenario_key exists" message. Inspection uses the
    Postgres psycopg diagnostic where available and falls back to a
    substring match on the exception message for drivers that don't
    surface ``diag``."""
    orig = getattr(exc, "orig", None)
    diag = getattr(orig, "diag", None)
    constraint_name = getattr(diag, "constraint_name", None)
    if constraint_name:
        return constraint_name == _SCENARIO_KEY_CONSTRAINT
    return _SCENARIO_KEY_CONSTRAINT in str(exc)


def _jsonb_text_array(values: Sequence[str]):
    """Bind a Python list as a Postgres ``text[]`` so JSONB's ``?|`` operator
    accepts it — otherwise SQLAlchemy may render the list as a JSON array,
    and Postgres raises ``operator does not exist: jsonb ?| jsonb``. The
    bind name is left unset so SQLAlchemy generates a unique one — otherwise
    a query that filters by two tag sets in one statement would collide."""
    return bindparam(key=None, value=list(values), type_=ARRAY(String))


def _clean_optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    return None


def _clean_string_list(value: Any) -> Optional[list[str]]:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        cleaned = [str(v).strip() for v in value if isinstance(v, str) and str(v).strip()]
        return cleaned or None
    return None


def _normalize_header(name: Optional[str]) -> Optional[str]:
    if name is None:
        return None
    key = name.strip().lower().replace(" ", "_")
    return _CSV_HEADER_ALIASES.get(key, key)


def _parse_scenarios_csv(raw: bytes) -> list[dict]:
    text = decode_csv_bytes(raw, log_tag="[agent-llm-eval]")
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = reader.fieldnames or []
    normalized = {_normalize_header(f) for f in fieldnames if f is not None}
    missing = [c for c in _CSV_REQUIRED_COLUMNS if c not in normalized]
    if missing:
        raise EvalConfigurationError(
            f"CSV is missing required column(s): {', '.join(missing)}. "
            f"Expected headers: scenario_key, prompt "
            "(optional: expected_answer, persona_criteria, instruction_criteria, "
            "tags, metrics_override, threshold_override, scenario_ord, folder)."
        )

    rows: list[dict] = []
    for raw_row in reader:
        cleaned: dict = {}
        for k, v in raw_row.items():
            col = _normalize_header(k)
            if col is None or col not in _CSV_ALLOWED_COLUMNS:
                continue
            if v is None:
                continue
            if isinstance(v, list):
                # csv.DictReader over-hands overflow cells; drop them.
                continue
            trimmed = v.strip()
            if trimmed:
                cleaned[col] = trimmed
        if cleaned:
            rows.append(cleaned)
    if not rows:
        raise EvalConfigurationError("CSV contains no data rows.")
    return rows


def _csv_row_to_input(row: dict) -> ScenarioInput:
    """Coerce parsed CSV strings into a ``ScenarioInput``. Rejects rows
    missing ``scenario_key`` / ``prompt`` (redundant with the header check
    but catches per-row blank cells)."""
    key = (row.get("scenario_key") or "").strip()
    prompt = (row.get("prompt") or "").strip()
    if not key or not prompt:
        raise EvalConfigurationError(
            f"CSV row missing scenario_key or prompt: {row!r}"
        )

    tags = _split_csv_list(row.get("tags"))
    metrics = _split_csv_list(row.get("metrics_override"))
    threshold = _parse_optional_float(row.get("threshold_override"))
    scenario_ord = _parse_optional_int(row.get("scenario_ord"))

    return ScenarioInput(
        scenario_key=key,
        prompt=prompt,
        expected_answer=(row.get("expected_answer") or None),
        persona_criteria=(row.get("persona_criteria") or None),
        instruction_criteria=(row.get("instruction_criteria") or None),
        tags=tags,
        folder_name=(row.get("folder") or None),
        metrics_override=metrics,
        threshold_override=threshold,
        scenario_ord=scenario_ord,
    )


def _generated_to_input(g: Any, *, folder_id: Optional[UUID] = None) -> ScenarioInput:
    """Convert a ``GeneratedScenario`` into a ``ScenarioInput`` for persist.
    Kept loose (``g: Any``) so this file never imports the generator package
    at module load — the generator, if any, is imported lazily inside
    ``generate_scenarios``.

    ``folder_id`` is stamped from the caller (the "Generate into folder X"
    picker); generators never invent a folder themselves.
    """
    return ScenarioInput(
        scenario_key=g.scenario_key,
        prompt=g.prompt,
        expected_answer=getattr(g, "expected_answer", None),
        persona_criteria=getattr(g, "persona_criteria", None),
        instruction_criteria=getattr(g, "instruction_criteria", None),
        tags=list(getattr(g, "tags", None) or []) or None,
        folder_id=folder_id,
        generation_metadata=getattr(g, "generation_metadata", None),
        # Forward tool-aware fields when the generator populated them
        # (Phase 2). ``None`` for text-only scenarios — persistence stores
        # NULL, and the deterministic ``tool_selection`` metric skips.
        expected_tools=getattr(g, "expected_tools", None),
    )


def _split_csv_list(value: Optional[str]) -> Optional[list[str]]:
    if value is None:
        return None
    parts = [p.strip() for p in value.split(",") if p and p.strip()]
    return parts or None


def _parse_optional_float(value: Optional[str]) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise EvalConfigurationError(
            f"threshold_override must be a number in (0, 1]; got {value!r}"
        ) from exc


def _parse_optional_int(value: Optional[str]) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise EvalConfigurationError(
            f"scenario_ord must be an integer; got {value!r}"
        ) from exc


__all__ = [
    "AgentLlmScenarioService",
    "ScenarioInput",
    "ScenarioPatch",
    "GeneratedBatch",
    "scenario_row_to_llm_scenario",
]
