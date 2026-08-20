"""Typed errors for the shared chat-completion router.

Kept separate from ``chat_complete`` so callers can ``except`` a specific type
without importing the SDK-heavy router module.
"""

from __future__ import annotations


class LLMError(Exception):
    """Base class for router-level failures."""


class LLMProviderResolutionError(LLMError):
    """Raised when a model name doesn't match any known provider prefix.

    Message includes the offending model + the known prefix families so the
    eval-run row's error field is directly actionable for the operator.
    """


class LLMChatCompletionError(LLMError):
    """Raised when the underlying SDK call fails or returns empty content.

    Wraps the original exception in ``.__cause__``; the message carries the
    provider + model but NEVER the api_key.
    """


class LLMProviderKeyMissingError(LLMError):
    """Raised when the caller can resolve a provider from the model name but
    the organisation hasn't configured an API key for that provider (and no
    env-var fallback exists). Distinct from the embedding-side
    ``EmbeddingProviderUnavailableError`` so eval-run rows carry a clearer
    "which provider / which model" message.
    """
