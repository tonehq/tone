"""Shared judge-model API-key resolution for every eval flow.

The judge model may point at a different provider than the thing being scored
(e.g. an agent on Anthropic scored by a judge on OpenAI). This is the ONE place
that turns a ``judge_model`` into a usable API key so the agent-LLM eval, the
call-transcript eval, and the scenario generator can't drift on the resolution
rule or the "no key configured" error wording.

Transport-agnostic: takes an open SQLAlchemy session + plain args and returns
the key string, raising ``error_cls`` (the caller's flow-specific config error)
on any failure so the caller's existing error handling is preserved.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from core.services.evals.errors import EvalConfigurationError


def resolve_judge_key(
    db: Session,
    *,
    organization_id: UUID,
    judge_model: str,
    fallback_provider: Optional[str],
    fallback_key: Optional[str] = None,
    error_cls: type[Exception] = EvalConfigurationError,
) -> str:
    """Resolve the API key for ``judge_model``'s provider.

    - When ``fallback_key`` is given and the judge shares the caller's
      ``fallback_provider``, return it directly (dev machines with a single
      key set still work without a separate judge key).
    - Otherwise fetch the org's stored key for the judge's provider.
    - Raise ``error_cls`` when the provider can't be resolved or no key exists.
    """
    # Local imports mirror the original call sites and avoid an import cycle
    # (chat_complete / provider_keys pull in service modules).
    from core.services.llm.chat_complete import resolve_provider
    from core.services.rag.provider_keys import ProviderKeyService

    try:
        judge_provider = resolve_provider(judge_model)
    except Exception as e:  # noqa: BLE001
        raise error_cls(
            f"Cannot resolve provider for judge model {judge_model!r}: {e}"
        ) from e

    if fallback_provider and judge_provider == fallback_provider and fallback_key:
        return fallback_key

    key = ProviderKeyService.get_key(db, organization_id, judge_provider)
    if not key:
        raise error_cls(
            f"No {judge_provider!r} API key configured for organisation "
            f"{organization_id} (needed by judge model {judge_model!r})."
        )
    return key
