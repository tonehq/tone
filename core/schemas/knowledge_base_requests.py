"""Request schemas for the knowledge-base document endpoints.

These mirror the fields the KB routes accepted as free-form dicts. They are
intentionally permissive: every field is optional and unknown keys are allowed
(``extra="allow"``) so clients that already send extra fields are not rejected.
The routers forward ``model_dump(exclude_unset=True)`` to the service layer,
keeping the downstream contract identical to the old dict body — the pipeline
service builds its recipe from the keys the client actually sent
(``{k: v for k, v in raw_body.items() if k in allowed}``), so only sent fields
must be present and the service keeps raising its own ``400`` for missing
required values.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class RenameDocumentRequest(BaseModel):
    """Body for ``PATCH /knowledge-base/documents/{upload_id}``.

    ``file_name`` stays optional so the router keeps raising its existing
    ``400 file_name is required`` (and length) checks instead of Pydantic's
    ``422``.
    """

    model_config = ConfigDict(extra="allow")

    file_name: Optional[str] = None


class PipelineRunRequest(BaseModel):
    """Body for ``POST /knowledge-base/documents/{upload_id}/runs``.

    Either ``ingestion_config_id`` (a saved recipe) or any subset of the
    individual recipe fields; anything omitted falls back to system defaults
    resolved by the service.
    """

    model_config = ConfigDict(extra="allow")

    ingestion_config_id: Optional[Any] = None
    parser: Optional[str] = None
    parser_config: Optional[Dict[str, Any]] = None
    tokeniser: Optional[str] = None
    tokeniser_config: Optional[Dict[str, Any]] = None
    embedding_provider: Optional[str] = None
    embedding_model: Optional[str] = None
    embedding_dimensions: Optional[int] = None
    embedding_version: Optional[str] = None
    vector_store: Optional[str] = None
    vector_store_ref: Optional[Dict[str, Any]] = None
