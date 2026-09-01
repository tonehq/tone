"""``CallTranscriptEvalService`` — orchestrator for the post-call transcript
eval harness.

Transport-agnostic: takes a SQLAlchemy session + plain args, returns a
:class:`CallTranscriptEvalSummary` dataclass. Invoked by the
``score_call_transcript`` Procrastinate task
(``EvalCallTranscriptAction`` → ``enqueue_call_transcript_eval_sync``);
also usable directly by a future manual re-run endpoint.

Shape mirrors :meth:`AgentLlmEvalService.run_eval`:

- Snapshot the agent config while the session is still open, then close it
  so nothing is held during the LLM loop (Neon
  ``idle_in_transaction_session_timeout`` would otherwise drop a session
  held across the judge call).
- Fail-soft on judge exception — stamp the row ``status='failed'`` with
  the exception on ``judge_error``; ``PostCallHandler`` treats action
  failures as isolated so the rest of the post-call flow is unaffected.
- Fail-loud on configuration — re-raise ``EvalConfigurationError`` /
  :class:`CallTranscriptEvalConfigError` so the Procrastinate task retries
  cleanly before persisting a fake-FAIL row.
- Idempotent — a re-delivered task early-returns if a ``full_call`` row
  already exists for the call.
- Auto-run gated at eval time (not enqueue time) — a redelivered job for
  an org that opted out AFTER the call still respects the toggle.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy.orm import Session

from core.models.agent_config import AgentConfig
from core.models.call import Call
from core.models.call_transcript_eval_result import CallTranscriptEvalResult
from core.services.base import BaseService
from core.services.evals.errors import (
    CallTranscriptEvalConfigError,
    EvalConfigurationError,
)
from core.services.rag.errors import humanize_provider_error

_JUDGE_ENGINE = "deepeval"
_MODE_FULL_CALL = "full_call"
# The plan locks the ``chatbot_role`` snapshot to the first 200 chars of
# the system prompt; kept as a constant so the value doesn't drift between
# the resolver here and any future re-run endpoint.
_CHATBOT_ROLE_MAX_CHARS = 200


@dataclass
class CallTranscriptEvalSummary:
    """Snapshot of one post-call transcript scoring run — what the
    Procrastinate task and any future re-run endpoint return."""

    call_id: UUID
    status: str  # 'completed' | 'failed'
    verdict: Optional[str]
    metric_scores: dict
    latency_ms: Optional[int]
    judge_model: Optional[str]
    judge_engine: Optional[str]
    skip_reason: Optional[str]


class CallTranscriptEvalService(BaseService):
    """Score one completed call's ``consolidated_transcript`` with DeepEval
    and persist the result row. See module docstring for shape / policies."""

    def __init__(
        self,
        db: Session,
        *,
        org_id: Optional[UUID] = None,
        judge: object | None = None,
    ) -> None:
        super().__init__(db, org_id=org_id)
        # DI seam: production callers pass no ``judge`` — the judge is built
        # lazily so read-only paths never transitively import DeepEval.
        self._injected_judge = judge

    @property
    def _judge(self):
        if self._injected_judge is None:
            # Local import — keeps DeepEval + its OTel hijack out of any
            # process that only reads the results table.
            from core.services.evals.call_transcript.judge import (
                CallTranscriptJudgeService,
            )

            self._injected_judge = CallTranscriptJudgeService()
        return self._injected_judge

    # ── Public API ──────────────────────────────────────────────────────

    def run_for_call(
        self,
        *,
        call_id: UUID,
        force: bool = False,
        triggered_by: str = "auto",
    ) -> CallTranscriptEvalSummary:
        """Score the call's consolidated transcript and persist ONE row.

        Skip paths (all return a summary with ``skip_reason`` and DO NOT
        persist a row — the FE distinguishes "never scored" from a real
        skip on the read endpoint):

        - ``auto_run_off`` — org toggled off, ``force=False``.
        - ``no_transcript`` — consolidator hasn't finished yet, or the call
          truly had no turns.
        - ``already_scored`` — a ``full_call`` row exists for this call.

        Fail-loud on pre-run config: raises ``CallTranscriptEvalConfigError``
        (missing agent_config on the call, missing provider key for the
        judge model). The Procrastinate task retries these.

        Fail-soft on judge exception: persists a row with ``status='failed'``
        and ``judge_error=<repr>``; returns a summary with the failure.
        """
        # 1. Load call + org guard. ``BaseService.query`` scopes by
        # ``self.org_id`` when set; the Procrastinate task passes it, so a
        # spoofed ``call_id`` from a different org yields no row.
        call: Optional[Call] = (
            self.query(Call).filter(Call.id == call_id).first()
        )
        if call is None:
            raise CallTranscriptEvalConfigError(
                f"Call {call_id} not found — cannot score transcript."
            )

        # 2. Idempotency — one ``full_call`` row per call.
        existing = (
            self.query(CallTranscriptEvalResult)
            .filter(
                CallTranscriptEvalResult.call_id == call_id,
                CallTranscriptEvalResult.mode == _MODE_FULL_CALL,
            )
            .first()
        )
        if existing is not None:
            logger.info(
                "[call-transcript-eval] skip already_scored call={} existing_id={}",
                call_id, existing.id,
            )
            return CallTranscriptEvalSummary(
                call_id=call_id,
                status=existing.status,
                verdict=existing.verdict,
                metric_scores=existing.metric_scores or {},
                latency_ms=existing.latency_ms,
                judge_model=existing.judge_model,
                judge_engine=existing.judge_engine,
                skip_reason="already_scored",
            )

        # 3. Transcript guard — the consolidator runs on its own queue, so
        # this task can lose the race. Skip cleanly instead of dialling
        # the judge with an empty conversation.
        transcript = call.consolidated_transcript or []
        if not transcript:
            logger.info(
                "[call-transcript-eval] skip no_transcript call={} (consolidator "
                "may not have run yet)", call_id,
            )
            return CallTranscriptEvalSummary(
                call_id=call_id,
                status="completed",
                verdict=None,
                metric_scores={},
                latency_ms=None,
                judge_model=None,
                judge_engine=None,
                skip_reason="no_transcript",
            )

        # 4. Resolve org settings — the auto_run toggle gates the LLM call.
        from core.services.org_settings import (
            load_call_eval_settings_for_org,
        )

        settings = load_call_eval_settings_for_org(
            self.db, call.organization_id,
        )
        if not settings.auto_run_enabled and not force:
            logger.info(
                "[call-transcript-eval] skip auto_run_off call={} org={}",
                call_id, call.organization_id,
            )
            return CallTranscriptEvalSummary(
                call_id=call_id,
                status="completed",
                verdict=None,
                metric_scores={},
                latency_ms=None,
                judge_model=None,
                judge_engine=None,
                skip_reason="auto_run_off",
            )

        # 5. Snapshot the agent config. We don't use ``AgentConfigLoader.load_for_eval``
        # — it raises when the agent has no ``published_config_id``, but a
        # call could have been dialled with a since-unpublished config and we
        # still want to score it (the scored snapshot preserves what actually
        # ran). Read the row this call was dialled with directly.
        snapshot = self._snapshot_call_config(call)

        # 6. Resolve judge model + key on the still-open session.
        judge_model = settings.judge_model
        judge_key = self._resolve_judge_key(
            organization_id=call.organization_id,
            judge_model=judge_model,
            fallback_provider=snapshot["llm_provider"],
        )

        organization_id = call.organization_id
        agent_id = call.agent_id
        agent_config_id = snapshot["agent_config_id"]
        # Close the session BEFORE the LLM loop — Neon idle-in-txn timeout
        # would otherwise drop it under any judge slowdown.
        self.db.close()

        # 7. Score.
        started_at = datetime.now(timezone.utc)
        t0 = time.monotonic()
        status = "completed"
        verdict: Optional[str] = None
        metric_scores: dict = {}
        judge_reasoning: Optional[str] = None
        judge_error: Optional[str] = None

        try:
            judge_out = self._judge.judge(
                transcript=transcript,
                system_prompt=snapshot["system_prompt"],
                chatbot_role=snapshot["chatbot_role"],
                api_key=judge_key,
                model=judge_model,
                metrics=list(settings.metrics_enabled),
                threshold=settings.metric_threshold,
            )
            verdict = judge_out.get("verdict")
            metric_scores = judge_out.get("metric_scores") or {}
            judge_reasoning = judge_out.get("reasoning") or None
        except EvalConfigurationError:
            # Systemic config bug — re-raise; task retries.
            raise
        except Exception as e:  # noqa: BLE001
            logger.exception(
                "[call-transcript-eval] judge failed call={} model={}",
                call_id, judge_model,
            )
            status = "failed"
            judge_error = humanize_provider_error(e)

        completed_at = datetime.now(timezone.utc)
        latency_ms = int((time.monotonic() - t0) * 1000)

        # 8. Persist on a fresh session so we don't inherit a broken pool
        # connection from the LLM-loop session (mirrors
        # ``AgentLlmEvalService._persist_result_batch``).
        self._persist_row(
            organization_id=organization_id,
            call_id=call_id,
            agent_id=agent_id,
            agent_config_id=agent_config_id,
            snapshot=snapshot,
            judge_model=judge_model,
            status=status,
            verdict=verdict,
            metric_scores=metric_scores,
            judge_reasoning=judge_reasoning,
            judge_error=judge_error,
            latency_ms=latency_ms,
            started_at=started_at,
            completed_at=completed_at,
        )

        logger.info(
            "[call-transcript-eval] scored call={} status={} verdict={} "
            "latency_ms={} judge_model={}",
            call_id, status, verdict, latency_ms, judge_model,
        )
        return CallTranscriptEvalSummary(
            call_id=call_id,
            status=status,
            verdict=verdict,
            metric_scores=metric_scores,
            latency_ms=latency_ms,
            judge_model=judge_model,
            judge_engine=_JUDGE_ENGINE,
            skip_reason=None,
        )

    def get_result_for_call(
        self, call_id: UUID,
    ) -> Optional[CallTranscriptEvalResult]:
        """Return the ``full_call`` row for a call, or ``None`` if never
        scored. Cross-tenant reads yield ``None`` because ``BaseService.query``
        scopes by ``self.org_id``."""
        return (
            self.query(CallTranscriptEvalResult)
            .filter(
                CallTranscriptEvalResult.call_id == call_id,
                CallTranscriptEvalResult.mode == _MODE_FULL_CALL,
            )
            .first()
        )

    # ── Internals ───────────────────────────────────────────────────────

    def _snapshot_call_config(self, call: Call) -> dict:
        """Freeze the agent-config fields the judge needs (and that we stamp
        onto the persisted row) into a plain dict, so the caller can close
        the session before scoring.

        Reads the agent_config the call was actually dialled with (via
        ``call.agent_config_id``) — NOT the currently-published config. This
        preserves attribution: a config edited after the call still shows
        the version that produced the transcript. Rows with no
        ``agent_config_id`` (older calls, edge cases) get a snapshot with
        every LLM/prompt field ``None``; the judge still runs (with no
        chatbot_role → RoleAdherence will skip / fail per its own policy).
        """
        agent_config: Optional[AgentConfig] = None
        if call.agent_config_id is not None:
            agent_config = (
                self.db.query(AgentConfig)
                .filter(AgentConfig.id == call.agent_config_id)
                .first()
            )

        system_prompt: Optional[str] = None
        llm_model: Optional[str] = None
        llm_provider: Optional[str] = None
        chatbot_role: Optional[str] = None
        if agent_config is not None:
            system_prompt = agent_config.system_prompt_template
            llm_settings = dict(agent_config.llm_settings or {})
            llm_model = llm_settings.get("model")
            provider_id = llm_settings.get("provider_id")
            if provider_id:
                from core.models.model_provider import ModelProvider

                prov = (
                    self.db.query(ModelProvider)
                    .filter(ModelProvider.id == provider_id)
                    .first()
                )
                if prov is not None:
                    llm_provider = prov.provider_id
            # Fall back to resolving provider via the model row (mirrors
            # the agent-config loader) when settings didn't carry
            # ``provider_id`` directly.
            if not llm_provider:
                model_id = llm_settings.get("model_id")
                if model_id:
                    from core.models.model import Model
                    from core.models.model_provider import ModelProvider

                    model_row = (
                        self.db.query(Model)
                        .filter(Model.id == model_id)
                        .first()
                    )
                    if model_row is not None:
                        prov = (
                            self.db.query(ModelProvider)
                            .filter(ModelProvider.id == model_row.provider_id)
                            .first()
                        )
                        if prov is not None:
                            llm_provider = prov.provider_id
                        if not llm_model:
                            llm_model = model_row.name
            if system_prompt:
                chatbot_role = system_prompt.strip()[:_CHATBOT_ROLE_MAX_CHARS]

        return {
            "agent_config_id": call.agent_config_id,
            "system_prompt": system_prompt,
            "llm_model": llm_model,
            "llm_provider": llm_provider,
            "chatbot_role": chatbot_role,
        }

    def _resolve_judge_key(
        self,
        *,
        organization_id: UUID,
        judge_model: str,
        fallback_provider: Optional[str],
    ) -> str:
        """Resolve the API key for the judge model's provider — mirrors
        :meth:`AgentLlmEvalService._resolve_judge_key`. The judge model may
        point at a different provider than the agent, so we route through
        the shared LLM router to derive the provider then fetch the org's
        stored key."""
        from core.services.llm.chat_complete import resolve_provider
        from core.services.rag.provider_keys import ProviderKeyService

        try:
            judge_provider = resolve_provider(judge_model)
        except Exception as e:  # noqa: BLE001
            raise CallTranscriptEvalConfigError(
                f"Cannot resolve provider for judge model {judge_model!r}: {e}"
            ) from e

        key = ProviderKeyService.get_key(self.db, organization_id, judge_provider)
        if not key and fallback_provider and fallback_provider == judge_provider:
            # Same-provider fallback for dev setups that only have one key.
            key = ProviderKeyService.get_key(
                self.db, organization_id, fallback_provider,
            )
        if not key:
            raise CallTranscriptEvalConfigError(
                f"No {judge_provider!r} API key configured for organisation "
                f"{organization_id} (needed by judge model {judge_model!r})."
            )
        return key

    def _persist_row(
        self,
        *,
        organization_id: UUID,
        call_id: UUID,
        agent_id: UUID,
        agent_config_id: Optional[UUID],
        snapshot: dict,
        judge_model: str,
        status: str,
        verdict: Optional[str],
        metric_scores: dict,
        judge_reasoning: Optional[str],
        judge_error: Optional[str],
        latency_ms: Optional[int],
        started_at: datetime,
        completed_at: datetime,
    ) -> None:
        from core.database.session import SessionLocal

        row = {
            "id": uuid.uuid4(),
            "organization_id": organization_id,
            "call_id": call_id,
            "agent_id": agent_id,
            "agent_config_id": agent_config_id,
            "mode": _MODE_FULL_CALL,
            "turn_number": None,
            "llm_model": snapshot.get("llm_model"),
            "llm_provider": snapshot.get("llm_provider"),
            "system_prompt": snapshot.get("system_prompt"),
            "chatbot_role": snapshot.get("chatbot_role"),
            "judge_model": judge_model,
            "judge_engine": _JUDGE_ENGINE,
            "status": status,
            "verdict": verdict,
            "metric_scores": metric_scores or None,
            "judge_reasoning": judge_reasoning,
            "latency_ms": latency_ms,
            "judge_error": judge_error,
            "skip_reason": None,
            "started_at": started_at,
            "completed_at": completed_at,
        }
        with SessionLocal() as fresh:
            fresh.bulk_insert_mappings(CallTranscriptEvalResult, [row])
            fresh.commit()


__all__ = ["CallTranscriptEvalService", "CallTranscriptEvalSummary"]
