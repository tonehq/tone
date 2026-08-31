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
    with_timeout_and_retry,
)
from core.services.readiness.checks._common import (
    ApiKeyDecryptsCheck,
    ApiKeyPresentCheck,
    ModelConfiguredCheck,
    ProviderConfiguredCheck,
)
from core.services.readiness.checks._messages import humanize_reason, quote
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


class TTSLanguageConfiguredCheck(_TTSMixin, ShallowCheck):
    """Warn when no language is selected — TTS falls back to the provider's
    default (usually English), which is fine for English deployments but
    silently synthesises non-English content with the wrong accent/phonemes.

    ``WARNING`` severity, not blocker: pipecat TTS services default to English
    voices when no language is passed, so a missing language never breaks the
    call. English-only agents work as-is; non-English deployments need the
    drawer hint to catch the misconfiguration. Two sources are accepted
    (matches how ``service_resolver._build_service_specs`` reads language today):
    the AgentConfig FK ``language_id`` OR the JSONB
    ``voice_settings.language`` / ``.language_code`` key.
    """

    id: ClassVar[str] = "tts.language_configured"
    category: ClassVar[Category] = Category.TTS
    severity: ClassVar[Severity] = Severity.WARNING

    async def run(self, ctx: CheckContext) -> CheckResult:
        if ctx.config is not None and getattr(ctx.config, "language_id", None):
            return self._pass("TTS language selected on agent.")
        settings = ctx.tts.settings or {}
        lang = settings.get("language_code") or settings.get("language")
        if lang:
            return self._pass(f"TTS language configured: {lang}.")
        return self._fail(
            "No TTS language selected — if your agent speaks in another "
            "language, set the language on the Language tab or in voice "
            "settings.",
            remediation=(
                "Pick a language on the agent (Language tab) or set "
                "'language' in the voice settings."
            ),
        )


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


class TTSVoiceLanguageMatchCheck(_TTSMixin, ShallowCheck):
    """Warn when the selected voice doesn't declare support for the agent's
    language.

    ``ModelVoice.language_list`` is a JSONB array of provider-specific codes
    (e.g. ``["en", "hi", "es"]``). If the code isn't in the list, the voice
    still "works" — the wrong-accent / wrong-phonemes failure is a quality
    problem, not a hard failure — so this is a WARNING that surfaces in the
    drawer without blocking publish. Skipped for legacy voices whose
    ``language_list`` is empty/null (metadata not seeded) so the check never
    false-flags an agent that was passing yesterday.
    """

    id: ClassVar[str] = "tts.voice_language_match"
    category: ClassVar[Category] = Category.TTS
    severity: ClassVar[Severity] = Severity.WARNING

    def applies(self, ctx: CheckContext) -> bool:
        return not ctx.is_s2s and ctx.voice is not None

    def skip_reason(self, ctx: CheckContext) -> str:
        if ctx.is_s2s:
            return _S2S_SKIP_REASON
        return "No voice selected."

    async def run(self, ctx: CheckContext) -> CheckResult:
        from core.services.readiness.checks._language import resolve_language_code

        supported = getattr(ctx.voice, "language_list", None) or []
        if not supported:
            return self._skip(
                "Voice does not declare supported languages (metadata not seeded)."
            )
        code = resolve_language_code(ctx, "tts")
        if not code:
            return self._skip("Language not configured (see language check).")
        # Case-insensitive comparison — providers mix "en" / "en-US" / "EN".
        normalised = {str(c).strip().lower() for c in supported if c}
        if code.lower() not in normalised:
            preview = ", ".join(str(c) for c in supported[:6])
            more = f" +{len(supported) - 6} more" if len(supported) > 6 else ""
            return self._fail(
                f"The selected voice doesn't support the “{code}” language "
                f"(it supports {preview}{more}).",
                remediation=(
                    "Pick a voice that supports the agent's language, or "
                    "switch the language."
                ),
                resource_ref=ResourceRef(type="voice", id=str(ctx.voice.id)),
            )
        return self._pass(f"Voice supports language '{code}'.")


