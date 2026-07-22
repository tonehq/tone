"""Category D — STT configuration + live probe.

Structurally identical to LLM. All checks in this file skip when the pipeline
is in speech-to-speech mode (OpenAI Realtime / Gemini Live handle STT
themselves) — the ``.applies()`` override on each concrete class is the only
STT-specific twist over the shared shapes.
"""

from __future__ import annotations

from typing import ClassVar

from core.services.readiness.base import (
    CheckContext,
    DeepCheck,
    with_timeout_and_retry,
)
from core.services.readiness.checks._common import (
    ApiKeyDecryptsCheck,
    ApiKeyPresentCheck,
    ModelConfiguredCheck,
    ProviderConfiguredCheck,
)
from core.services.readiness.schemas import Category, CheckResult, Severity


_S2S_SKIP_REASON = "Speech-to-speech mode — STT is handled by the LLM."


class _STTMixin:
    """Common S2S-skip behaviour for every STT check."""

    def applies(self, ctx: CheckContext) -> bool:  # type: ignore[override]
        return not ctx.is_s2s

    def skip_reason(self, ctx: CheckContext) -> str:  # type: ignore[override]
        return _S2S_SKIP_REASON


class STTProviderConfiguredCheck(_STTMixin, ProviderConfiguredCheck):
    id: ClassVar[str] = "stt.provider_configured"
    category: ClassVar[Category] = Category.STT
    spec_attr: ClassVar[str] = "stt"
    service_label: ClassVar[str] = "STT"


class STTModelConfiguredCheck(_STTMixin, ModelConfiguredCheck):
    id: ClassVar[str] = "stt.model_configured"
    category: ClassVar[Category] = Category.STT
    spec_attr: ClassVar[str] = "stt"
    service_label: ClassVar[str] = "STT"


class STTApiKeyPresentCheck(_STTMixin, ApiKeyPresentCheck):
    id: ClassVar[str] = "stt.api_key_present"
    category: ClassVar[Category] = Category.STT
    spec_attr: ClassVar[str] = "stt"
    service_label: ClassVar[str] = "STT"


class STTApiKeyDecryptsCheck(_STTMixin, ApiKeyDecryptsCheck):
    id: ClassVar[str] = "stt.api_key_decrypts"
    category: ClassVar[Category] = Category.STT
    spec_attr: ClassVar[str] = "stt"
    service_label: ClassVar[str] = "STT"


class STTProviderReachableCheck(DeepCheck):
    """Instantiate the pipecat STT service to verify credentials + deps + config.

    Constructor-only for now: pipecat STT services stream over WebSocket / gRPC,
    and opening a real session just to verify auth is provider-specific and
    expensive. Construction still catches bad keys, missing deps, and malformed
    config — the same failure modes the deep check exists to surface.
    """

    id: ClassVar[str] = "stt.provider_reachable"
    category: ClassVar[Category] = Category.STT
    # BLOCKER: a wrong/revoked STT API key or unreachable provider means the
    # agent has no transcript source. WARNING would let the overall verdict
    # settle at READY_WITH_WARNINGS (see runner._aggregate) which the UI
    # treats as ready.
    severity: ClassVar[Severity] = Severity.BLOCKER

    def applies(self, ctx: CheckContext) -> bool:
        return (
            not ctx.is_s2s
            and ctx.stt.provider is not None
            and ctx.stt.decrypted_key is not None
        )

    def skip_reason(self, ctx: CheckContext) -> str:
        if ctx.is_s2s:
            return _S2S_SKIP_REASON
        return "Provider or key not resolved (see shallow checks)."

    # Pipeline harness adds ~2–4s for PipelineTask lifecycle (StartFrame,
    # WS handshake, TaskManager setup) on top of the real-audio probe.
    # Cold WS-STTs (Deepgram / AssemblyAI / Sarvam / Soniox in fresh
    # regions) can take 15-22s to complete first-handshake + final
    # transcript. 45s (was 30s) gives real headroom for pre-work under
    # load (spec resolution, decryption, cache miss) BEFORE the probe's
    # internal 25s wait fires; without that headroom a busy event loop
    # consumed the outer window and healthy providers were false-flagged
    # as BLOCKER. `with_timeout_and_retry` (attempts=2) gives each attempt
    # its own fresh 45s budget and retries specifically on
    # `asyncio.TimeoutError` so a single transient WS handshake or cold
    # region doesn't fail a working provider. Auth/quota 4xx errors
    # surface as `ProbeResult(ok=False)` and are returned immediately —
    # no retry, no delay.
    @with_timeout_and_retry(45.0, attempts=2)
    async def run(self, ctx: CheckContext) -> CheckResult:
        from core.services.readiness.probes import probe_stt

        result = await probe_stt(ctx)
        return self._pass(result.message) if result.ok else self._fail(
            result.message,
            remediation="Verify the STT provider status and that the API key is valid.",
        )
