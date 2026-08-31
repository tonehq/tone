"""Shared abstract check shapes for the pipeline legs (LLM / STT / TTS).

The three legs answer the same structural questions ("is a provider chosen?
is a model chosen? is a key stored? does it decrypt?"). Rather than write
each rule three times (12+ duplicates across llm.py / stt.py / tts.py), we
implement the rule once here and pin ``category`` / ``service_label`` /
``spec_attr`` in the tiny per-leg subclasses.

Every subclass in ``llm.py`` / ``stt.py`` / ``tts.py`` is a 5–10 line class —
this file carries the actual assertion logic.
"""

from __future__ import annotations

from typing import ClassVar

from core.services.readiness.base import CheckContext, ServiceSpec, ShallowCheck
from core.services.readiness.checks._messages import quote
from core.services.readiness.schemas import (
    Category,
    CheckResult,
    ResourceRef,
    Severity,
)


class _LegCheckMixin:
    """Provides ``_spec()`` — the one context lookup every leg check needs."""

    # Set on concrete leg subclasses.
    spec_attr: ClassVar[str]      # "llm" | "stt" | "tts"
    service_label: ClassVar[str]  # "LLM" | "STT" | "TTS" — shown to the user

    def _spec(self, ctx: CheckContext) -> ServiceSpec:
        return getattr(ctx, self.spec_attr)


class ProviderConfiguredCheck(ShallowCheck, _LegCheckMixin):
    """Verify the leg has a provider selected and the provider row exists."""

    severity: ClassVar[Severity] = Severity.BLOCKER
    category: ClassVar[Category]  # set on concrete subclass

    async def run(self, ctx: CheckContext) -> CheckResult:
        spec = self._spec(ctx)
        if not spec.provider_id:
            return self._fail(
                f"No {self.service_label} provider selected.",
                remediation=(
                    f"Open the agent editor and pick a {self.service_label} "
                    "provider."
                ),
            )
        if spec.provider is None:
            return self._fail(
                f"Selected {self.service_label} provider no longer exists.",
                remediation="Choose a different provider from the list.",
                resource_ref=ResourceRef(
                    type="provider", id=str(spec.provider_id)
                ),
            )
        return self._pass(f"{self.service_label} provider: {spec.provider.display_name}")


class ProviderEnabledCheck(ShallowCheck, _LegCheckMixin):
    """Verify the provider isn't marked inactive at the platform level."""

    severity: ClassVar[Severity] = Severity.BLOCKER
    category: ClassVar[Category]

    async def run(self, ctx: CheckContext) -> CheckResult:
        spec = self._spec(ctx)
        if spec.provider is None:
            return self._skip("Provider not resolved (see provider check).")
        if not spec.provider.is_active:
            return self._fail(
                f"The {self.service_label} provider {quote(spec.provider.display_name)} "
                "is turned off.",
                remediation=(
                    "Contact your workspace admin or switch to an active provider."
                ),
                resource_ref=ResourceRef(
                    type="provider", id=str(spec.provider.id)
                ),
            )
        return self._pass(
            f"{self.service_label} provider '{spec.provider.display_name}' is enabled."
        )


class ModelConfiguredCheck(ShallowCheck, _LegCheckMixin):
    """Verify a model is selected, exists, and belongs to the chosen provider."""

    severity: ClassVar[Severity] = Severity.BLOCKER
    category: ClassVar[Category]

    async def run(self, ctx: CheckContext) -> CheckResult:
        spec = self._spec(ctx)
        # Some STT/TTS providers accept a raw model string via settings["model"]
        # (see service_resolver._build_service_specs); a raw string counts as a
        # valid selection even without a model_id row.
        raw_model = (spec.settings or {}).get("model")
        if not spec.model_id and not raw_model:
            return self._fail(
                f"No {self.service_label} model selected.",
                remediation=(
                    f"Choose a {self.service_label} model in the agent editor."
                ),
            )
        if spec.model_id and spec.model is None:
            return self._fail(
                f"Selected {self.service_label} model no longer exists.",
                remediation="Choose a different model.",
                resource_ref=ResourceRef(
                    type="model", id=str(spec.model_id)
                ),
            )
        if (
            spec.model is not None
            and spec.provider is not None
            and spec.model.provider_id != spec.provider.id
        ):
            return self._fail(
                f"{self.service_label} model belongs to a different provider "
                "than the one selected.",
                remediation="Re-select the model after switching providers.",
                resource_ref=ResourceRef(
                    type="model", id=str(spec.model.id)
                ),
            )
        model_name = spec.model.name if spec.model else raw_model
        return self._pass(f"{self.service_label} model: {model_name}")


class ApiKeyPresentCheck(ShallowCheck, _LegCheckMixin):
    """Verify an ApiKey row exists for (org, provider, service_type)."""

    severity: ClassVar[Severity] = Severity.BLOCKER
    category: ClassVar[Category]

    async def run(self, ctx: CheckContext) -> CheckResult:
        spec = self._spec(ctx)
        if spec.provider is None:
            return self._skip("Provider not resolved (see provider check).")
        if spec.api_key is None:
            return self._fail(
                f"The {self.service_label} provider {quote(spec.provider.display_name)} "
                "has no API key saved.",
                remediation=(
                    f"Open Services → {spec.provider.display_name} and add a key."
                ),
                resource_ref=ResourceRef(
                    type="provider", id=str(spec.provider.id)
                ),
            )
        return self._pass(
            f"{self.service_label} API key saved for {spec.provider.display_name}."
        )


class ApiKeyDecryptsCheck(ShallowCheck, _LegCheckMixin):
    """Verify the saved ApiKey ciphertext decrypts with the current secret."""

    severity: ClassVar[Severity] = Severity.BLOCKER
    category: ClassVar[Category]

    async def run(self, ctx: CheckContext) -> CheckResult:
        spec = self._spec(ctx)
        if spec.api_key is None:
            return self._skip("No API key to decrypt (see key-present check).")
        if spec.decrypted_key is None:
            # Distinguish from "no key at all" — this is almost always a rotated
            # JWT_SECRET_KEY, so the remediation is different.
            return self._fail(
                f"{self.service_label} API key cannot be decrypted with the "
                "current server secret.",
                remediation=(
                    "The encryption secret has changed since this key was saved. "
                    f"Re-enter the {self.service_label} API key in Services."
                ),
                resource_ref=ResourceRef(
                    type="api_key", id=str(spec.api_key.id)
                ),
            )
        return self._pass(f"{self.service_label} API key decrypts successfully.")
