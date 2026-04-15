"""Document tool for voice agents — lets the LLM search uploaded documents during a call.

How it works (step by step):
1. When building the pipeline, we check if the agent has any documents uploaded.
2. If yes, we create a tool called "read_document" with a description listing the doc names.
3. We register a handler so when the LLM calls read_document(query="..."), we:
   a. Convert the query into an embedding (list of numbers representing meaning)
   b. Search document_chunks using pgvector to find the closest matching chunks
   c. Return the chunk texts back to the LLM so it can answer the user
4. The LLM then speaks the answer based on the retrieved content.
"""

from typing import Any, List, Optional

from loguru import logger

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.llm_service import FunctionCallParams


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


def create_document_handler(agent_id: int, org_id: Any, api_key: str, top_k: int = 3):
    """Create the handler function for read_document tool calls.

    Args:
        agent_id: The agent's ID (to scope chunk search)
        org_id: The organization ID
        api_key: Decrypted OpenAI API key for embedding the query
        top_k: Number of top matching chunks to return

    Returns:
        An async handler function compatible with Pipecat's register_function
    """

    async def handle_read_document(params: FunctionCallParams) -> None:
        """Called when the LLM invokes read_document(query="...").

        Steps:
        1. Get the query from params.arguments
        2. Embed the query using OpenAI (same model used at upload time)
        3. Search document_chunks with pgvector similarity (<=> operator)
        4. Return the top matching chunk texts to the LLM via result_callback
        """
        query = params.arguments.get("query", "")
        logger.info("read_document called: query='{}' agent_id={}", query, agent_id)

        try:
            from core.services.embedding_service import EmbeddingService
            from core.database.session import get_db_context
            from core.models.document import Document, DocumentChunk
            from sqlalchemy import text

            # Step 1: Embed the query
            embedder = EmbeddingService(api_key)
            query_embedding = embedder.embed_query(query)

            # Step 2: Search document_chunks using pgvector similarity
            with get_db_context() as db:
                # Find all document IDs for this agent
                doc_ids = (
                    db.query(Document.id)
                    .filter(Document.agent_id == agent_id, Document.status == "ready")
                    .all()
                )
                doc_ids = [d[0] for d in doc_ids]

                if not doc_ids:
                    await params.result_callback("No documents are available for this agent.")
                    return

                # pgvector similarity search using <=> (cosine distance) operator
                embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
                query_sql = text("""
                    SELECT chunk_text, embedding <=> :embedding AS distance
                    FROM document_chunks
                    WHERE document_id = ANY(:doc_ids)
                    ORDER BY embedding <=> :embedding
                    LIMIT :top_k
                """)
                results = db.execute(
                    query_sql,
                    {"embedding": embedding_str, "doc_ids": doc_ids, "top_k": top_k},
                ).fetchall()

            if not results:
                await params.result_callback("No relevant content found in the documents.")
                return

            # Step 3: Combine chunk texts and return to LLM
            chunks_text = "\n\n---\n\n".join(row[0] for row in results)
            result = f"Here is the relevant content from the documents:\n\n{chunks_text}"
            logger.info("read_document returning {} chunks for query='{}'", len(results), query)
            await params.result_callback(result)

        except Exception as e:
            logger.error("read_document failed: {}", e)
            await params.result_callback(f"Error searching documents: {str(e)}")

    return handle_read_document


def get_document_names_for_agent(agent_id: int, org_id: Any) -> List[str]:
    """Fetch file names of all ready documents for an agent."""
    from core.database.session import get_db_context
    from core.models.document import Document
    from core.models.upload import Upload

    with get_db_context() as db:
        rows = (
            db.query(Upload.file_name)
            .join(Document, Document.upload_id == Upload.id)
            .filter(Document.agent_id == agent_id, Document.status == "ready")
            .all()
        )
    return [row[0] for row in rows if row[0]]


def get_openai_api_key_for_agent(org_id: Any) -> Optional[str]:
    """Fetch and decrypt the OpenAI API key from DB for embedding."""
    from core.database.session import get_db_context
    from core.models.service_provider import ServiceProvider
    from core.models.api_key import ApiKey
    from core.utils.encryption import decrypt

    with get_db_context() as db:
        provider = (
            db.query(ServiceProvider)
            .filter(ServiceProvider.name == "openai", ServiceProvider.provider_type == "llm")
            .first()
        )
        if not provider:
            return None

        api_key_record = (
            db.query(ApiKey)
            .filter(
                ApiKey.service_provider_id == provider.id,
                ApiKey.status == "active",
                ApiKey.organization_id == org_id,
            )
            .first()
        )
        if not api_key_record or not api_key_record.api_key_encrypted:
            return None

        return decrypt(api_key_record.api_key_encrypted)


def register_document_tool(llm: Any, agent_id: int, org_id: Any) -> Optional[ToolsSchema]:
    """Main entry point — call this from agent_factory_service after LLM is created.

    Checks if the agent has documents, and if so:
    1. Builds the tool schema with document names
    2. Registers the handler on the LLM
    3. Returns the ToolsSchema (to pass to LLMContext)

    Returns None if the agent has no documents.
    """
    # Check if agent has any ready documents
    doc_names = get_document_names_for_agent(agent_id, org_id)
    if not doc_names:
        logger.info("Agent {} has no documents, skipping tool registration", agent_id)
        return None

    # Get OpenAI API key for embedding queries at call time
    api_key = get_openai_api_key_for_agent(org_id)
    if not api_key:
        logger.warning("No OpenAI API key found for org {}, skipping document tool", org_id)
        return None

    # Build tool schema and handler
    tools_schema = get_document_tool_schema(doc_names)
    handler = create_document_handler(agent_id, org_id, api_key)

    # Register handler on the LLM
    llm.register_function("read_document", handler)
    logger.info("Registered read_document tool for agent {} with docs: {}", agent_id, doc_names)

    return tools_schema
