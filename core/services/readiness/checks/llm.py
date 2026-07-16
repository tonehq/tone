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
    """Fire a 1-token completion through the pipecat LLM service to verify
    credentials + reachability + model availability.

    Reuses ``service_factory.build_llm`` so the probe hits the exact same code
    path a real call would use — no duplicated per-provider adapters. Wrapped
    in a 3-second timeout and one retry on transient errors.
    """

    id: ClassVar[str] = "llm.provider_reachable"
    category: ClassVar[Category] = Category.LLM
    severity: ClassVar[Severity] = Severity.WARNING

    def applies(self, ctx: CheckContext) -> bool:
        return ctx.llm.provider is not None and ctx.llm.decrypted_key is not None

    def skip_reason(self, ctx: CheckContext) -> str:
        return "Provider or key not resolved (see shallow checks)."

    @with_retry()
    @with_timeout(5.0)  # cold-start on some LLMs (Cohere, Groq spin-up) can exceed 3s
    async def run(self, ctx: CheckContext) -> CheckResult:
        from core.services.readiness.probes import probe_llm

        result = await probe_llm(ctx)
        return self._pass(result.message) if result.ok else self._fail(
            result.message,
            remediation=(
                "Verify the provider status, that the API key is still valid, "
                "and that the model name is current."
            ),
        )
