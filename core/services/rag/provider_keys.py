"""Provider-key lookup — generalises the OpenAI-only helper that used to live
in ``document_tool_service.get_openai_api_key_for_agent``. Every RAG entry
point (ingest + retrieve) resolves keys through this single class so a new
embedding provider is a one-line factory registration plus an existing key row.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from core.models.api_key import ApiKey
from core.models.model_provider import ModelProvider
from core.services.rag.errors import EmbeddingProviderUnavailableError
from core.utils.encryption import decrypt


class ProviderKeyService:
    """Fetches and decrypts the active API key an organisation has configured
    for a given provider slug (matches ``model_providers.provider_id``).

    Transport-agnostic: takes a SQLAlchemy session + plain args and returns a
    plain string. Never logs the key.
    """

    @staticmethod
    def get_key(db: Session, org_id: Any, provider_slug: str) -> Optional[str]:
        row = (
            db.query(ApiKey)
            .join(ModelProvider, ModelProvider.id == ApiKey.provider_id)
            .filter(
                ModelProvider.provider_id == provider_slug,
                ApiKey.is_active.is_(True),
                ApiKey.organization_id == org_id,
            )
            .first()
        )
        if row and row.encrypted_key:
            return decrypt(row.encrypted_key)
        return None

    @staticmethod
    def require_key(db: Session, org_id: Any, provider_slug: str) -> str:
        key = ProviderKeyService.get_key(db, org_id, provider_slug)
        if not key:
            raise EmbeddingProviderUnavailableError(
                f"No {provider_slug!r} API key configured for organisation {org_id}"
            )
        return key
