"""Extract plain text from uploaded document files (PDF, DOCX, TXT, CSV)."""

import csv
import io

from loguru import logger


class TextExtractor:
    """Converts file bytes into plain text based on content type."""

    SUPPORTED_TYPES = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/csv",
    }

    def extract(self, file_bytes: bytes, content_type: str) -> str:
        if content_type == "application/pdf":
            return self._extract_pdf(file_bytes)
        elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return self._extract_docx(file_bytes)
        elif content_type == "text/csv":
            return self._extract_csv(file_bytes)
        elif content_type == "text/plain":
            return file_bytes.decode("utf-8")
        else:
            raise ValueError(f"Unsupported content type: {content_type}")

    def _extract_pdf(self, file_bytes: bytes) -> str:
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        result = "\n\n".join(pages)
        logger.info("Extracted text from PDF: {} pages, {} chars", len(reader.pages), len(result))
        return result

    def _extract_docx(self, file_bytes: bytes) -> str:
        from docx import Document

        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        result = "\n\n".join(paragraphs)
        logger.info("Extracted text from DOCX: {} paragraphs, {} chars", len(paragraphs), len(result))
        return result

    def _extract_csv(self, file_bytes: bytes) -> str:
        text = file_bytes.decode("utf-8")
        reader = csv.reader(io.StringIO(text))
        rows = []
        for row in reader:
            rows.append(", ".join(row))
        result = "\n".join(rows)
        logger.info("Extracted text from CSV: {} rows, {} chars", len(rows), len(result))
        return result
