"""Generate vector embeddings for text chunks using OpenAI's embedding API."""

from typing import List

from loguru import logger


class EmbeddingService:
    """Generates embeddings using OpenAI's text-embedding-3-small model.

    What is an embedding?
    ---------------------
    An embedding converts text into a list of 1536 numbers (a vector).
    These numbers represent the *meaning* of the text. Similar texts will
    have similar numbers. When a user asks "What's the refund policy?",
    we convert that question into numbers too, then find which chunk's
    numbers are closest — that's the most relevant chunk.

    Think of it like plotting text on a map. Similar meanings are close
    together on the map. Searching = finding the nearest point.
    """

    MODEL = "text-embedding-3-small"

    def __init__(self, api_key: str):
        """
        Args:
            api_key: OpenAI API key (decrypted from DB).
        """
        self.api_key = api_key

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts. Returns list of vectors (each 1536 floats)."""
        import openai

        client = openai.OpenAI(api_key=self.api_key)

        # OpenAI supports batching — send all chunks in one API call
        response = client.embeddings.create(
            model=self.MODEL,
            input=texts,
        )

        embeddings = [item.embedding for item in response.data]
        logger.info(
            "Generated {} embeddings (model={}, dimensions={})",
            len(embeddings), self.MODEL, len(embeddings[0]) if embeddings else 0,
        )
        return embeddings

    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a single query string. Used at search time."""
        result = self.embed_texts([query])
        return result[0]