class TTSModelLanguageMatchCheck(_TTSMixin, ShallowCheck):
    """Warn when the selected TTS model doesn't declare support for the agent's
    language.

    ``WARNING`` severity: TTS providers with a mismatched language usually
    fall back to their default language or a degraded voice rather than
    hard-failing. The check surfaces the mismatch so users can pick a
    language-supporting model, but doesn't block publish. Empty
    ``ModelLanguage`` result set means metadata isn't seeded — SKIP rather
    than fail, so older models don't regress passing agents.
    """

    id: ClassVar[str] = "tts.model_language_match"
    category: ClassVar[Category] = Category.TTS
    severity: ClassVar[Severity] = Severity.WARNING

    def applies(self, ctx: CheckContext) -> bool:
        return not ctx.is_s2s and ctx.tts.model is not None

    def skip_reason(self, ctx: CheckContext) -> str:
        if ctx.is_s2s:
            return _S2S_SKIP_REASON
        return "TTS model not resolved."

    async def run(self, ctx: CheckContext) -> CheckResult:
        from core.models.model_language import ModelLanguage
        from core.services.readiness.checks._language import resolve_language_code

        code = resolve_language_code(ctx, "tts")
        if not code:
            return self._skip("Language not configured (see language check).")

        rows = (
            ctx.db.query(ModelLanguage.name)
            .filter(
                ModelLanguage.model_id == ctx.tts.model.id,
                ModelLanguage.is_active.is_(True),
            )
            .all()
        )
        if not rows:
            return self._skip(
                "TTS model does not declare supported languages (metadata not seeded)."
            )
        supported = {str(r[0]).strip().lower() for r in rows if r[0]}
        if code.lower() not in supported:
            return self._fail(
                f"The TTS model {quote(ctx.tts.model.name)} doesn't support the "
                f"“{code}” language.",
                remediation=(
                    "Pick a TTS model that supports the language, or switch "
                    "the language."
                ),
                resource_ref=ResourceRef(type="model", id=str(ctx.tts.model.id)),
            )
        return self._pass(
            f"TTS model '{ctx.tts.model.name}' supports language '{code}'."
        )


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
    # BLOCKER: a wrong/revoked TTS API key or unreachable provider means the
    # agent cannot speak. WARNING would let the overall verdict settle at
    # READY_WITH_WARNINGS (see runner._aggregate) which the UI treats as ready.
    severity: ClassVar[Severity] = Severity.BLOCKER

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

    # Pipeline harness (PipelineTask start + WS handshake) + sentence
    # synthesis + first-audio consumption. Slower WS TTSs (ElevenLabs,
    # LMNT, Cartesia streaming, Play.ht) can take 10-15s cold on heavy
    # voices or distant regions. 35s (was 22s) gives real headroom for
    # pre-work under load (spec resolution, decryption, cache miss)
    # BEFORE the probe's internal 18s wait fires; without that headroom
    # a busy event loop consumed the outer window and healthy providers
    # were false-flagged as BLOCKER. `with_timeout_and_retry` (attempts=2)
    # gives each attempt its own fresh 35s budget and retries specifically
    # on `asyncio.TimeoutError` so a single transient WS handshake or
    # cold voice-model load doesn't fail a working provider. Auth/quota
    # 4xx errors surface as `ProbeResult(ok=False)` and are returned
    # immediately — no retry, no delay.
    @with_timeout_and_retry(35.0, attempts=2)
    async def run(self, ctx: CheckContext) -> CheckResult:
        from core.services.readiness.probes import probe_tts

        result = await probe_tts(ctx)
        if result.ok:
            return self._pass(result.message)
        provider_name = getattr(ctx.tts.provider, "display_name", None)
        return self._fail(
            f"The TTS provider {quote(provider_name)} can't be used — "
            f"{humanize_reason(result.message)}.",
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
