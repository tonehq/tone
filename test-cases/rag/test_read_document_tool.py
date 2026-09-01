"""Negative/edge tests for the read_document voice tool handler
(``core/services/document_tool_service.create_document_handler``).

Two failure modes that must NOT crash the call:

1. Vector-store (pgvector) query error — when EVERY retrieval group fails, the
   handler swallows the store exception and answers with a safe "unavailable"
   line via ``result_callback``; no exception escapes the handler.
2. Query before ingestion completes — with no ready ingestion runs (empty
   ``upload_runs``), the handler short-circuits to
   "No relevant content found in the documents." instead of erroring.

The handler resolves its collaborators via function-local imports
(``from core.services.rag.embedder_factory import get_embedder`` etc.), so we
patch them at their SOURCE modules rather than on ``document_tool_service``.
"""

import asyncio
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from core.services.document_tool_service import create_document_handler


class FakeParams:
    """Minimal stand-in for pipecat's ``FunctionCallParams`` — the handler only
    touches ``.arguments`` and awaits ``.result_callback``. ``tool_call_id`` is
    read via ``getattr(..., None)`` so a plain attribute is enough."""

    def __init__(self, query: str):
        self.arguments = {"query": query}
        self.tool_call_id = None
        self.captured: list[str] = []

    async def result_callback(self, message: str) -> None:
        self.captured.append(message)


def _upload_run():
    """One entry shaped like ``get_kb_document_names`` output."""
    return {
        "upload_id": "u1",
        "file_name": "pricing.pdf",
        "ingestion_run_id": "run-1",
        "embedding_provider": "openai",
        "embedding_model": "text-embedding-3-small",
        "embedding_dimensions": 3,
        "vector_store": "pgvector",
        "vector_store_ref": {},
    }


@contextmanager
def _fake_db_ctx():
    yield MagicMock()


def test_vector_store_query_error_is_handled_not_raised():
    """pgvector ``.query`` raising must be caught: all groups fail → the
    handler sends the 'unavailable' line and returns without propagating."""
    handler = create_document_handler(
        agent_id=7, org_id="org-1", upload_runs=[_upload_run()], top_k=3
    )

    fake_embedder = MagicMock()
    fake_embedder.embed_query.return_value = [0.0] * 3

    fake_store = MagicMock()
    fake_store.query.side_effect = RuntimeError("db down")

    params = FakeParams("what is the price?")

    with patch(
        "core.database.session.get_db_context", _fake_db_ctx
    ), patch(
        "core.services.rag.provider_keys.ProviderKeyService.get_key",
        return_value="fake-key",
    ), patch(
        "core.services.rag.embedder_factory.get_embedder",
        return_value=fake_embedder,
    ), patch(
        "core.services.rag.factory.get_vector_store",
        return_value=fake_store,
    ):
        # No exception must escape the handler.
        asyncio.run(handler(params))

    assert fake_store.query.called
    assert len(params.captured) == 1
    assert "unavailable" in params.captured[0].lower()


def test_query_before_ingestion_returns_no_relevant_content():
    """With no ready ingestion runs (pre-ingestion state), the handler must
    answer 'No relevant content found in the documents.' and return cleanly —
    never touching the DB / embedder / store."""
    handler = create_document_handler(
        agent_id=7, org_id="org-1", upload_runs=[], top_k=3
    )
    params = FakeParams("anything")

    asyncio.run(handler(params))

    assert params.captured == ["No relevant content found in the documents."]
