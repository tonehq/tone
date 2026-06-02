from __future__ import annotations

import io
import os
from abc import ABC, abstractmethod
from typing import List

from docx import Document as _Docx
from llama_cloud_services import LlamaParse
from loguru import logger
from PyPDF2 import PdfReader as _PdfReader

from core.services.rag.types import Document


class DocumentReader(ABC):
    @abstractmethod
    def supports(self, content_type: str) -> bool:
        ...

    @abstractmethod
    def read(self, file_bytes: bytes, content_type: str) -> Document:
        ...


class LlamaParseReader(DocumentReader):
    _EXT = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
        "application/vnd.ms-powerpoint": ".ppt",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/vnd.ms-excel": ".xls",
        "text/html": ".html",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/tiff": ".tiff",
    }

    def __init__(self, api_key: str = None, result_type: str = "markdown"):
        self._api_key = api_key or os.getenv("LLAMA_CLOUD_API_KEY")
        self._result_type = result_type
        self._parser = None

    def _get_parser(self):
        if self._parser is None:
            self._parser = LlamaParse(api_key=self._api_key, result_type=self._result_type)
        return self._parser

    def supports(self, content_type: str) -> bool:
        return content_type in self._EXT and bool(self._api_key)

    def read(self, file_bytes: bytes, content_type: str) -> Document:
        ext = self._EXT.get(content_type, "")
        docs = self._get_parser().load_data(file_bytes, extra_info={"file_name": f"upload{ext}"})
        text = "\n\n".join(d.text for d in docs if getattr(d, "text", None))
        logger.info("LlamaParse parsed {} -> {} chars", content_type, len(text))
        return Document(text=text, metadata={"parser": "llamaparse"})


class PdfReader(DocumentReader):
    def supports(self, content_type: str) -> bool:
        return content_type == "application/pdf"

    def read(self, file_bytes: bytes, content_type: str) -> Document:
        reader = _PdfReader(io.BytesIO(file_bytes))
        pages = [p.extract_text() for p in reader.pages]
        result = "\n\n".join(t for t in pages if t)
        logger.info("Extracted {} chars from PDF ({} pages)", len(result), len(reader.pages))
        return Document(text=result, metadata={"parser": "pypdf2"})


class DocxReader(DocumentReader):
    _TYPES = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    )

    def supports(self, content_type: str) -> bool:
        return content_type in self._TYPES

    def read(self, file_bytes: bytes, content_type: str) -> Document:
        doc = _Docx(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        result = "\n\n".join(paragraphs)
        logger.info("Extracted {} chars from DOCX ({} paragraphs)", len(result), len(paragraphs))
        return Document(text=result, metadata={"parser": "python-docx"})


class TextReader(DocumentReader):
    def supports(self, content_type: str) -> bool:
        return content_type.startswith("text/") or content_type in ("application/csv", "application/json")

    def read(self, file_bytes: bytes, content_type: str) -> Document:
        return Document(text=file_bytes.decode("utf-8", errors="replace"), metadata={"parser": "text"})


class CompositeReader(DocumentReader):
    def __init__(self, readers: List[DocumentReader] = None):
        self._readers = readers or [LlamaParseReader(), PdfReader(), DocxReader(), TextReader()]

    def supports(self, content_type: str) -> bool:
        return any(r.supports(content_type) for r in self._readers)

    def read(self, file_bytes: bytes, content_type: str) -> Document:
        for reader in self._readers:
            if reader.supports(content_type):
                return reader.read(file_bytes, content_type)
        raise ValueError(f"Unsupported content type for text extraction: {content_type}")
