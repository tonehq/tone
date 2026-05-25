"""Extract plain text from uploaded files (PDF, DOCX, TXT, CSV)."""

import io

from loguru import logger


class TextExtractionService:

    def extract(self, file_bytes: bytes, content_type: str) -> str:
        """Extract text from file bytes based on content type."""
        if content_type == "application/pdf":
            return self._extract_pdf(file_bytes)
        elif content_type in (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ):
            return self._extract_docx(file_bytes)
        elif content_type.startswith("text/") or content_type == "application/csv":
            return file_bytes.decode("utf-8", errors="replace")
        else:
            raise ValueError(f"Unsupported content type for text extraction: {content_type}")

    def _extract_pdf(self, file_bytes: bytes) -> str:
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        result = "\n\n".join(pages)
        logger.info("Extracted {} chars from PDF ({} pages)", len(result), len(reader.pages))
        return result

    def _extract_docx(self, file_bytes: bytes) -> str:
        from docx import Document

        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        result = "\n\n".join(paragraphs)
        logger.info("Extracted {} chars from DOCX ({} paragraphs)", len(result), len(paragraphs))
        return result
