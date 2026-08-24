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
    ShallowCheck,
    with_timeout_and_retry,
)
from core.services.readiness.checks._common import (
    ApiKeyDecryptsCheck,
    ApiKeyPresentCheck,
    ModelConfiguredCheck,
    ProviderConfiguredCheck,
)
from core.services.readiness.schemas import (
    Category,
    CheckResult,
    ResourceRef,
    Severity,
)


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


class STTLanguageConfiguredCheck(_STTMixin, ShallowCheck):
    """Warn when no language is selected — STT falls back to the provider's
    default (usually English), which is fine for English deployments but
    silently mistranscribes any other language.

    ``WARNING`` severity, not blocker: every pipecat STT service ships an
    English default (Cartesia, Deepgram, AssemblyAI, Whisper, Sarvam, …), so
    a missing language never crashes the call. English-only agents work as-is
    and shouldn't be blocked; non-English deployments need the drawer hint to
    catch the misconfiguration before customers hear garbled transcripts.
    Two sources are accepted (matches how ``service_resolver._build_service_specs``
    reads language today): the AgentConfig FK ``language_id`` OR the JSONB
    ``stt_settings.language`` / ``.language_code`` key.
    """

    id: ClassVar[str] = "stt.language_configured"
    category: ClassVar[Category] = Category.STT
    severity: ClassVar[Severity] = Severity.WARNING

    async def run(self, ctx: CheckContext) -> CheckResult:
        if ctx.config is not None and getattr(ctx.config, "language_id", None):
            return self._pass("STT language selected on agent.")
        settings = ctx.stt.settings or {}
        lang = settings.get("language_code") or settings.get("language")
        if lang:
            return self._pass(f"STT language configured: {lang}.")
        return self._fail(
            "No STT language selected — if your agent handles non-English "
            "calls, set the language on the Language tab to avoid "
            "mistranscription.",
            remediation=(
                "Pick a language on the agent (Language tab) or set "
                "'language' in the STT settings."
            ),
        )


class STTModelLanguageMatchCheck(_STTMixin, ShallowCheck):
    """Warn when the selected STT model doesn't declare support for the agent's
    language.

    ``WARNING`` severity: providers with a mismatched language typically fall
    back to their default language or a coarser model, producing degraded
    transcripts rather than a hard failure. The check surfaces the mismatch
    so users can pick a language-supporting model, but doesn't block publish.
    Reads ``ModelLanguage`` join rows for ``ctx.stt.model``. Empty result set
    means the model's language metadata isn't seeded — SKIP rather than fail,
    so older models don't regress passing agents.
    """

    id: ClassVar[str] = "stt.model_language_match"
    category: ClassVar[Category] = Category.STT
    severity: ClassVar[Severity] = Severity.WARNING

    def applies(self, ctx: CheckContext) -> bool:
        return not ctx.is_s2s and ctx.stt.model is not None

    def skip_reason(self, ctx: CheckContext) -> str:
        if ctx.is_s2s:
            return _S2S_SKIP_REASON
        return "STT model not resolved."

    async def run(self, ctx: CheckContext) -> CheckResult:
        from core.models.model_language import ModelLanguage
        from core.services.readiness.checks._language import resolve_language_code

        code = resolve_language_code(ctx, "stt")
        if not code:
            return self._skip("Language not configured (see language check).")

        rows = (
            ctx.db.query(ModelLanguage.name)
            .filter(
                ModelLanguage.model_id == ctx.stt.model.id,
                ModelLanguage.is_active.is_(True),
            )
            .all()
        )
        if not rows:
            return self._skip(
                "STT model does not declare supported languages (metadata not seeded)."
            )
        supported = {str(r[0]).strip().lower() for r in rows if r[0]}
        if code.lower() not in supported:
            return self._fail(
                f"STT model '{ctx.stt.model.name}' does not support language "
                f"'{code}'.",
                remediation=(
                    "Pick an STT model that supports the language, or switch "
                    "the language."
                ),
                resource_ref=ResourceRef(type="model", id=str(ctx.stt.model.id)),
            )
        return self._pass(
            f"STT model '{ctx.stt.model.name}' supports language '{code}'."
        )


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
