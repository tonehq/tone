"""Document tool for voice agents — lets the LLM search uploaded documents during a call.

How it works (step by step):
1. When building the pipeline, we check if the agent has any KB uploads.
2. If yes, we create a tool called "read_document" with a description listing the file names.
3. We register a handler so when the LLM calls read_document(query="..."), we:
   a. Look up the active ingestion run for each upload (cached at pipeline build).
   b. Group uploads by (vector_store, embedding_provider, embedding_model, dims) so one embedder + one store call covers each group.
   c. For each group: decrypt the provider's API key, embed the query with the SAME model that produced the stored vectors, query the store, and merge results across groups.
4. The LLM then speaks the answer based on the retrieved content.
"""

from collections import defaultdict
from typing import Any, List, Optional

from loguru import logger

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.llm_service import FunctionCallParams

from core.services.pipeline.tool_call_timing import (
    ToolCallTimer,
    finalize_and_record,
)

DEFAULT_TOP_K = 8


def get_document_tool_schema(document_names: List[str]) -> ToolsSchema:
    """Build the read_document tool schema with document names in the description.

    Args:
        document_names: List of file names linked to this agent (e.g., ["pricing.pdf", "faq.txt"])

    Returns:
        ToolsSchema ready to pass to LLMContext
    """
    names_str = ", ".join(document_names)
    description = (
        f"Search content from the following documents: {names_str}. "
        "Use this tool when the user asks a question that might be answered by these documents. "
        "Pass the user's question or a relevant search phrase as the query."
    )

    function_schema = FunctionSchema(
        name="read_document",
        description=description,
        properties={
            "query": {
                "type": "string",
                "description": "The search query to find relevant content in the documents",
            },
        },
        required=["query"],
    )

    return ToolsSchema(standard_tools=[function_schema])


def create_document_handler(
    agent_id: int,
    org_id: Any,
    upload_runs: List[dict],
    top_k: int = DEFAULT_TOP_K,
    tool_call_entries: Optional[list] = None,
    tool_request_ts: Optional[dict] = None,
    current_turn: Optional[dict] = None,
):
    """Create the handler function for read_document tool calls.

    Args:
        agent_id: The agent's ID (to scope chunk search)
        org_id: The organization ID
        upload_runs: One dict per ready upload describing its active ingestion run — see
            ``get_kb_document_names``. The handler groups by (vector_store, provider, model,
            dims) so we build one embedder / store per group.
        top_k: Number of top matching chunks to return
        tool_call_entries: Shared list to append tool call logs to (optional)
    """

    async def handle_read_document(params: FunctionCallParams) -> None:
        """Called when the LLM invokes read_document(query="...")."""
        import time as _time

        query = params.arguments.get("query", "")
        logger.info("read_document called: query='{}' agent_id={}", query, agent_id)
        _t_start = _time.monotonic()
        timer = ToolCallTimer.start(params, tool_request_ts)
        tool_call_entry = {
            "tool": "read_document",
            "tool_type": "read_document",
            "arguments": {"query": query},
            "timestamp": int(_time.time()),
            "turn": current_turn["number"] if current_turn else None,
            **timer.initial_fields(),
        }

        try:
            from core.database.session import get_db_context
            from core.services.rag.embedder_factory import get_embedder
            from core.services.rag.factory import get_vector_store
            from core.services.rag.provider_keys import ProviderKeyService

            # Group by the retrieval "space" — same embedder + store settings serve as one call.
            groups: dict[tuple, list[dict]] = defaultdict(list)
            for u in upload_runs or []:
                key = (
                    u["vector_store"],
                    u["embedding_provider"],
                    u["embedding_model"],
                    u["embedding_dimensions"],
                    tuple(sorted((u.get("vector_store_ref") or {}).items())),
                )
                groups[key].append(u)

            if not groups:
                await params.result_callback("No relevant content found in the documents.")
                tool_call_entry["result"] = "No relevant content found"
                tool_call_entry["chunks_returned"] = 0
                tool_call_entry["status_code"] = 200
                tool_call_entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
                finalize_and_record(tool_call_entry, timer, tool_call_entries)
                return

            merged: list = []
            failures = 0
            for key, uploads_in_group in groups.items():
                vector_store, provider, model, dims, ref_tuple = key
                vector_store_ref = dict(ref_tuple) if ref_tuple else {}
                run_ids = [u["ingestion_run_id"] for u in uploads_in_group]

                try:
                    with get_db_context() as db:
                        api_key = ProviderKeyService.get_key(db, org_id, provider)
                    if not api_key:
                        logger.warning(
                            "read_document: no {!r} API key for org {}, skipping group",
                            provider, org_id,
                        )
                        failures += 1
                        continue
                    embedder = get_embedder(
                        provider, model=model, api_key=api_key, dimensions=dims
                    )
                    store = get_vector_store(vector_store, **vector_store_ref)
                    query_embedding = embedder.embed_query(query)
                    # Per-agent published-config filter still applies inside store.query;
                    # we additionally pin the exact ingestion_run_ids from this group so
                    # a stale row from another run can't leak in.
                    for run_id in run_ids:
                        results = store.query(
                            query_embedding,
                            top_k=top_k,
                            filters={
                                "agent_id": str(agent_id),
                                "ingestion_run_id": run_id,
                                "embedding_provider": provider,
                                "embedding_model": model,
                                "embedding_dimensions": dims,
                            },
                        )
                        merged.extend(results)
                except Exception:
                    logger.exception(
                        "read_document: group ({}, {}, {}, {}D) failed", vector_store, provider, model, dims
                    )
                    failures += 1

            if not merged:
                if failures and failures == len(groups):
                    await params.result_callback(
                        "Document search is currently unavailable. Please try again."
                    )
                    tool_call_entry["result"] = "search unavailable"
                    tool_call_entry["chunks_returned"] = 0
                    tool_call_entry["status_code"] = 503
                    tool_call_entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
                    finalize_and_record(tool_call_entry, timer, tool_call_entries)
                    return
                await params.result_callback("No relevant content found in the documents.")
                tool_call_entry["result"] = "No relevant content found"
                tool_call_entry["chunks_returned"] = 0
                tool_call_entry["status_code"] = 200
                tool_call_entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
                finalize_and_record(tool_call_entry, timer, tool_call_entries)
                return

            merged.sort(key=lambda r: r.score)
            top = merged[:top_k]
            chunks_text = "\n\n---\n\n".join(r.text for r in top)
            result = f"Here is the relevant content from the documents:\n\n{chunks_text}"
            logger.info("read_document returning {} chunks for query='{}'", len(top), query)

            tool_call_entry["result"] = "success"
            tool_call_entry["chunks_returned"] = len(top)
            tool_call_entry["status_code"] = 200
            tool_call_entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
            finalize_and_record(tool_call_entry, timer, tool_call_entries)

            await params.result_callback(result)

        except Exception as e:
            logger.exception("read_document failed")
            tool_call_entry["result"] = f"error: {str(e)}"
            tool_call_entry["status_code"] = 500
            tool_call_entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
            finalize_and_record(tool_call_entry, timer, tool_call_entries)
            await params.result_callback(f"Error searching documents: {str(e)}")

    return handle_read_document


