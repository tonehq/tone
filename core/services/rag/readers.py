from __future__ import annotations

import importlib.util
import io
from abc import ABC, abstractmethod
from typing import List

from loguru import logger

from core.services.rag.types import Document


class DocumentReader(ABC):
    @abstractmethod
    def supports(self, content_type: str) -> bool:
        ...

    @abstractmethod
    def read(self, file_bytes: bytes, content_type: str) -> Document:
        ...


class DoclingReader(DocumentReader):
    _EXT = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/msword": ".docx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "text/html": ".html",
        "text/markdown": ".md",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/tiff": ".tiff",
    }

    def __init__(self):
        self._converter = None

    @staticmethod
    def _installed() -> bool:
        return importlib.util.find_spec("docling") is not None

    def _get_converter(self):
        if self._converter is None:
            from docling.document_converter import DocumentConverter

            self._converter = DocumentConverter()
        return self._converter

    def supports(self, content_type: str) -> bool:
        return content_type in self._EXT and self._installed()

    def read(self, file_bytes: bytes, content_type: str) -> Document:
        from docling.datamodel.base_models import DocumentStream

        ext = self._EXT.get(content_type, "")
        source = DocumentStream(name=f"upload{ext}", stream=io.BytesIO(file_bytes))
        result = self._get_converter().convert(source)
        dl_doc = result.document
        markdown = dl_doc.export_to_markdown()
        logger.info("Docling parsed {} -> {} chars of markdown", content_type, len(markdown))
        return Document(text=markdown, native=dl_doc, metadata={"parser": "docling"})


class PdfReader(DocumentReader):
    def supports(self, content_type: str) -> bool:
        return content_type == "application/pdf"

    def read(self, file_bytes: bytes, content_type: str) -> Document:
        from PyPDF2 import PdfReader as _PdfReader

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
        from docx import Document as _Docx

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
        self._readers = readers or [DoclingReader(), PdfReader(), DocxReader(), TextReader()]

    def supports(self, content_type: str) -> bool:
        return any(r.supports(content_type) for r in self._readers)

    def read(self, file_bytes: bytes, content_type: str) -> Document:
        for reader in self._readers:
            if reader.supports(content_type):
                return reader.read(file_bytes, content_type)
        raise ValueError(f"Unsupported content type for text extraction: {content_type}")
