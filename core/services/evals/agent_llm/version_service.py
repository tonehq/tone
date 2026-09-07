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
    AgentLlmEvalVersionHasRunsError,
    AgentLlmEvalVersionNotFoundError,
    AgentLlmScenarioNotFoundError,
    EvalGenerationError,
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
        """Generate scenarios into a VERSION (synchronous).

        ``mode='new'`` creates the next version for the agent; ``mode='overwrite'``
        reuses ``version_id`` (refused once the version has been run). Scenarios
        are saved as ``approval_status='pending'`` under a ``draft`` version for
        review. ``generation_prompt`` is the user's custom prompt — stored on
        the version and fed to the LLM generator.
        """
        if mode not in {"new", "overwrite"}:
            raise EvalGenerationError(f"mode must be 'new' or 'overwrite'; got {mode!r}")

        self._assert_agent_in_org(agent_id)
        cleaned_prompt = (generation_prompt or "").strip() or None

        version = self._resolve_generation_version(
            agent_id,
            mode=mode,
            version_id=version_id,
            generation_prompt=cleaned_prompt,
        )

        scenarios_svc = AgentLlmScenarioService(
            self.db, user_id=self.user_id, org_id=self.org_id
        )
        options = {"generation_prompt": cleaned_prompt} if cleaned_prompt else {}
        batch = scenarios_svc.generate_scenarios(
            agent_id,
            strategy=self._GENERATION_STRATEGY,
            count=count,
            dry_run=False,
            options=options,
            folder_id=parent_id,
            version_id=version.id,
            approval_status="pending",
        )

        # Stamp provenance on the version (hash + model) now that generation
        # succeeded. ``generated_by_model`` is read off the first persisted
        # row's generation_metadata when the strategy recorded it.
        version.generation_prompt_hash = _prompt_hash(cleaned_prompt)
        version.generated_by_model = _model_from_persisted(batch.persisted)
        self.db.commit()
        self.db.refresh(version)

        logger.info(
            "[agent-llm-eval] generated version agent={} version_id={} number={} "
            "mode={} scenarios={}",
            agent_id, version.id, version.version_number, mode, len(batch.persisted),
        )
        return GeneratedVersion(version=version, scenarios=list(batch.persisted))

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
        """Create (``new``) or reuse (``overwrite``) the target version.
        Overwrite is refused once a version has been run; otherwise its pending
        scenarios are cleared before regeneration."""
        if mode == "overwrite":
            if version_id is None:
                raise EvalGenerationError(
                    "version_id is required when mode='overwrite'"
                )
            version = self._require_version(agent_id, version_id)
            if self._version_has_runs(agent_id, version_id):
                raise AgentLlmEvalVersionHasRunsError(
                    "This version has already been run — create a new version "
                    "instead of overwriting it."
                )
            # Overwrite replaces the version's entire contents (safe — the
            # version is guaranteed un-run by the guard above), so stale
            # approved rows don't survive a regenerate.
            self.query(AgentLlmEvalScenario).filter(
                AgentLlmEvalScenario.agent_id == agent_id,
                AgentLlmEvalScenario.version_id == version_id,
                AgentLlmEvalScenario.node_type == "scenario",
            ).delete(synchronize_session=False)
            version.status = "draft"
            version.source = "generated"
            version.generation_prompt = generation_prompt
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
            status="draft",
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


__all__ = ["AgentLlmEvalVersionService", "GeneratedVersion"]
