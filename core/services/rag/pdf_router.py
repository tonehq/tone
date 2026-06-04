from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from loguru import logger

from core.services.rag.pdf_html import HtmlConversion, convert_pdf_to_html
from core.services.rag.pdf_inspect import PdfInspection, inspect_pdf

PDF_CONTENT_TYPE = "application/pdf"
HTML_CONTENT_TYPE = "text/html"

PIPELINE_HTML_DOCLING = "html_docling"
PIPELINE_OCR = "ocr"

OCR_ENABLED = False


@dataclass
class BuildResult:
    pipeline: str
    recommended_pipeline: str
    content_type: str
    html: str
    text: str
    inspection: PdfInspection
    conversion: HtmlConversion

    @property
    def html_bytes(self) -> bytes:
        return self.html.encode("utf-8")

    def metrics(self) -> dict:
        data = {
            "pipeline": self.pipeline,
            "recommended_pipeline": self.recommended_pipeline,
            "ocr_enabled": OCR_ENABLED,
            "html_conversion_seconds": round(self.conversion.conversion_seconds, 3),
            "html_length": len(self.html),
            "text_length": len(self.text),
        }
        data.update(self.inspection.to_dict())
        return data


class IngestionPipelineBuilder:
    pipeline = "base"
    content_type = HTML_CONTENT_TYPE

    def __init__(self, inspection: PdfInspection, conversion: HtmlConversion):
        self.inspection = inspection
        self.conversion = conversion

    def recommended(self) -> str:
        return PIPELINE_OCR if self.inspection.has_blockers else PIPELINE_HTML_DOCLING

    def build(self) -> BuildResult:
        return BuildResult(
            pipeline=self.pipeline,
            recommended_pipeline=self.recommended(),
            content_type=self.content_type,
            html=self.conversion.html,
            text=self.conversion.text,
            inspection=self.inspection,
            conversion=self.conversion,
        )


class HtmlDoclingPipelineBuilder(IngestionPipelineBuilder):
    pipeline = PIPELINE_HTML_DOCLING
    content_type = HTML_CONTENT_TYPE


class PdfRoutingService:
    def build(self, file_bytes: bytes, content_type: str) -> Optional[BuildResult]:
        if content_type != PDF_CONTENT_TYPE:
            return None

        conversion = convert_pdf_to_html(file_bytes)
        inspection = inspect_pdf(file_bytes)
        result = HtmlDoclingPipelineBuilder(inspection, conversion).build()

        logger.info("\n" + _format_banner(result))
        return result


def _format_banner(result: BuildResult) -> str:
    insp = result.inspection
    conv = result.conversion
    bar = "=" * 70
    lines = [
        "",
        bar,
        "  PDF ROUTER",
        bar,
        f"  pipeline             : {result.pipeline}",
        f"  recommended_pipeline : {result.recommended_pipeline}",
        f"  ocr_enabled          : {OCR_ENABLED}",
        f"  pdf -> html          : {conv.conversion_seconds:.2f}s",
        f"  html_length          : {len(result.html)} chars",
        f"  text_length          : {len(result.text)} chars",
        "  " + "-" * 68,
        f"  total_pages          : {insp.total_pages}",
        f"  image_count          : {insp.image_count}  (skipped)",
        f"  table_count          : {insp.table_count}  (skipped)",
        f"  pages_with_images    : {insp.pages_with_images}",
        f"  pages_with_tables    : {insp.pages_with_tables}",
        f"  sections_with_images : {insp.sections_with_images}",
        f"  sections_with_tables : {insp.sections_with_tables}",
        bar,
        "",
    ]
    return "\n".join(lines)
