"""Typed errors for the ingestion-config + ingestion-run services.

Mirrors the pattern in ``core/services/evals/errors.py`` and
``core/services/rag/errors.py`` so the service layer stays transport-agnostic
(no ``HTTPException`` imports). The router layer catches each subclass and
maps it to the appropriate HTTP status + user-facing message.
"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError


# ── DB helpers ───────────────────────────────────────────────────────────────

# Postgres SQLSTATE code for unique-violation. Used across the ingestion
# flow to differentiate an "already exists" collision from other integrity
# failures (NOT NULL, CHECK, FK) that must NOT be mapped to a friendly 400.
PG_UNIQUE_VIOLATION = "23505"


def is_unique_violation(exc: IntegrityError) -> bool:
    """True when an ``IntegrityError`` was raised by a Postgres
    unique-constraint violation (SQLSTATE ``23505``). Every other
    ``IntegrityError`` (NOT NULL, CHECK, FK) is a real bug and must surface
    as a 500 after ``logger.exception``."""
    orig = getattr(exc, "orig", None)
    return getattr(orig, "pgcode", None) == PG_UNIQUE_VIOLATION


class IngestionError(Exception):
    """Base for every ingestion-config / ingestion-run service error."""


class IngestionValidationError(IngestionError):
    """Caller-supplied input failed validation (blank name, non-positive
    embedding dimensions, etc.). Maps to HTTP 400."""


class IngestionConfigNotFoundError(IngestionError):
    """Ingestion config row does not exist for the caller's (org, id) scope.
    Maps to HTTP 404."""


class IngestionConfigNameConflictError(IngestionError):
    """Attempted create/update collides with an existing config name in the
    same org. Maps to HTTP 400."""


class IngestionConfigInactiveError(IngestionError):
    """Attempted to start a run from an ``is_active=false`` config. Maps to
    HTTP 400 — the config is user-hidden and cannot be dialled."""


class UnknownRagComponentError(IngestionValidationError):
    """The supplied parser/tokeniser/embedding_provider/vector_store slug is
    not registered. Maps to HTTP 400. Carries ``kind`` and ``slug`` so the
    router / logs can render an ``Available: [...]`` hint."""

    def __init__(self, kind: str, slug: str, available: list[str]):
        super().__init__(
            f"Unknown {kind} {slug!r}. Available: {', '.join(sorted(available))}."
        )
        self.kind = kind
        self.slug = slug
        self.available = list(available)


class IngestionRunNotFoundError(IngestionError, LookupError):
    """Ingestion pipeline run row does not exist for the caller's
    (org, upload, id) scope. Maps to HTTP 404. Also subclasses
    ``LookupError`` so callers that prefer the stdlib base still work — the
    previous inline definition in ``ingestion_run_service`` inherited from
    ``LookupError``."""


class IngestionRunNotReadyError(IngestionError):
    """Attempted to activate / pin / eval-run a pipeline run whose status is
    not ``ready``. Maps to HTTP 400. Carries the actual status so the router
    can render it verbatim."""

    def __init__(self, status: str, action: str = "use"):
        super().__init__(
            f"Cannot {action} a run with status={status!r}; only 'ready' is allowed"
        )
        self.status = status
        self.action = action


class IngestionRunKbMismatchError(IngestionError):
    """Attempted to pin a run whose ``knowledge_base_id`` differs from the
    ``AgentKnowledgeBase`` row being pinned. Maps to HTTP 400."""


class AgentHasNoPublishedConfigError(IngestionError):
    """Referenced agent has no ``published_config_id`` — cannot resolve the
    published ``AgentKnowledgeBase`` row. Maps to HTTP 404."""


class AgentKnowledgeBaseNotFoundError(IngestionError):
    """The KB is not attached to the agent's published config. Maps to
    HTTP 404."""
