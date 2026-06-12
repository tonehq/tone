"""Document tool for voice agents — lets the LLM search uploaded documents during a call.

How it works (step by step):
1. When building the pipeline, we check if the agent has any KB uploads.
2. If yes, we create a tool called "read_document" with a description listing the file names.
3. We register a handler so when the LLM calls read_document(query="..."), we:
   a. Convert the query into an embedding (list of numbers representing meaning)
   b. Search knowledge_base_chunks using pgvector to find the closest matching chunks
   c. Return the chunk texts back to the LLM so it can answer the user
4. The LLM then speaks the answer based on the retrieved content.
"""

from typing import Any, List, Optional

from loguru import logger

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.llm_service import FunctionCallParams

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


def create_document_handler(agent_id: int, org_id: Any, api_key: str, upload_ids: List, top_k: int = DEFAULT_TOP_K, tool_call_entries: Optional[list] = None, current_turn: Optional[dict] = None):
    """Create the handler function for read_document tool calls.

    Args:
        agent_id: The agent's ID (to scope chunk search)
        org_id: The organization ID
        api_key: Decrypted OpenAI API key for embedding the query
        upload_ids: Pre-fetched list of ready upload IDs for this agent
        top_k: Number of top matching chunks to return
        tool_call_entries: Shared list to append tool call logs to (optional)

    Returns:
        An async handler function compatible with Pipecat's register_function
    """

    async def handle_read_document(params: FunctionCallParams) -> None:
        """Called when the LLM invokes read_document(query="...").

        Steps:
        1. Get the query from params.arguments
        2. Embed the query using OpenAI (same model used at upload time)
        3. Search knowledge_base_chunks with pgvector similarity (<=> operator)
        4. Return the top matching chunk texts to the LLM via result_callback
        """
        import time as _time

        query = params.arguments.get("query", "")
        logger.info("read_document called: query='{}' agent_id={}", query, agent_id)
        _t_start = _time.monotonic()
        tool_call_entry = {
            "tool": "read_document",
            "arguments": {"query": query},
            "timestamp": int(_time.time()),
            "turn": current_turn["number"] if current_turn else None,
        }

        try:
            from core.services.rag.embedders import OpenAIEmbedder
            from core.services.rag.vector_stores.pgvector_store import PgVectorStore

            query_embedding = OpenAIEmbedder(api_key).embed_query(query)
            results = PgVectorStore().query(
                query_embedding, top_k=top_k, filters={"agent_id": str(agent_id)}
            )

            if not results:
                tool_call_entry["result"] = "No relevant content found"
                tool_call_entry["chunks_returned"] = 0
                tool_call_entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
                if tool_call_entries is not None:
                    tool_call_entries.append(tool_call_entry)
                await params.result_callback("No relevant content found in the documents.")
                return

            chunks_text = "\n\n---\n\n".join(r.text for r in results)
            result = f"Here is the relevant content from the documents:\n\n{chunks_text}"
            logger.info("read_document returning {} chunks for query='{}'", len(results), query)

            tool_call_entry["result"] = "success"
            tool_call_entry["chunks_returned"] = len(results)
            tool_call_entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
            if tool_call_entries is not None:
                tool_call_entries.append(tool_call_entry)

            await params.result_callback(result)

        except Exception as e:
            logger.error("read_document failed: {}", e)
            tool_call_entry["result"] = f"error: {str(e)}"
            tool_call_entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
            if tool_call_entries is not None:
                tool_call_entries.append(tool_call_entry)
            await params.result_callback(f"Error searching documents: {str(e)}")

    return handle_read_document


def _published_config_subquery(agent_id: Any):
    """Scalar subquery: the published config id for the given agent.

    Attachments are per-version, so every runtime KB read must filter by the
    agent's currently-published config — never a draft and never the union
    across versions.
    """
    from sqlalchemy import select

    from core.models.agent import Agent

    return select(Agent.published_config_id).where(Agent.id == agent_id).scalar_subquery()


