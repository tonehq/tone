"""Resolve an agent's LLM eval config from the DB.

The eval must score the agent's ACTUAL config (the LLM the agent would use
on a real call), NOT a synthetic one — otherwise the developer's "did my
system-prompt change help?" question isn't answerable. This loader walks
``agents.published_config_id → agent_configs.{system_prompt_template,
llm_settings}`` and hands back a plain ``AgentEvalConfig`` dataclass the
service reads once and then closes the DB session (so no pool connection is
held across the LLM loop).

Mirrors ``core/services/pipeline/service_resolver.py:_build_service_specs``
LLM branch — same JSONB keys (``provider_id``, ``model_id``,
``temperature``, …), same decrypt path — so what the eval scores matches
what production dials.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from core.models.agent import Agent
from core.models.agent_config import AgentConfig
from core.models.model import Model
from core.models.model_provider import ModelProvider
from core.services.evals.errors import AgentLlmEvalConfigError
from core.services.rag.provider_keys import ProviderKeyService


# JSONB keys that identify the provider / model / snapshot — mirrors
# ``core/services/pipeline/service_resolver.py`` so the two paths can't drift.
_LLM_PROVIDER_KEY = "provider_id"
_LLM_MODEL_ID_KEY = "model_id"
_LLM_MODEL_NAME_KEY = "model"
# Keys we pull into the JSONB snapshot column verbatim (the hybrid schema —
# typed columns for model/provider/system-prompt, JSONB for the rest).
_SNAPSHOT_KEYS = ("temperature", "top_p", "top_k", "max_tokens")


@dataclass
class AgentEvalConfig:
    """Snapshot of every attribute the LLM loop needs — resolved once, then
    the caller can close the session. The service passes this to
    ``chat_complete`` (for the agent's own LLM) and stamps the snapshot
    fields onto every persisted result row.
    """

    agent_id: UUID
    agent_name: str
    organization_id: UUID
    agent_config_id: Optional[UUID]
    llm_model: Optional[str]
    llm_provider: Optional[str]
    llm_api_key: Optional[str]
    system_prompt: Optional[str]
    llm_settings_snapshot: dict
    # Kwargs pulled out of the snapshot for ``chat_complete`` — kept
    # separate so the persisted snapshot stays raw (no defaults/coercion).
    temperature: float
    max_tokens: int


class AgentConfigLoader:
    """Loads and freezes the LLM-related bits of an agent's published config
    for one eval run. Injected into ``AgentLlmEvalService`` so tests can
    stub the DB path out without patching module globals.
    """

    def load_for_eval(
        self,
        db: Session,
        agent_id: Any,
        *,
        organization_id: Optional[UUID] = None,
    ) -> AgentEvalConfig:
        """Resolve the agent's published config + decrypted LLM API key.

        Raises ``AgentLlmEvalConfigError`` with an actionable message when:
        - the agent row doesn't exist,
        - the agent has no ``published_config_id`` (unpublished draft),
        - the config carries no LLM model / provider,
        - or no API key is configured for that provider on the org.

        When ``organization_id`` is supplied the lookup is tenant-scoped —
        the CLI runs single-tenant so this is optional today; a future
        API adapter MUST pass ``org_id`` from ``JWTClaims`` to prevent
        cross-tenant reads of the decrypted API key.
        """
        q = db.query(Agent).filter(Agent.id == agent_id)
        if organization_id is not None:
            q = q.filter(Agent.organization_id == organization_id)
        agent = q.first()
        if agent is None:
            raise AgentLlmEvalConfigError(f"Agent {agent_id} not found")

        if agent.published_config_id is None:
            raise AgentLlmEvalConfigError(
                f"Agent {agent.name!r} has no published config — publish the "
                "agent before running an LLM eval."
            )

        cfg: Optional[AgentConfig] = (
            db.query(AgentConfig)
            .filter(AgentConfig.id == agent.published_config_id)
            .first()
        )
        if cfg is None:
            raise AgentLlmEvalConfigError(
                f"Agent {agent.name!r} published_config_id "
                f"{agent.published_config_id} points at a missing agent_configs row."
            )

        llm_settings = dict(cfg.llm_settings or {})

        # Resolve the concrete model name — either baked directly on
        # ``llm_settings.model`` (some templates) or via the ``model_id`` UUID
        # (the resolver's canonical path). Missing model = the agent has never
        # been fully configured; we can't dial the LLM either.
        model_name: Optional[str] = llm_settings.get(_LLM_MODEL_NAME_KEY)
        model_id = llm_settings.get(_LLM_MODEL_ID_KEY)
        provider_slug: Optional[str] = None
        model_row: Optional[Model] = None
        if model_id:
            model_row = db.query(Model).filter(Model.id == model_id).first()
            if model_row and not model_name:
                model_name = model_row.name

        # Provider slug — resolve via the ``provider_id`` FK on the settings.
        # ``ModelProvider.provider_id`` is the slug ``chat_complete`` /
        # ``ProviderKeyService`` expect (openai / anthropic / google / …).
        provider_id = llm_settings.get(_LLM_PROVIDER_KEY)
        if provider_id:
            prov = (
                db.query(ModelProvider)
                .filter(ModelProvider.id == provider_id)
                .first()
            )
            if prov:
                provider_slug = prov.provider_id
        elif model_row:
            prov = (
                db.query(ModelProvider)
                .filter(ModelProvider.id == model_row.provider_id)
                .first()
            )
            if prov:
                provider_slug = prov.provider_id

        if not model_name:
            raise AgentLlmEvalConfigError(
                f"Agent {agent.name!r} config has no LLM model — set an LLM "
                "on the agent before running an LLM eval."
            )
        if not provider_slug:
            raise AgentLlmEvalConfigError(
                f"Agent {agent.name!r} config has no LLM provider — set an "
                "LLM provider on the agent before running an LLM eval."
            )

        api_key = ProviderKeyService.get_key(db, agent.organization_id, provider_slug)
        if not api_key:
            raise AgentLlmEvalConfigError(
                f"No {provider_slug!r} API key configured for organisation "
                f"{agent.organization_id} (needed by agent {agent.name!r})."
            )

        snapshot = {k: llm_settings[k] for k in _SNAPSHOT_KEYS if k in llm_settings}

        # ``chat_complete`` needs a numeric temperature and max_tokens. Pull
        # them out of the raw settings with safe fallbacks (agents that never
        # touched the sliders keep the OpenAI defaults).
        temperature = _coerce_float(llm_settings.get("temperature"), default=0.0)
        max_tokens = _coerce_int(llm_settings.get("max_tokens"), default=1024)

        return AgentEvalConfig(
            agent_id=agent.id,
            agent_name=agent.name,
            organization_id=agent.organization_id,
            agent_config_id=cfg.id,
            llm_model=model_name,
            llm_provider=provider_slug,
            llm_api_key=api_key,
            system_prompt=cfg.system_prompt_template,
            llm_settings_snapshot=snapshot,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def resolve_agent_id(
        self,
        db: Session,
        agent_ref: str,
        *,
        organization_id: Optional[UUID] = None,
    ) -> UUID:
        """Resolve a CLI ``--agent`` argument to an agent UUID.

        ``agent_ref`` can be a UUID (matched to ``agents.id``) or a name
        (matched case-insensitively to ``agents.name``). Raises
        ``AgentLlmEvalConfigError`` for no-match / ambiguous cases so the CLI
        surfaces an actionable message instead of a stack trace.

        ``%`` / ``_`` in the caller-supplied name are ESCAPED before the
        ``ILIKE`` — otherwise ``--agent '%'`` would match every agent in
        every tenant. When ``organization_id`` is supplied both branches are
        tenant-scoped.
        """
        candidate = (agent_ref or "").strip()
        if not candidate:
            raise AgentLlmEvalConfigError("--agent must be a UUID or name; got empty string")

        try:
            uuid_val = UUID(candidate)
        except ValueError:
            uuid_val = None

        if uuid_val is not None:
            q = db.query(Agent).filter(Agent.id == uuid_val)
            if organization_id is not None:
                q = q.filter(Agent.organization_id == organization_id)
            agent = q.first()
            if agent is None:
                raise AgentLlmEvalConfigError(f"Agent with id {uuid_val} not found")
            return agent.id

        # Escape LIKE wildcards so a user-supplied '%'/'_' matches literally
        # (both would otherwise silently expand into a wildcard match across
        # the tenant / whole DB when unscoped).
        escaped = (
            candidate.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        q = db.query(Agent).filter(Agent.name.ilike(escaped, escape="\\"))
        if organization_id is not None:
            q = q.filter(Agent.organization_id == organization_id)
        matches = q.all()
        if not matches:
            raise AgentLlmEvalConfigError(f"No agent named {candidate!r} found")
        if len(matches) > 1:
            ids = ", ".join(str(m.id) for m in matches)
            raise AgentLlmEvalConfigError(
                f"Multiple agents named {candidate!r} — pass a UUID instead "
                f"(candidates: {ids})"
            )
        return matches[0].id


def _coerce_float(v: Any, *, default: float) -> float:
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _coerce_int(v: Any, *, default: int) -> int:
    if v is None or v == "":
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default