def get_document_names_for_agent(agent_id: int, org_id: Any) -> List[str]:
    """Fetch file names of all ready KB uploads for an agent's published version."""
    from core.database.session import get_db_context
    from core.models.upload import Upload
    from core.models.agent_knowledge_base import AgentKnowledgeBase
    from core.models.knowledge_base import KnowledgeBase
    from core.utils.agent_scope import published_config_subquery

    published_config_sq = published_config_subquery(agent_id)

    with get_db_context() as db:
        rows = (
            db.query(Upload.file_name)
            .join(KnowledgeBase, KnowledgeBase.upload_id == Upload.id)
            .join(AgentKnowledgeBase, AgentKnowledgeBase.knowledge_base_id == KnowledgeBase.id)
            .filter(
                AgentKnowledgeBase.agent_id == agent_id,
                AgentKnowledgeBase.agent_config_id == published_config_sq,
                Upload.status == "ready",
            )
            .all()
        )
    return [row[0] for row in rows if row[0]]


def get_openai_api_key_for_agent(org_id: Any) -> Optional[str]:
    """Fetch and decrypt the OpenAI API key from DB for embedding.

    Thin wrapper on ``ProviderKeyService.get_key`` so legacy callers keep the
    old signature while new code flows through the general provider lookup.
    """
    from core.database.session import get_db_context
    from core.services.rag.provider_keys import ProviderKeyService

    with get_db_context() as db:
        return ProviderKeyService.get_key(db, org_id, "openai")


def get_kb_refs(agent_id: int) -> List[dict]:
    """`[{id, name}, ...]` for the agent's active knowledge bases.

    Cached alongside the rest of the pipeline payload so the call-log snapshot can
    record which KBs were available without a per-call DB hit. Mirrors the
    `KnowledgeBase.is_active` filter the runner's original inline query used.
    """
    from core.database.session import get_db_context
    from core.models.agent_knowledge_base import AgentKnowledgeBase
    from core.models.knowledge_base import KnowledgeBase
    from core.utils.agent_scope import published_config_subquery

    published_config_sq = published_config_subquery(agent_id)

    with get_db_context() as db:
        rows = (
            db.query(KnowledgeBase.id, KnowledgeBase.name)
            .join(AgentKnowledgeBase, AgentKnowledgeBase.knowledge_base_id == KnowledgeBase.id)
            .filter(
                AgentKnowledgeBase.agent_id == agent_id,
                AgentKnowledgeBase.agent_config_id == published_config_sq,
                KnowledgeBase.is_active.is_(True),
            )
            .all()
        )
    return [{"id": str(r.id), "name": r.name} for r in rows]