def get_document_names_for_agent(agent_id: int, org_id: Any) -> List[str]:
    """Fetch file names of all ready KB uploads for an agent's published version."""
    from core.database.session import get_db_context
    from core.models.upload import Upload
    from core.models.agent_knowledge_base import AgentKnowledgeBase
    from core.models.knowledge_base import KnowledgeBase

    published_config_sq = _published_config_subquery(agent_id)

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
    """Fetch and decrypt the OpenAI API key from DB for embedding."""
    from core.database.session import get_db_context
    from core.models.api_key import ApiKey
    from core.models.model_provider import ModelProvider
    from core.utils.encryption import decrypt

    with get_db_context() as db:
        row = (
            db.query(ApiKey)
            .join(ModelProvider, ModelProvider.id == ApiKey.provider_id)
            .filter(
                ModelProvider.provider_id == "openai",
                ApiKey.is_active.is_(True),
                ApiKey.organization_id == org_id,
            )
            .first()
        )
        if row and row.encrypted_key:
            return decrypt(row.encrypted_key)

    return None


def get_kb_refs(agent_id: int) -> List[dict]:
    """`[{id, name}, ...]` for the agent's active knowledge bases.

    Cached alongside the rest of the pipeline payload so the call-log snapshot can
    record which KBs were available without a per-call DB hit. Mirrors the
    `KnowledgeBase.is_active` filter the runner's original inline query used.
    """
    from core.database.session import get_db_context
    from core.models.agent_knowledge_base import AgentKnowledgeBase
    from core.models.knowledge_base import KnowledgeBase

    published_config_sq = _published_config_subquery(agent_id)

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
    """The agent's ready KB documents (the only DB query for KB), as a cacheable dict
    `{"document_names": [...], "upload_ids": [...]}` or None when the agent has no KB.
    Stored in the agent pipeline cache; `build_document_tool` consumes it with no DB query."""
    from core.database.session import get_db_context
    from core.models.upload import Upload
    from core.models.agent_knowledge_base import AgentKnowledgeBase
    from core.models.knowledge_base import KnowledgeBase

    published_config_sq = _published_config_subquery(agent_id)

    with get_db_context() as db:
        upload_rows = (
            db.query(Upload.file_name, Upload.id)
            .join(KnowledgeBase, KnowledgeBase.upload_id == Upload.id)
            .join(AgentKnowledgeBase, AgentKnowledgeBase.knowledge_base_id == KnowledgeBase.id)
            .filter(
                AgentKnowledgeBase.agent_id == agent_id,
                AgentKnowledgeBase.agent_config_id == published_config_sq,
                Upload.status == "ready",
            )
            .all()
        )
    doc_names = [row[0] for row in upload_rows if row[0]]
    upload_ids = [str(row[1]) for row in upload_rows]
    if not doc_names:
        return None
    return {"document_names": doc_names, "upload_ids": upload_ids}


def build_document_tool(
    llm: Any, agent_id: int, org_id: Any, kb: Optional[dict],
    tool_call_entries: Optional[list] = None, current_turn: Optional[dict] = None,
) -> Optional[ToolsSchema]:
    """Build + register the read_document tool from the cached `kb` dict (no KB DB query).

    The pgvector search still runs live at call time inside the handler. Returns the
    ToolsSchema (for LLMContext) or None if the agent has no KB documents.
    """
    if not kb or not kb.get("document_names"):
        logger.info("Agent {} has no KB documents, skipping tool registration", agent_id)
        return None

    doc_names = kb["document_names"]
    upload_ids = kb.get("upload_ids") or []

    api_key = get_openai_api_key_for_agent(org_id)
    if not api_key:
        logger.warning("No OpenAI API key found for org {}, skipping document tool", org_id)
        return None

    tools_schema = get_document_tool_schema(doc_names)
    handler = create_document_handler(agent_id, org_id, api_key, upload_ids, tool_call_entries=tool_call_entries, current_turn=current_turn)
    llm.register_function("read_document", handler)
    logger.info("Registered read_document tool for agent {} with docs: {}", agent_id, doc_names)
    return tools_schema


def register_document_tool(llm: Any, agent_id: int, org_id: Any, tool_call_entries: Optional[list] = None, current_turn: Optional[dict] = None) -> Optional[ToolsSchema]:
    """Back-compat entry point: fetch the agent's KB docs from the DB, then build the tool.
    New callers should cache `get_kb_document_names()` and call `build_document_tool()`."""
    kb = get_kb_document_names(agent_id)
    return build_document_tool(llm, agent_id, org_id, kb, tool_call_entries=tool_call_entries, current_turn=current_turn)
