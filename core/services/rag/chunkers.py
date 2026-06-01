from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from loguru import logger

from core.services.rag.types import Chunk, Document


class Chunker(ABC):
    @abstractmethod
    def chunk(self, document: Document) -> List[Chunk]:
        ...


class RecursiveCharacterChunker(Chunker):
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, document: Document) -> List[Chunk]:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = [Chunk(index=i, text=t) for i, t in enumerate(splitter.split_text(document.text))]
        logger.info(
            "Split text into {} chunks (chunk_size={}, overlap={})",
            len(chunks), self.chunk_size, self.chunk_overlap,
        )
        return chunks


class DoclingChunker(Chunker):
    def __init__(self, embedding_model: str = "text-embedding-3-small", tokenizer=None,
                 max_tokens: int = None, hf_fallback_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self._embedding_model = embedding_model
        self._tokenizer = tokenizer
        self._max_tokens = max_tokens
        self._hf_fallback_model = hf_fallback_model
        self._chunker = None
        self._fallback = RecursiveCharacterChunker()

    def _resolve_tokenizer(self):
        if self._tokenizer is not None:
            return self._tokenizer
        if self._embedding_model:
            try:
                import tiktoken
                from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer

                enc = tiktoken.encoding_for_model(self._embedding_model)
                logger.info("Tokenizer: OpenAI ({})", self._embedding_model)
                return OpenAITokenizer(tokenizer=enc, max_tokens=self._max_tokens or 8191)
            except Exception as e:
                logger.warning("OpenAI tokenizer unavailable for {!r}: {}; falling back to HuggingFace {}",
                               self._embedding_model, e, self._hf_fallback_model)
        from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer

        logger.info("Tokenizer: HuggingFace ({})", self._hf_fallback_model)
        return HuggingFaceTokenizer.from_pretrained(self._hf_fallback_model, max_tokens=self._max_tokens or 512)

    def _get_chunker(self):
        if self._chunker is None:
            from docling.chunking import HybridChunker

            self._chunker = HybridChunker(tokenizer=self._resolve_tokenizer())
        return self._chunker

    def chunk(self, document: Document) -> List[Chunk]:
        if document.native is None:
            return self._fallback.chunk(document)
        chunker = self._get_chunker()
        chunks: List[Chunk] = []
        for i, ck in enumerate(chunker.chunk(dl_doc=document.native)):
            try:
                text = chunker.contextualize(chunk=ck)
            except Exception:
                text = getattr(ck, "text", "")
            if text:
                chunks.append(Chunk(index=i, text=text))
        logger.info("Docling chunked document into {} chunks", len(chunks))
        return chunks
