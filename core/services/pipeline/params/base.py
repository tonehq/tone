"""Framework-agnostic pipeline parameters.

`PipelineParams` is the single source of truth for everything needed to build a voice
pipeline for an agent: the resolved LLM/STT/TTS service specs, the conversation messages,
the S2S flag, and the end-call message. It is produced by `from_agent` (DB + decrypt, via
`service_resolver.resolve_agent_services`) or `from_cache_dict` (subprocess prefetch / Redis),
and consumed by a `PipelineBuilder`.

NO Pipecat imports here — this layer stays framework-agnostic so future engines can reuse it.
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional

from core.services.pipeline.service_resolver import (
    resolve_agent_services,
    resolve_agent_services_with_fallback,
)

# Default services for the no-agent fallback path (WebRTC / Daily without an agent).
DEFAULT_VOICE_ID = "71a7ad14-091c-4e8e-a314-022ece01c121"


@dataclass
class ServiceSpec:
    """A resolved LLM/STT/TTS service: provider + decrypted key + model + metadata.

    This is exactly the dict shape consumed by `service_factory.build_llm/stt/tts`.
    """

    provider_name: str
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    model_meta_data: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "ServiceSpec":
        return cls(
            provider_name=d["provider_name"],
            api_key=d.get("api_key"),
            model_name=d.get("model_name"),
            metadata=d.get("metadata") or {},
            model_meta_data=d.get("model_meta_data") or {},
        )

    def to_dict(self) -> dict:
        return {
            "provider_name": self.provider_name,
            "api_key": self.api_key,
            "model_name": self.model_name,
            "metadata": self.metadata,
            "model_meta_data": self.model_meta_data,
        }


@dataclass
class PipelineParams:
    """High-level, framework-agnostic configuration for one voice pipeline run."""

    llm: ServiceSpec
    stt: Optional[ServiceSpec] = None
    tts: Optional[ServiceSpec] = None
    is_s2s: bool = False
    messages: List[dict] = field(default_factory=list)
    end_call_message: Optional[str] = None
    # Telephony credentials — only populated on the serialize/prefetch path; popped by the
    # caller before the dict is handed downstream. Not used by the builder/runner.
    telephony_creds: Optional[dict] = None

    @property
    def system_prompt(self) -> Optional[str]:
        for m in self.messages:
            if m.get("role") == "system":
                return m.get("content")
        return None

    @property
    def first_message_text(self) -> Optional[str]:
        """The greeting to speak on connect (last message if it's an assistant turn)."""
        if len(self.messages) > 1 and self.messages[-1].get("role") == "assistant":
            return self.messages[-1].get("content", "").strip()
        return None

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #
    @classmethod
    def from_cache_dict(cls, d: Optional[dict]) -> Optional["PipelineParams"]:
        """Build params from the Redis-cached / subprocess prefetch dict shape."""
        if not d:
            return None
        return cls(
            llm=ServiceSpec.from_dict(d["llm"]),
            stt=ServiceSpec.from_dict(d["stt"]) if d.get("stt") else None,
            tts=ServiceSpec.from_dict(d["tts"]) if d.get("tts") else None,
            is_s2s=bool(d.get("is_s2s")),
            messages=d.get("messages") or [],
            end_call_message=d.get("end_call_message"),
            telephony_creds=d.get("_telephony_creds"),
        )

    def to_cache_dict(self) -> dict:
        """Serialize to the exact JSON shape used by the Redis cache + subprocess payload."""
        d = {
            "llm": self.llm.to_dict() if self.llm else None,
            "stt": self.stt.to_dict() if self.stt else None,
            "tts": self.tts.to_dict() if self.tts else None,
            "is_s2s": self.is_s2s,
            "messages": self.messages,
            "end_call_message": self.end_call_message,
        }
        if self.telephony_creds:
            d["_telephony_creds"] = self.telephony_creds
        return d

    @classmethod
    def from_agent(cls, agent: Any, db, transport_type: str = None, org_id=None) -> Optional["PipelineParams"]:
        """Read the agent's active config from the DB, decrypt keys, and build params.

        Reads Redis first (via service_resolver). When transport_type is None, tries the
        transport-specific cache keys before a fresh resolution (matches the old
        get_agent_bot_data read-back behavior).
        """
        if transport_type is not None:
            data = resolve_agent_services(db, agent, transport_type=transport_type, org_id=org_id)
        else:
            data = resolve_agent_services_with_fallback(db, agent, org_id=org_id)
        return cls.from_cache_dict(data) if data else None

    @classmethod
    def serialize_for_prefetch(cls, agent: Any, db, transport_type: str = None, org_id=None) -> Optional[dict]:
        """Return the cache-shape dict (incl. _telephony_creds) for the telephony prefetch path."""
        return resolve_agent_services(db, agent, transport_type=transport_type, org_id=org_id)

    @classmethod
    def default_env(cls, openai_key: str, deepgram_key: str, cartesia_key: str, messages: List[dict]) -> "PipelineParams":
        """Params for the no-agent fallback path (env-based OpenAI/Deepgram/Cartesia)."""
        return cls(
            llm=ServiceSpec(provider_name="openai", api_key=openai_key, model_name="gpt-4o"),
            stt=ServiceSpec(provider_name="deepgram", api_key=deepgram_key),
            tts=ServiceSpec(provider_name="cartesia", api_key=cartesia_key, metadata={"voice_id": DEFAULT_VOICE_ID}),
            is_s2s=False,
            messages=messages,
        )
