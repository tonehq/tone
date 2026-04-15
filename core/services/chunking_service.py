"""Split plain text into smaller chunks for embedding and retrieval."""

from typing import List, Dict, Any

from loguru import logger


class ChunkingService:
    """Splits text into chunks using LangChain's RecursiveCharacterTextSplitter.

    What is chunking?
    -----------------
    A document can be thousands of words long. You can't embed the whole thing
    as one piece — it's too big and the meaning gets diluted. So we split it
    into smaller pieces (chunks) of ~500 tokens each. Each chunk is small
    enough to have a clear, focused meaning, making search more accurate.

    The splitter tries to break on paragraphs first, then sentences, then words,
    so chunks stay as coherent as possible.
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Args:
            chunk_size: Max characters per chunk (~500 tokens at ~2 chars/token).
            chunk_overlap: Overlap between chunks so context isn't lost at boundaries.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, text: str) -> List[Dict[str, Any]]:
        """Split text into chunks. Returns list of dicts with chunk_index and chunk_text."""
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        texts = splitter.split_text(text)

        chunks = []
        for i, chunk_text in enumerate(texts):
            chunks.append({
                "chunk_index": i,
                "chunk_text": chunk_text,
            })

        logger.info(
            "Split text into {} chunks (chunk_size={}, overlap={})",
            len(chunks), self.chunk_size, self.chunk_overlap,
        )
        return chunks
