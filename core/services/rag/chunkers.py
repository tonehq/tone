from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from docling.chunking import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

from core.services.rag.tokenizers import Tokenizer
from core.services.rag.types import Chunk, Document


class Chunker(ABC):
    @abstractmethod
    def chunk(self, document: Document) -> List[Chunk]:
        ...


class TokenAwareChunker(Chunker):
    def __init__(self, tokenizer: Tokenizer, max_tokens: int = 512, overlap_tokens: int = 64):
        self.tokenizer = tokenizer
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, document: Document) -> List[Chunk]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.max_tokens,
            chunk_overlap=self.overlap_tokens,
            length_function=self.tokenizer.count_tokens,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = [Chunk(index=i, text=t) for i, t in enumerate(splitter.split_text(document.text))]
        logger.info(
            "Token-aware split into {} chunks (max_tokens={}, tokenizer={})",
            len(chunks), self.max_tokens, type(self.tokenizer).__name__,
        )
        return chunks


class RecursiveCharacterChunker(Chunker):
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, document: Document) -> List[Chunk]:
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


class DoclingHybridChunker(Chunker):
    def __init__(self, max_tokens: int = 512, embedding_model: str = "text-embedding-3-small"):
        self.max_tokens = max_tokens
        self.embedding_model = embedding_model
        self._chunker = None
        self._fallback = None

    def _resolve_tokenizer(self):
        try:
            import tiktoken

            return OpenAITokenizer(
                tokenizer=tiktoken.encoding_for_model(self.embedding_model),
                max_tokens=self.max_tokens,
            )
        except Exception as e:
            logger.info("OpenAI tokenizer unavailable ({}); using HuggingFace tokenizer", e)
            return HuggingFaceTokenizer.from_pretrained(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                max_tokens=self.max_tokens,
            )

    def _get_chunker(self):
        if self._chunker is None:
            self._chunker = HybridChunker(tokenizer=self._resolve_tokenizer())
        return self._chunker

    def chunk(self, document: Document) -> List[Chunk]:
        if document.native is None:
            if self._fallback is None:
                self._fallback = RecursiveCharacterChunker()
            return self._fallback.chunk(document)
        chunker = self._get_chunker()
        chunks: List[Chunk] = []
        for i, ch in enumerate(chunker.chunk(dl_doc=document.native)):
            text = chunker.contextualize(ch)
            if text and text.strip():
                chunks.append(Chunk(index=i, text=text))
        logger.info("Docling HybridChunker -> {} chunks (max_tokens={})", len(chunks), self.max_tokens)
        return chunks
