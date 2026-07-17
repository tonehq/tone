"""Category E — TTS configuration (+ voice) + live probe.

Same S2S-skip pattern as STT. Adds two TTS-only checks that don't have LLM/STT
equivalents: the voice must exist, and its owning model (if resolvable) must
match the configured TTS model.
"""

from __future__ import annotations

from typing import ClassVar

from core.services.readiness.base import (
    CheckContext,
    DeepCheck,
    ShallowCheck,
    with_retry,
    with_timeout,
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


_S2S_SKIP_REASON = "Speech-to-speech mode — TTS is handled by the LLM."


class _TTSMixin:
    def applies(self, ctx: CheckContext) -> bool:  # type: ignore[override]
        return not ctx.is_s2s

    def skip_reason(self, ctx: CheckContext) -> str:  # type: ignore[override]
        return _S2S_SKIP_REASON


class TTSProviderConfiguredCheck(_TTSMixin, ProviderConfiguredCheck):
    id: ClassVar[str] = "tts.provider_configured"
    category: ClassVar[Category] = Category.TTS
    spec_attr: ClassVar[str] = "tts"
    service_label: ClassVar[str] = "TTS"


class TTSModelConfiguredCheck(_TTSMixin, ModelConfiguredCheck):
    id: ClassVar[str] = "tts.model_configured"
    category: ClassVar[Category] = Category.TTS
    spec_attr: ClassVar[str] = "tts"
    service_label: ClassVar[str] = "TTS"


class TTSApiKeyPresentCheck(_TTSMixin, ApiKeyPresentCheck):
    id: ClassVar[str] = "tts.api_key_present"
    category: ClassVar[Category] = Category.TTS
    spec_attr: ClassVar[str] = "tts"
    service_label: ClassVar[str] = "TTS"


class TTSApiKeyDecryptsCheck(_TTSMixin, ApiKeyDecryptsCheck):
    id: ClassVar[str] = "tts.api_key_decrypts"
    category: ClassVar[Category] = Category.TTS
    spec_attr: ClassVar[str] = "tts"
    service_label: ClassVar[str] = "TTS"


class TTSVoiceSelectedCheck(_TTSMixin, ShallowCheck):
    """A voice must be selected. Accepts either a UUID (row lookup) or a
    raw provider-native string (e.g. ElevenLabs voice id)."""

    id: ClassVar[str] = "tts.voice_selected"
    category: ClassVar[Category] = Category.TTS
    severity: ClassVar[Severity] = Severity.BLOCKER

    async def run(self, ctx: CheckContext) -> CheckResult:
        voice_id_raw = (ctx.tts.settings or {}).get("voice_id")
        if not voice_id_raw:
            return self._fail(
                "No TTS voice selected.",
                remediation="Pick a voice in the agent editor's Voice tab.",
            )
        # If it looks like a UUID, we should have resolved a row for it.
        if ctx.voice is None and _looks_like_uuid(voice_id_raw):
            return self._fail(
                "Selected TTS voice no longer exists.",
                remediation="Choose a different voice.",
                resource_ref=ResourceRef(type="voice", id=str(voice_id_raw)),
            )
        voice_name = getattr(ctx.voice, "name", None) if ctx.voice else str(voice_id_raw)
        return self._pass(f"Voice selected: {voice_name}.")


class TTSVoiceModelMatchCheck(_TTSMixin, ShallowCheck):
    """Warn if the selected voice belongs to a different TTS model than the
    configured one — Pipecat may fall back, but audio quality is unpredictable.
    """

    id: ClassVar[str] = "tts.voice_model_match"
    category: ClassVar[Category] = Category.TTS
    severity: ClassVar[Severity] = Severity.WARNING

    def applies(self, ctx: CheckContext) -> bool:
        return (
            not ctx.is_s2s
            and ctx.voice is not None
            and ctx.tts.model is not None
        )

    def skip_reason(self, ctx: CheckContext) -> str:
        if ctx.is_s2s:
            return _S2S_SKIP_REASON
        return "Voice or model not resolved."

    async def run(self, ctx: CheckContext) -> CheckResult:
        # ModelVoice.model_id is the source of truth for which model the voice
        # was catalogued under. Older seed data may leave model_id null — treat
        # that as "unknown, don't complain".
        voice_model_id = getattr(ctx.voice, "model_id", None)
        if voice_model_id is None:
            return self._pass("Voice model linkage not tracked — skipping match check.")
        if voice_model_id != ctx.tts.model.id:
            return self._fail(
                "Selected voice belongs to a different TTS model than the "
                "one configured.",
                remediation=(
                    "Re-select a voice after switching TTS models to keep "
                    "audio quality consistent."
                ),
                resource_ref=ResourceRef(type="voice", id=str(ctx.voice.id)),
            )
        return self._pass("Voice matches the configured TTS model.")


class TTSProviderReachableCheck(DeepCheck):
    """Synthesise the word "test" through the pipecat TTS service.

    ``TTSService.run_tts()`` is the standard pipecat TTS API — we iterate until
    the first audio frame (or error), which proves the provider accepted the
    request end-to-end. Works across every TTS provider without per-provider
    code because it uses pipecat's universal streaming interface.
    """

    id: ClassVar[str] = "tts.provider_reachable"
    category: ClassVar[Category] = Category.TTS
    severity: ClassVar[Severity] = Severity.WARNING

    def applies(self, ctx: CheckContext) -> bool:
        return (
            not ctx.is_s2s
            and ctx.tts.provider is not None
            and ctx.tts.decrypted_key is not None
        )

    def skip_reason(self, ctx: CheckContext) -> str:
        if ctx.is_s2s:
            return _S2S_SKIP_REASON
        return "Provider or key not resolved (see shallow checks)."

    @with_retry()
    # Pipeline harness (PipelineTask start + WS handshake) + sentence
    # synthesis + first-audio consumption. Slower WS TTSs (ElevenLabs, LMNT,
    # Cartesia streaming) can take 4–8s cold; 12s keeps us honest without
    # false-flagging them.
    @with_timeout(12.0)
    async def run(self, ctx: CheckContext) -> CheckResult:
        from core.services.readiness.probes import probe_tts

        result = await probe_tts(ctx)
        return self._pass(result.message) if result.ok else self._fail(
            result.message,
            remediation=(
                "Verify the TTS provider status, the API key, and that the "
                "selected voice still exists in the provider's catalog."
            ),
        )


def _looks_like_uuid(value: str) -> bool:
    from uuid import UUID
    try:
        UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False
