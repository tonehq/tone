"""Framework-agnostic pipeline parameters.

`PipelineParams` is the single source of truth for everything needed to build a voice
pipeline for an agent: the resolved LLM/STT/TTS service specs, the conversation messages,
the S2S flag, and the end-call message. It is produced by `from_agent` (DB + decrypt, via
`service_resolver.load_agent_service_config`) or `from_cache_dict` (subprocess prefetch /
Redis), and consumed by a `PipelineBuilder`.

NO Pipecat imports here — this layer stays framework-agnostic so future engines can reuse it.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional
from zoneinfo import ZoneInfo

from core.services.pipeline.service_resolver import (
    load_agent_service_config, load_agent_service_config_cached)


def build_date_preamble() -> str:
    """A system-prompt preamble anchoring the model to the real current date.

    Clock-less models (e.g. gpt-4o-mini) otherwise invent years and can't enforce
    "no past dates". "Today" is resolved in a configurable timezone (AGENT_TIMEZONE,
    default UTC) so the anchor matches the caller's locale instead of naive
    server-local time. Falls back to UTC on an unknown zone.
    """
    from core.config import settings

    tz_name = getattr(settings, "AGENT_TIMEZONE", None) or "UTC"
    try:
        now = datetime.now(ZoneInfo(tz_name))
    except Exception:
        tz_name = "UTC"
        now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    return (
        f"Today's date is {today} ({tz_name}, YYYY-MM-DD). Treat this as the current date "
        f"for all date reasoning. Never use a year earlier than the current year, and "
        f"never schedule or book a date earlier than today.\n\n"
    )


@dataclass
class PipelineParams:
    """High-level, framework-agnostic configuration for one voice pipeline run.

    The `llm`/`stt`/`tts` specs are plain dicts of shape
    `{provider_name, api_key, model_name, metadata, model_meta_data}` — exactly what
    `service_factory.build_llm/stt/tts` consume — so no wrapper type is needed.
    """

    llm: dict
    stt: Optional[dict] = None
    tts: Optional[dict] = None
    is_s2s: bool = False
    messages: List[dict] = field(default_factory=list)
    end_call_message: Optional[str] = None
    # Cached, DB-free tool/KB data the builder rebuilds handlers from (MCP stays live).
    tools: List[dict] = field(default_factory=list)
    kb: Optional[dict] = None
    # `{id, name}` refs cached for the call-log snapshot only — not consumed by the
    # builder. Lets the runner record which KBs/MCP servers were wired to the agent
    # without an extra DB hit on the call-insert path.
    kb_refs: List[dict] = field(default_factory=list)
    mcp_servers: List[dict] = field(default_factory=list)
    telephony_creds: Optional[dict] = None
    # Raw workflow graph + api-fn-name map for the runtime engine (workflow mode only).
    # Absent ⇒ prompt mode / playbook fallback; `is_workflow` gates the runtime path.
    workflow: Optional[dict] = None
    workflow_fn_names: dict = field(default_factory=dict)

    @property
    def is_workflow(self) -> bool:
        """True when a runtime workflow graph is present to drive the call deterministically."""
        return bool(self.workflow)

    @property
    def first_message_text(self) -> Optional[str]:
        """The greeting to speak on connect (last message if it's an assistant turn)."""
        if len(self.messages) > 1 and self.messages[-1].get("role") == "assistant":
            return self.messages[-1].get("content", "").strip()
        return None

    def messages_with_date_anchor(self) -> List[dict]:
        """Messages with the current-date preamble prepended to the system prompt.

        Computed fresh at build time (the builder calls this per call) rather than baked
        into the resolver's Redis-cached messages, so the anchored date never goes stale.
        Returns the messages unchanged if there is no system message.
        """
        preamble = build_date_preamble()
        anchored = []
        injected = False
        for m in self.messages:
            if not injected and m.get("role") == "system":
                anchored.append({**m, "content": preamble + (m.get("content") or "")})
                injected = True
            else:
                anchored.append(m)
        return anchored

    def messages_with_runtime_context(self, context: Optional[dict] = None) -> List[dict]:
        """Date-anchored messages with per-call ``{{variable}}`` substitution applied.

        Substitutes known variables (caller number, agent name, date, …) into the system
        and assistant (first_message) turns. Like the date anchor this runs per call in
        the builder, NOT in the Redis-cached payload, so one caller's values never leak
        into another call. Falls back to date-anchor-only when ``context`` is empty.
        """
        msgs = self.messages_with_date_anchor()
        if not context:
            return msgs
        from core.services.pipeline.prompt_variables import substitute_variables

        out = []
        for m in msgs:
            if m.get("role") in ("system", "assistant") and m.get("content"):
                out.append({**m, "content": substitute_variables(m["content"], context)})
            else:
                out.append(m)
        return out

    def first_message_with_context(self, context: Optional[dict] = None) -> Optional[str]:
        """The greeting to speak on connect, with ``{{variable}}`` substitution applied."""
        text = self.first_message_text
        if not text or not context:
            return text
        from core.services.pipeline.prompt_variables import substitute_variables

        return substitute_variables(text, context)

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #
    @classmethod
    def load(cls, agent: Any, body: Optional[dict] = None) -> "PipelineParams":
        """Single entry point for run_bot: build params for an agent.

        Uses the prefetched service dict from `body["_prefetched_services"]` when present
        (subprocess/warm-pool path, no DB); otherwise opens a short-lived DB session and
        resolves from the agent's config. Raises ValueError if the agent has no usable
        config so the caller fails loudly instead of running a half-built pipeline.
        """
        body = body or {}
        prefetched = body.get("_prefetched_services")
        if prefetched:
            params = cls.from_cache_dict(prefetched)
        else:
            from core.database.session import get_db_context
            with get_db_context() as db:
                params = cls.from_agent(agent, db, transport_type=body.get("transport_type"))
        if not params:
            raise ValueError(
                "Agent has no active config or missing LLM/STT/TTS services. "
                "Configure the agent and ensure services are set."
            )
        return params

    @classmethod
    def from_cache_dict(cls, d: Optional[dict]) -> Optional["PipelineParams"]:
        """Build params from the Redis-cached / subprocess prefetch dict shape."""
        if not d:
            return None
        return cls(
            llm=d["llm"],
            stt=d.get("stt"),
            tts=d.get("tts"),
            is_s2s=bool(d.get("is_s2s")),
            messages=d.get("messages") or [],
            end_call_message=d.get("end_call_message"),
            telephony_creds=d.get("_telephony_creds"),
            tools=d.get("tools") or [],
            kb=d.get("kb"),
            kb_refs=d.get("kb_refs") or [],
            mcp_servers=d.get("mcp_servers") or [],
            workflow=d.get("workflow"),
            workflow_fn_names=d.get("workflow_fn_names") or {},
        )

    @classmethod
    def from_agent(cls, agent: Any, db, transport_type: str = None, org_id=None) -> Optional["PipelineParams"]:
        """Read the agent's active config from the DB, decrypt keys, and build params.

        Reads Redis first (via service_resolver). When transport_type is None, tries the
        transport-specific cache keys before a fresh resolution.
        """
        if transport_type is not None:
            data = load_agent_service_config(db, agent, transport_type=transport_type, org_id=org_id)
        else:
            data = load_agent_service_config_cached(db, agent, org_id=org_id)
        return cls.from_cache_dict(data) if data else None
