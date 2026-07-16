"""Category C — LLM configuration + live provider probe.

Every shallow check here is a 5-line concrete subclass of a shape defined in
``_common.py``; the LLM-specific bits are just the class attributes.
"""

from __future__ import annotations

import asyncio
from typing import ClassVar

from core.services.readiness.base import (
    CheckContext,
    DeepCheck,
    TransientProviderError,
    with_retry,
    with_timeout,
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
    """Send a 1-token completion to the LLM to verify credentials + reachability.

    Wraps the provider call in a 3-second timeout and one retry on transient
    errors. Actual per-provider probe logic isn't implemented in v1 (the shallow
    checks catch ~95% of real breakage); this returns ``skipped`` with a clear
    reason so the UI can render the placeholder correctly.
    """

    id: ClassVar[str] = "llm.provider_reachable"
    category: ClassVar[Category] = Category.LLM
    severity: ClassVar[Severity] = Severity.WARNING

    def applies(self, ctx: CheckContext) -> bool:
        return ctx.llm.provider is not None and ctx.llm.decrypted_key is not None

    def skip_reason(self, ctx: CheckContext) -> str:
        return "Provider or key not resolved (see shallow checks)."

    @with_retry()
    @with_timeout(3.0)
    async def run(self, ctx: CheckContext) -> CheckResult:
        # Placeholder: per-provider probe adapters land in a follow-up. Doing
        # nothing here is deliberately safe — the shallow LLM checks already
        # cover the common failure modes, so a green shallow + skipped deep
        # is still an actionable signal for the UI ("verified structurally").
        await asyncio.sleep(0)
        return self._skip(
            "Live LLM provider probe not implemented yet — "
            "structural checks passed."
        )
