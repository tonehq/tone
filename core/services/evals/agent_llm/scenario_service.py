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
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional, Sequence
from uuid import UUID

from loguru import logger
from sqlalchemy import String, bindparam
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.exc import IntegrityError

from core.models.agent_llm_eval_scenario import AgentLlmEvalScenario
from core.services.base import BaseService
from core.services.common.list_query import apply_search_sort_pagination
from core.services.evals.errors import (
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
}


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
        sort_by: Optional[str] = "created_at",
        sort_order: str = "desc",
        page_no: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AgentLlmEvalScenario], int]:
        """Paginated list of scenarios for one agent, with optional search /
        tag filter / whitelisted sort. Reuses ``apply_search_sort_pagination``
        so search / sort / pagination semantics match every other
        ``POST /…/list`` endpoint.
        """
        q = self.query(AgentLlmEvalScenario).filter(
            AgentLlmEvalScenario.agent_id == agent_id
        )

        # Tag filter — JSONB ``?|`` (has-any-of-these-keys) so a scenario
        # with tags = ['booking','happy'] matches when tags param is
        # ['booking'] OR ['pricing','booking']. Skipped when empty.
        clean_tags = [t.strip() for t in (tags or []) if isinstance(t, str) and t.strip()]
        if clean_tags:
            q = q.filter(AgentLlmEvalScenario.tags.op("?|")(_jsonb_text_array(clean_tags)))

        sort_map = {
            "created_at": AgentLlmEvalScenario.created_at,
            "updated_at": AgentLlmEvalScenario.updated_at,
            "scenario_key": AgentLlmEvalScenario.scenario_key,
            "scenario_ord": AgentLlmEvalScenario.scenario_ord,
        }

        return apply_search_sort_pagination(
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

    def get_scenario(self, agent_id: UUID, scenario_id: UUID) -> AgentLlmEvalScenario:
        """Fetch one scenario, org- + agent-scoped. Raises
        ``AgentLlmScenarioNotFoundError`` when the id is missing OR belongs
        to another agent in the same org (agent-mismatch is a 404, not a 403 —
        the caller shouldn't be able to distinguish "wrong agent" from
        "no such row" without another API call)."""
        row = self._require_scenario(agent_id, scenario_id)
        return row

    def load_all_for_run(
        self,
        agent_id: UUID,
        *,
        scenario_ids: Optional[Sequence[UUID]] = None,
        tags: Optional[Sequence[str]] = None,
    ) -> list[AgentLlmEvalScenario]:
        """Every scenario the run should score, ordered by ``scenario_ord``.

        Filters when ``scenario_ids`` OR ``tags`` is provided; otherwise
        returns every scenario for the agent. Kept out of ``list_scenarios``
        so run-eval doesn't accidentally paginate off the 51st scenario.
        """
        q = self.query(AgentLlmEvalScenario).filter(
            AgentLlmEvalScenario.agent_id == agent_id
        )
        if scenario_ids:
            q = q.filter(AgentLlmEvalScenario.id.in_(list(scenario_ids)))
        clean_tags = [t.strip() for t in (tags or []) if isinstance(t, str) and t.strip()]
        if clean_tags:
            q = q.filter(AgentLlmEvalScenario.tags.op("?|")(_jsonb_text_array(clean_tags)))
        return (
            q.order_by(
                AgentLlmEvalScenario.scenario_ord.asc(),
                AgentLlmEvalScenario.created_at.asc(),
            )
            .all()
        )

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

        ``source`` is stamped on every created row so the UI can badge
        manual vs csv vs generated vs fixture inputs identically. It's a
        keyword arg on the SERVICE (not the DTO) so a caller can't spoof
        the provenance of a payload it received from the network.
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

        # Figure out the next ``scenario_ord`` once so bulk imports land
        # after existing rows in display order (rather than at 0 or NULL).
        next_ord = self._next_scenario_ord(agent_id)

        created: list[AgentLlmEvalScenario] = []
        for offset, payload in enumerate(payloads):
            row = AgentLlmEvalScenario(
                # Explicitly stamp the caller's org — the model's default reads
                # a context var (``get_current_org_id``) that isn't guaranteed
                # to be populated for every code path (workers, seed scripts,
                # tests). Setting it here keeps the pre-check
                # (org-scoped ``self.query``) consistent with the INSERT, so
                # a duplicate we DID surface at the pre-check step can't be
                # duplicated via a different-org row that the pre-check missed
                # but the DB constraint (``(agent_id, scenario_key)``, which is
                # NOT org-scoped) still catches.
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
    ) -> "GeneratedBatch":
        """Ask the given generator strategy for ``count`` scenarios.

        When ``dry_run`` is True (the FE preview step), returns the raw
        ``GeneratedScenario`` list without persisting. When False, persists
        via ``create_scenarios_bulk(source='generated')`` — the SAME entry
        point as manual create, so future automated cron jobs use exactly
        the same code path.
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

        payloads = [_generated_to_input(g) for g in generated]
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
    """
    # Local import keeps the CLI fixture module out of any process that
    # never runs an eval (routes that only list scenarios).
    from evals.fixtures.agent_llm_scenarios import LLMScenario

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


def _decode_csv_bytes(raw: bytes) -> str:
    """Tolerant CSV decoding — UTF-8 (BOM-aware for Excel exports), then
    cp1252 / latin-1 so a spreadsheet with a stray non-UTF-8 byte doesn't
    hard-fail. Mirror of the tolerant decoder in ``core/services/evals/csv_import.py``.
    """
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            logger.debug("[agent-llm-eval] CSV not decodable as %s", encoding)
    return raw.decode("utf-8", errors="replace")


def _normalize_header(name: Optional[str]) -> Optional[str]:
    if name is None:
        return None
    key = name.strip().lower().replace(" ", "_")
    return _CSV_HEADER_ALIASES.get(key, key)


def _parse_scenarios_csv(raw: bytes) -> list[dict]:
    text = _decode_csv_bytes(raw)
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = reader.fieldnames or []
    normalized = {_normalize_header(f) for f in fieldnames if f is not None}
    missing = [c for c in _CSV_REQUIRED_COLUMNS if c not in normalized]
    if missing:
        raise EvalConfigurationError(
            f"CSV is missing required column(s): {', '.join(missing)}. "
            f"Expected headers: scenario_key, prompt "
            "(optional: expected_answer, persona_criteria, instruction_criteria, "
            "tags, metrics_override, threshold_override, scenario_ord)."
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
        metrics_override=metrics,
        threshold_override=threshold,
        scenario_ord=scenario_ord,
    )


def _generated_to_input(g: Any) -> ScenarioInput:
    """Convert a ``GeneratedScenario`` into a ``ScenarioInput`` for persist.
    Kept loose (``g: Any``) so this file never imports the generator package
    at module load — the generator, if any, is imported lazily inside
    ``generate_scenarios``."""
    return ScenarioInput(
        scenario_key=g.scenario_key,
        prompt=g.prompt,
        expected_answer=getattr(g, "expected_answer", None),
        persona_criteria=getattr(g, "persona_criteria", None),
        instruction_criteria=getattr(g, "instruction_criteria", None),
        tags=list(getattr(g, "tags", None) or []) or None,
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
