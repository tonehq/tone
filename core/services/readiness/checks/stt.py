"""Category D — STT configuration + live probe.

Structurally identical to LLM. All checks in this file skip when the pipeline
is in speech-to-speech mode (OpenAI Realtime / Gemini Live handle STT
themselves) — the ``.applies()`` override on each concrete class is the only
STT-specific twist over the shared shapes.
"""

from __future__ import annotations

import asyncio
from typing import ClassVar

from core.services.readiness.base import (
    CheckContext,
    DeepCheck,
    with_retry,
    with_timeout,
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
    id: ClassVar[str] = "stt.provider_reachable"
    category: ClassVar[Category] = Category.STT
    severity: ClassVar[Severity] = Severity.WARNING

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

    @with_retry()
    @with_timeout(3.0)
    async def run(self, ctx: CheckContext) -> CheckResult:
        await asyncio.sleep(0)
        return self._skip(
            "Live STT provider probe not implemented yet — "
            "structural checks passed."
        )
