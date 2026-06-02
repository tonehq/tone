from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

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
