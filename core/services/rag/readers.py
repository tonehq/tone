from __future__ import annotations

import io
import os
import tempfile
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docx import Document as _Docx
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


class DoclingReader(DocumentReader):
    _EXT = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
        "application/vnd.ms-powerpoint": ".ppt",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/vnd.ms-excel": ".xls",
        "text/html": ".html",
        "text/markdown": ".md",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/tiff": ".tiff",
    }

    def __init__(self, page_range: Optional[Tuple[int, int]] = None, ocr: bool = False, tables: bool = False):
        self._converter = None
        self._page_range = page_range
        self._ocr = ocr
        self._tables = tables

    def _get_converter(self):
        if self._converter is None:
            options = PdfPipelineOptions(do_ocr=self._ocr, do_table_structure=self._tables)
            self._converter = DocumentConverter(
                format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
            )
        return self._converter

    def supports(self, content_type: str) -> bool:
        return content_type in self._EXT

    def read(self, file_bytes: bytes, content_type: str) -> Document:
        ext = self._EXT.get(content_type, "")
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        kwargs = {"page_range": self._page_range} if self._page_range else {}
        logger.info(
            "Docling parsing {} ({:.2f} MB), page_range={}, ocr={}, tables={} ...",
            content_type, len(file_bytes) / 1024 / 1024, self._page_range or "all", self._ocr, self._tables,
        )
        start = time.monotonic()
        try:
            result = self._get_converter().convert(tmp_path, **kwargs)
            text = result.document.export_to_markdown()
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        logger.info(
            "Docling parsed {} -> {} chars in {:.1f}s (page_range={})",
            content_type, len(text), time.monotonic() - start, self._page_range or "all",
        )
        return Document(text=text, metadata={"parser": "docling", "page_range": self._page_range})


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
        self._readers = readers or [DoclingReader(), PdfReader(), DocxReader(), TextReader()]

    def supports(self, content_type: str) -> bool:
        return any(r.supports(content_type) for r in self._readers)

    def read(self, file_bytes: bytes, content_type: str) -> Document:
        for reader in self._readers:
            if reader.supports(content_type):
                return reader.read(file_bytes, content_type)
        raise ValueError(f"Unsupported content type for text extraction: {content_type}")
