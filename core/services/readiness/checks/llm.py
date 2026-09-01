"""Category C — LLM configuration + live provider probe.

Every shallow check here is a 5-line concrete subclass of a shape defined in
``_common.py``; the LLM-specific bits are just the class attributes.
"""

from __future__ import annotations

from typing import ClassVar

from core.services.readiness.base import (
    CheckContext,
    DeepCheck,
    TransientProviderError,
    with_timeout_and_retry,
)
from core.services.readiness.checks._common import (
    ApiKeyDecryptsCheck,
    ApiKeyPresentCheck,
    ModelConfiguredCheck,
    ProviderConfiguredCheck,
    ProviderEnabledCheck,
)
from core.services.readiness.schemas import (
    Category,
    CheckResult,
    ResourceRef,
    Severity,
)


class LLMProviderConfiguredCheck(ProviderConfiguredCheck):
    id: ClassVar[str] = "llm.provider_configured"
    category: ClassVar[Category] = Category.LLM
    spec_attr: ClassVar[str] = "llm"
    service_label: ClassVar[str] = "LLM"


class LLMModelConfiguredCheck(ModelConfiguredCheck):
    id: ClassVar[str] = "llm.model_configured"
    category: ClassVar[Category] = Category.LLM
    spec_attr: ClassVar[str] = "llm"
    service_label: ClassVar[str] = "LLM"


class LLMApiKeyPresentCheck(ApiKeyPresentCheck):
    id: ClassVar[str] = "llm.api_key_present"
    category: ClassVar[Category] = Category.LLM
    spec_attr: ClassVar[str] = "llm"
    service_label: ClassVar[str] = "LLM"


class LLMApiKeyDecryptsCheck(ApiKeyDecryptsCheck):
    id: ClassVar[str] = "llm.api_key_decrypts"
    category: ClassVar[Category] = Category.LLM
    spec_attr: ClassVar[str] = "llm"
    service_label: ClassVar[str] = "LLM"


class LLMProviderEnabledCheck(ProviderEnabledCheck):
    id: ClassVar[str] = "llm.provider_enabled"
    category: ClassVar[Category] = Category.LLM
    spec_attr: ClassVar[str] = "llm"
    service_label: ClassVar[str] = "LLM"


# ── Deep: live probe ────────────────────────────────────────────────────────


class LLMProviderReachableCheck(DeepCheck):
    """Feed a one-message ``LLMContextFrame`` through the pipecat LLM pipeline
    and consume the first ``LLMTextFrame`` (or ``LLMFullResponseEndFrame``).

    Same frame flow the runtime uses (see ``core/services/pipeline/runner/
    pipecat.py``), so this exercises the full pipecat ``LLMService`` wrapper —
    not just the raw provider SDK. Cost is bounded by max_completion_tokens=16
    in the probe. Wrapped in a 12s timeout and one retry on transient errors.
    """

    id: ClassVar[str] = "llm.provider_reachable"
    category: ClassVar[Category] = Category.LLM
    # BLOCKER: a wrong/revoked API key or unreachable provider means the agent
    # cannot take a call. Anything less than BLOCKER lets the overall verdict
    # settle at READY_WITH_WARNINGS (see runner._aggregate), which the UI
    # renders as green — a bad key would silently pass the readiness gate.
    severity: ClassVar[Severity] = Severity.BLOCKER

    def applies(self, ctx: CheckContext) -> bool:
        # S2S LLMs (openai_realtime, gemini_live) can't be live-probed without
        # opening a real audio session; skip cleanly instead of returning a
        # false PASS from the probe. Same pattern the STT/TTS deep checks use.
        return (
            not ctx.is_s2s
            and ctx.llm.provider is not None
            and ctx.llm.decrypted_key is not None
        )

    def skip_reason(self, ctx: CheckContext) -> str:
        if ctx.is_s2s:
            return (
                "Speech-to-speech LLM — live probe requires an audio session "
                "and is skipped by design."
            )
        return "Provider or key not resolved (see shallow checks)."

    # Pipeline harness (PipelineTask start + provider HTTP/WS handshake) +
    # first-token streaming. Cold reasoning models (o1/o3, claude-*-thinking,
    # gemini-*-thinking) and cold self-hosted / cross-region endpoints
    # (Ollama, Bedrock, custom Azure deployments) can take 10-18s to emit the
    # first token. 40s (was 25s) gives real headroom for pre-work under load
    # (spec resolution, decryption, cache miss) BEFORE the probe's internal
    # 20s wait fires; without that headroom a busy event loop consumed the
    # outer window and healthy providers were false-flagged as BLOCKER.
    # `with_timeout_and_retry` (attempts=2) gives each attempt its own fresh
    # 40s budget and retries specifically on `asyncio.TimeoutError` so a
    # single transient hiccup doesn't fail a working provider. Auth/quota
    # 4xx errors surface as `ProbeResult(ok=False)` and are returned
    # immediately — no retry, no delay.
    @with_timeout_and_retry(40.0, attempts=2)
    async def run(self, ctx: CheckContext) -> CheckResult:
        from core.services.readiness.probes import probe_llm

        result = await probe_llm(ctx)
        if result.ok:
            return self._pass(result.message)
        # ``result.message`` is already a clean, provider-named sentence
        # (probes classify auth / credit / model / rate / outage and extract the
        # human message from anything else) — surface it as-is. A TIMEOUT
        # ("slow / warming up") is downgraded to WARNING so a healthy-but-slow
        # provider never hard-blocks publish; a confirmed failure keeps BLOCKER.
        return self._fail(
            result.message,
            remediation=(
                "Verify the provider status, that the API key is still valid, "
                "and that the model name is current."
            ),
            severity=Severity.WARNING if result.timed_out else None,
        )