def get_kb_document_names(agent_id: int) -> Optional[dict]:
    """The agent's ready KB documents + each upload's active ingestion run.

    Cached per-agent so ``build_document_tool`` + the retrieval handler run
    with NO per-call KB DB query. One join to ``ingestion_pipeline_runs`` (the
    active row per upload) means callers know which embedder / store to
    instantiate at retrieval without a second DB hit.
    """
    from core.database.session import get_db_context
    from core.models.upload import Upload
    from core.models.agent_knowledge_base import AgentKnowledgeBase
    from core.models.ingestion_pipeline_run import IngestionPipelineRun
    from core.models.knowledge_base import KnowledgeBase

    from core.utils.agent_scope import published_config_subquery

    published_config_sq = published_config_subquery(agent_id)

    with get_db_context() as db:
        rows = (
            db.query(
                Upload.file_name,
                Upload.id.label("upload_id"),
                IngestionPipelineRun.id.label("run_id"),
                IngestionPipelineRun.embedding_provider,
                IngestionPipelineRun.embedding_model,
                IngestionPipelineRun.embedding_dimensions,
                IngestionPipelineRun.vector_store,
                IngestionPipelineRun.vector_store_ref,
            )
            .join(KnowledgeBase, KnowledgeBase.upload_id == Upload.id)
            .join(AgentKnowledgeBase, AgentKnowledgeBase.knowledge_base_id == KnowledgeBase.id)
            .outerjoin(
                IngestionPipelineRun,
                (IngestionPipelineRun.upload_id == Upload.id)
                & (IngestionPipelineRun.is_active.is_(True)),
            )
            .filter(
                AgentKnowledgeBase.agent_id == agent_id,
                AgentKnowledgeBase.agent_config_id == published_config_sq,
                Upload.status == "ready",
            )
            .all()
        )
    doc_names = [row.file_name for row in rows if row.file_name]
    upload_ids = [str(row.upload_id) for row in rows]
    upload_runs = [
        {
            "upload_id": str(row.upload_id),
            "file_name": row.file_name,
            "ingestion_run_id": str(row.run_id) if row.run_id else None,
            "embedding_provider": row.embedding_provider,
            "embedding_model": row.embedding_model,
            "embedding_dimensions": row.embedding_dimensions,
            "vector_store": row.vector_store,
            "vector_store_ref": row.vector_store_ref,
        }
        for row in rows
        if row.run_id is not None
    ]
    if not doc_names:
        return None
    return {
        "document_names": doc_names,
        "upload_ids": upload_ids,
        "upload_runs": upload_runs,
    }


def build_document_tool(
    llm: Any, agent_id: int, org_id: Any, kb: Optional[dict],
    tool_call_entries: Optional[list] = None, tool_request_ts: Optional[dict] = None,
    current_turn: Optional[dict] = None,
) -> Optional[ToolsSchema]:
    """Build + register the read_document tool from the cached `kb` dict (no KB DB query).

    The actual vector search still runs live at call time inside the handler.
    Returns the ToolsSchema (for LLMContext) or None if the agent has no KB documents.
    """
    if not kb or not kb.get("document_names"):
        logger.info("Agent {} has no KB documents, skipping tool registration", agent_id)
        return None

    doc_names = kb["document_names"]
    upload_runs = kb.get("upload_runs") or []
    if not upload_runs:
        logger.warning(
            "Agent {} has KB documents but no active ingestion runs; skipping tool", agent_id
        )
        return None

    tools_schema = get_document_tool_schema(doc_names)
    handler = create_document_handler(
        agent_id, org_id, upload_runs,
        tool_call_entries=tool_call_entries,
        tool_request_ts=tool_request_ts,
        current_turn=current_turn,
    )
    llm.register_function("read_document", handler)
    logger.info("Registered read_document tool for agent {} with docs: {}", agent_id, doc_names)
    return tools_schema


def register_document_tool(llm: Any, agent_id: int, org_id: Any, tool_call_entries: Optional[list] = None, tool_request_ts: Optional[dict] = None, current_turn: Optional[dict] = None) -> Optional[ToolsSchema]:
    """Back-compat entry point: fetch the agent's KB docs from the DB, then build the tool.
    New callers should cache `get_kb_document_names()` and call `build_document_tool()`."""
    kb = get_kb_document_names(agent_id)
    return build_document_tool(
        llm, agent_id, org_id, kb,
        tool_call_entries=tool_call_entries,
        tool_request_ts=tool_request_ts,
        current_turn=current_turn,
    )
