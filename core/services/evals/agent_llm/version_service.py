"""``AgentLlmEvalVersionService`` — versioned generation + human review for
per-agent LLM eval scenarios.

Each auto-generation is a **version** (``agent_llm_eval_scenario_versions``):
scenarios are saved as ``approval_status='pending'`` under a ``draft`` version
for review; approve keeps them, reject deletes the row (ignored evals are
never stored), approve-all finalizes the version. Runs are tied to a version
and score only its approved scenarios.

Mirrors the RAG ``EvalService`` version lifecycle
(``generate_version`` / ``list_versions`` / ``approve_*`` / ``reject_*``),
adapted to the agent-scoped domain. Transport-agnostic: the API routes in
``core/api/v1/agent_llm_evals.py`` are thin adapters over this class; errors
are TYPED so the route maps them to HTTP codes.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import case, func

from core.models.agent_llm_eval_result import AgentLlmEvalResult
from core.models.agent_llm_eval_run import AgentLlmEvalRun
from core.models.agent_llm_eval_scenario import AgentLlmEvalScenario
from core.models.agent_llm_eval_scenario_version import AgentLlmEvalScenarioVersion
from core.services.base import BaseService
from core.services.evals.agent_llm.folder_service import assert_agent_in_org
from core.services.evals.agent_llm.scenario_service import AgentLlmScenarioService
from core.services.evals.errors import (
    AgentLlmEvalConfigError,
    AgentLlmEvalVersionGeneratingError,
    AgentLlmEvalVersionHasRunsError,
    AgentLlmEvalVersionNotFoundError,
    AgentLlmScenarioNotFoundError,
    EvalGenerationError,
)

# User-safe reason surfaced on a version when its background generation doesn't
# complete — never the raw exception (which may leak provider/model internals).
# One voice for both failure points: the worker (generation raised) and the
# route (enqueue raised), so the UI reads the same message either way.
GENERATION_FAILED_MESSAGE = (
    "We couldn't generate scenarios this time. Please try again in a moment."
)


@dataclass
class GeneratedVersion:
    """Return value of :meth:`AgentLlmEvalVersionService.generate` — the draft
    version plus the pending scenarios awaiting review."""

    version: AgentLlmEvalScenarioVersion
    scenarios: list[AgentLlmEvalScenario]


class AgentLlmEvalVersionService(BaseService):
    """Manages ``agent_llm_eval_scenario_versions`` rows + the review
    lifecycle of their scenarios. Every read/write is org-scoped via
    ``BaseService`` so cross-tenant access is impossible.
    """

    _GENERATION_STRATEGY = "llm"

    # ── Generation ──────────────────────────────────────────────────────

    def generate(
        self,
        agent_id: UUID,
        *,
        mode: str = "new",
        version_id: Optional[UUID] = None,
        parent_id: Optional[UUID] = None,
        generation_prompt: Optional[str] = None,
        count: int = 10,
    ) -> GeneratedVersion:
        """Generate scenarios into a VERSION (synchronous — CLI / tests).

        Runs both phases back-to-back so the SAME logic backs the background
        path: :meth:`begin_generation` creates/reserves the ``generating``
        version, then :meth:`run_generation` produces the scenarios and flips it
        to ``draft`` (or ``failed``). ``raise_on_error=True`` here so a sync
        caller still sees a generation failure (the worker swallows + persists
        ``failed`` instead). The API route splits the two phases across a
        Procrastinate boundary rather than calling this.
        """
        version = self.begin_generation(
            agent_id,
            mode=mode,
            version_id=version_id,
            generation_prompt=generation_prompt,
        )
        self.run_generation(
            version.id, count=count, parent_id=parent_id, raise_on_error=True
        )
        self.db.refresh(version)
        scenarios = (
            self.query(AgentLlmEvalScenario)
            .filter(AgentLlmEvalScenario.agent_id == agent_id)
            .filter(AgentLlmEvalScenario.version_id == version.id)
            .filter(AgentLlmEvalScenario.node_type == "scenario")
            .order_by(AgentLlmEvalScenario.scenario_ord.asc())
            .all()
        )
        return GeneratedVersion(version=version, scenarios=list(scenarios))

    def begin_generation(
        self,
        agent_id: UUID,
        *,
        mode: str = "new",
        version_id: Optional[UUID] = None,
        generation_prompt: Optional[str] = None,
    ) -> AgentLlmEvalScenarioVersion:
        """Phase 1 (synchronous, pre-enqueue): validate + create/reserve the
        target version in ``status='generating'`` so the FE can show a live
        "Generating…" indicator the moment the request returns.

        ``mode='new'`` allocates the next version; ``mode='overwrite'`` reuses
        ``version_id`` — refused once the version has been run (has-runs) or
        while a generation is already in flight (concurrency). Overwrite KEEPS
        the existing scenarios; the worker swaps them only once new ones are in
        hand, so a failed regenerate never loses reviewed drafts. Raises typed
        errors the route maps to HTTP codes.
        """
        if mode not in {"new", "overwrite"}:
            raise EvalGenerationError(f"mode must be 'new' or 'overwrite'; got {mode!r}")
        self._assert_agent_in_org(agent_id)
        cleaned_prompt = (generation_prompt or "").strip() or None
        return self._resolve_generation_version(
            agent_id,
            mode=mode,
            version_id=version_id,
            generation_prompt=cleaned_prompt,
        )

    def run_generation(
        self,
        version_id: UUID,
        *,
        count: int = 10,
        parent_id: Optional[UUID] = None,
        raise_on_error: bool = False,
    ) -> None:
        """Phase 2 (background worker / sync tail): produce scenarios for a
        ``generating`` version and flip it to ``draft`` — or ``failed`` with a
        user-safe reason.

        Idempotent for Procrastinate replays: a version no longer ``generating``
        (a prior attempt already finished) is a no-op. Generation runs IN-MEMORY
        first (``dry_run=True``); only once the new scenarios are in hand are the
        old ones deleted and replaced — one ``create_scenarios_bulk`` commit
        flushes the delete, the inserts, and the version's ``draft`` flip
        together, so a failure never destroys previously-reviewed drafts.
        """
        version = (
            self.query(AgentLlmEvalScenarioVersion)
            .filter(AgentLlmEvalScenarioVersion.id == version_id)
            .first()
        )
        if version is None:
            raise AgentLlmEvalVersionNotFoundError(f"Version {version_id} not found")
        if version.status != "generating":
            logger.info(
                "[agent-llm-eval] skip generation version_id={} status={} "
                "(not generating — replay no-op)",
                version_id, version.status,
            )
            return

        agent_id = version.agent_id
        cleaned_prompt = (version.generation_prompt or "").strip() or None
        scenarios_svc = AgentLlmScenarioService(
            self.db, user_id=self.user_id, org_id=self.org_id
        )
        try:
            options = {"generation_prompt": cleaned_prompt} if cleaned_prompt else {}
            batch = scenarios_svc.generate_scenarios(
                agent_id,
                strategy=self._GENERATION_STRATEGY,
                count=count,
                dry_run=True,
                options=options,
            )
            generated = list(batch.generated)
            if not generated:
                raise EvalGenerationError("Generator returned no scenarios")

            # Atomic swap, all in one transaction: stage the delete of the old
            # scenarios + the version's ``draft`` flip, insert the new
            # scenarios, then commit once. The trailing ``commit`` is explicit
            # so persistence never depends on whether ``persist_generated`` /
            # ``create_scenarios_bulk`` commits internally — if it already did,
            # this is a no-op; if it ever stops, the staged delete + flip still
            # land together here. The pending delete autoflushes ahead of the
            # bulk-create's key-conflict check, so recurring keys don't clash.
            self.query(AgentLlmEvalScenario).filter(
                AgentLlmEvalScenario.agent_id == agent_id,
                AgentLlmEvalScenario.version_id == version.id,
                AgentLlmEvalScenario.node_type == "scenario",
            ).delete(synchronize_session=False)
            version.status = "draft"
            version.generation_error = None
            version.generation_prompt_hash = _prompt_hash(cleaned_prompt)
            version.generated_by_model = _model_from_persisted(generated)
            persisted = scenarios_svc.persist_generated(
                agent_id,
                generated,
                folder_id=parent_id,
                version_id=version.id,
                approval_status="pending",
            )
            self.db.commit()
            self.db.refresh(version)
            logger.info(
                "[agent-llm-eval] generated version agent={} version_id={} "
                "number={} scenarios={}",
                agent_id, version.id, version.version_number, len(persisted),
            )
        except Exception:
            logger.exception(
                "[agent-llm-eval] generation failed agent={} version_id={}",
                agent_id, version_id,
            )
            self.db.rollback()
            self.fail_generation(version_id, GENERATION_FAILED_MESSAGE)
            if raise_on_error:
                raise

    def fail_generation(
        self, version_id: UUID, error: str
    ) -> Optional[AgentLlmEvalScenarioVersion]:
        """Flip a version to ``failed`` with a user-safe reason (never the raw
        exception). Org-scoped; ``None`` if the row is gone. Used by the worker
        on a generation failure and by the route when enqueue itself fails, so a
        version never stays stuck in ``generating``."""
        version = (
            self.query(AgentLlmEvalScenarioVersion)
            .filter(AgentLlmEvalScenarioVersion.id == version_id)
            .first()
        )
        if version is None:
            return None
        version.status = "failed"
        version.generation_error = (error or "").strip()[:500] or None
        self.db.commit()
        self.db.refresh(version)
        logger.info(
            "[agent-llm-eval] version generation failed version_id={}", version_id
        )
        return version

    # ── Review ──────────────────────────────────────────────────────────

    def approve_scenario(
        self, agent_id: UUID, scenario_id: UUID
    ) -> AgentLlmEvalScenario:
        """Approve one pending scenario — it joins the version's scored set."""
        row = self._require_scenario(agent_id, scenario_id)
        row.approval_status = "approved"
        self.db.commit()
        self.db.refresh(row)
        logger.info(
            "[agent-llm-eval] approved scenario agent={} id={} version={}",
            agent_id, row.id, row.version_id,
        )
        return row

    def reject_scenario(self, agent_id: UUID, scenario_id: UUID) -> None:
        """Reject one scenario — DELETE the row (ignored evals are not stored)."""
        row = self._require_scenario(agent_id, scenario_id)
        version_id = row.version_id
        self.db.delete(row)
        self.db.commit()
        logger.info(
            "[agent-llm-eval] rejected (deleted) scenario agent={} id={} version={}",
            agent_id, scenario_id, version_id,
        )

    def approve_all(self, agent_id: UUID, version_id: UUID) -> int:
        """Approve every pending scenario in a version and finalize it."""
        version = self._require_version(agent_id, version_id)
        n = (
            self.query(AgentLlmEvalScenario)
            .filter(AgentLlmEvalScenario.agent_id == agent_id)
            .filter(AgentLlmEvalScenario.version_id == version_id)
            .filter(AgentLlmEvalScenario.node_type == "scenario")
            .filter(AgentLlmEvalScenario.approval_status == "pending")
            .update({AgentLlmEvalScenario.approval_status: "approved"}, synchronize_session=False)
        )
        version.status = "finalized"
        self.db.commit()
        logger.info(
            "[agent-llm-eval] approved all ({}) in version={}", n, version_id
        )
        return int(n)

    def reject_all(self, agent_id: UUID, version_id: UUID) -> int:
        """Reject (delete) every pending scenario in a version. Approved
        scenarios are kept; rejected ones are not stored."""
        self._require_version(agent_id, version_id)
        n = (
            self.query(AgentLlmEvalScenario)
            .filter(AgentLlmEvalScenario.agent_id == agent_id)
            .filter(AgentLlmEvalScenario.version_id == version_id)
            .filter(AgentLlmEvalScenario.node_type == "scenario")
            .filter(AgentLlmEvalScenario.approval_status == "pending")
            .delete(synchronize_session=False)
        )
        self.db.commit()
        logger.info(
            "[agent-llm-eval] rejected (deleted) all ({}) in version={}", n, version_id
        )
        return int(n)

    # ── Read ────────────────────────────────────────────────────────────

    def list_versions(self, agent_id: UUID) -> list[dict]:
        """Every version for an agent (newest first) with per-version approval
        counts and a ``has_results`` flag (whether it's been run — overwrite is
        blocked once true). One grouped query each; no N+1."""
        versions = (
            self.query(AgentLlmEvalScenarioVersion)
            .filter(AgentLlmEvalScenarioVersion.agent_id == agent_id)
            .order_by(AgentLlmEvalScenarioVersion.version_number.desc())
            .all()
        )
        if not versions:
            return []
        version_ids = [v.id for v in versions]
        count_rows = (
            self.query(AgentLlmEvalScenario)
            .with_entities(
                AgentLlmEvalScenario.version_id,
                func.count(AgentLlmEvalScenario.id),
                func.sum(
                    case((AgentLlmEvalScenario.approval_status == "approved", 1), else_=0)
                ),
            )
            .filter(AgentLlmEvalScenario.version_id.in_(version_ids))
            .filter(AgentLlmEvalScenario.node_type == "scenario")
            .group_by(AgentLlmEvalScenario.version_id)
            .all()
        )
        counts = {
            vid: (int(total or 0), int(approved or 0))
            for vid, total, approved in count_rows
        }
        with_results = {
            r[0]
            for r in self.query(AgentLlmEvalRun)
            .with_entities(AgentLlmEvalRun.version_id)
            .filter(AgentLlmEvalRun.version_id.in_(version_ids))
            .distinct()
            .all()
        }
        out: list[dict] = []
        for v in versions:
            total, approved = counts.get(v.id, (0, 0))
            d = v.to_dict()
            d["counts"] = {
                "total": total,
                "approved": approved,
                "pending": total - approved,
            }
            d["has_results"] = v.id in with_results
            out.append(d)
        return out

    # ── Internals ───────────────────────────────────────────────────────

    def _resolve_generation_version(
        self,
        agent_id: UUID,
        *,
        mode: str,
        version_id: Optional[UUID],
        generation_prompt: Optional[str],
    ) -> AgentLlmEvalScenarioVersion:
        """Create (``new``) or reserve (``overwrite``) the target version in
        ``status='generating'``.

        Overwrite is refused once a version has been run (has-runs) or while a
        generation is already in flight (concurrency). The existing scenarios
        are PRESERVED — the worker swaps them only once new ones are ready — so
        a failed regenerate keeps the previously-reviewed drafts intact."""
        if mode == "overwrite":
            if version_id is None:
                raise EvalGenerationError(
                    "version_id is required when mode='overwrite'"
                )
            version = self._require_version(agent_id, version_id)
            if version.status == "generating":
                raise AgentLlmEvalVersionGeneratingError(
                    "This version is already generating scenarios — wait for it "
                    "to finish before regenerating."
                )
            if self._version_has_runs(agent_id, version_id):
                raise AgentLlmEvalVersionHasRunsError(
                    "This version has already been run — create a new version "
                    "instead of overwriting it."
                )
            # Atomic flip to 'generating' (the FE also disables the button, but
            # a double-fire / forged request must not start two jobs on one
            # version). ``status != 'generating'`` is the guard predicate.
            flipped = (
                self.query(AgentLlmEvalScenarioVersion)
                .filter(AgentLlmEvalScenarioVersion.id == version_id)
                .filter(AgentLlmEvalScenarioVersion.agent_id == agent_id)
                .filter(AgentLlmEvalScenarioVersion.status != "generating")
                .update(
                    {
                        AgentLlmEvalScenarioVersion.status: "generating",
                        AgentLlmEvalScenarioVersion.source: "generated",
                        AgentLlmEvalScenarioVersion.generation_prompt: generation_prompt,
                        AgentLlmEvalScenarioVersion.generation_error: None,
                    },
                    synchronize_session=False,
                )
            )
            if not flipped:
                raise AgentLlmEvalVersionGeneratingError(
                    "This version is already generating scenarios — wait for it "
                    "to finish before regenerating."
                )
            self.db.commit()
            self.db.refresh(version)
            return version

        next_number = int(
            self.query(AgentLlmEvalScenarioVersion)
            .with_entities(
                func.coalesce(func.max(AgentLlmEvalScenarioVersion.version_number), 0) + 1
            )
            .filter(AgentLlmEvalScenarioVersion.agent_id == agent_id)
            .scalar()
            or 1
        )
        version = AgentLlmEvalScenarioVersion(
            organization_id=self.org_id,
            agent_id=agent_id,
            version_number=next_number,
            source="generated",
            status="generating",
            generation_prompt=generation_prompt,
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version

    def _version_has_runs(self, agent_id: UUID, version_id: UUID) -> bool:
        run = (
            self.query(AgentLlmEvalRun)
            .filter(AgentLlmEvalRun.agent_id == agent_id)
            .filter(AgentLlmEvalRun.version_id == version_id)
            .first()
        )
        if run is not None:
            return True
        result = (
            self.query(AgentLlmEvalResult)
            .filter(AgentLlmEvalResult.agent_id == agent_id)
            .filter(AgentLlmEvalResult.version_id == version_id)
            .first()
        )
        return result is not None

    def _require_version(
        self, agent_id: UUID, version_id: UUID
    ) -> AgentLlmEvalScenarioVersion:
        row = (
            self.query(AgentLlmEvalScenarioVersion)
            .filter(AgentLlmEvalScenarioVersion.id == version_id)
            .filter(AgentLlmEvalScenarioVersion.agent_id == agent_id)
            .first()
        )
        if row is None:
            raise AgentLlmEvalVersionNotFoundError(
                f"Version {version_id} not found for agent {agent_id}"
            )
        return row

    def _require_scenario(
        self, agent_id: UUID, scenario_id: UUID
    ) -> AgentLlmEvalScenario:
        row = (
            self.query(AgentLlmEvalScenario)
            .filter(AgentLlmEvalScenario.id == scenario_id)
            .filter(AgentLlmEvalScenario.agent_id == agent_id)
            .filter(AgentLlmEvalScenario.node_type == "scenario")
            .first()
        )
        if row is None:
            raise AgentLlmScenarioNotFoundError(
                f"Scenario {scenario_id} not found for agent {agent_id}"
            )
        return row

    def _assert_agent_in_org(self, agent_id: UUID) -> None:
        assert_agent_in_org(
            self.db,
            agent_id=agent_id,
            org_id=self.org_id,
            error_cls=AgentLlmEvalConfigError,
        )


# ── Helpers ──────────────────────────────────────────────────────────


def _prompt_hash(prompt: Optional[str]) -> Optional[str]:
    if not prompt:
        return None
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _model_from_persisted(persisted: list) -> Optional[str]:
    """Best-effort ``generated_by_model`` — read from the first persisted
    scenario's ``generation_metadata`` when the strategy recorded a model."""
    for row in persisted or []:
        meta = getattr(row, "generation_metadata", None)
        if isinstance(meta, dict):
            model = meta.get("model") or meta.get("judge_model") or meta.get("generated_by_model")
            if model:
                return str(model)
    return None


__all__ = [
    "AgentLlmEvalVersionService",
    "GeneratedVersion",
    "GENERATION_FAILED_MESSAGE",
]
